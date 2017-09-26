from docutils.core import publish_parts
import inspect
import json
from functools import wraps
from textwrap import dedent

from flask import Response, render_template, request
from jinja2 import Environment

from runtime_typecheck import check_args, DetailedTypeError


class TypedMounter(object):
    DOC_HTML='''
        <html>
        <head>
        <title>{{ function_name }}</title>
        <style>
        th, td {
            border: 1px solid black;
            padding: 1ex;
            font-family: sans-serif;
        }
        </style>
        </head>
        <body>
        <h1>{{ function_name }}</h1>
        {{ doc_html|safe }}
        <p>Type hints</p>
        <table>
          <colgroup span="4"></colgroup>
          <tr>
            <th>Parameter</th>
            <th>Type</th>
            <th>Default value</th>
          </tr>
          
            {% for p in parameters %}
                <tr>
                    <td>{{ p.name }}</td>
                    <td>{{ p.type }}</td>
                    <td>{{ p.default_value }}</td>
                </tr>
            {% endfor %}
        </table>

       
        </body>
        </html>
    '''

    def __init__(self, app=None):
        self._app = app

    def init_app(self, app):
        self._app = app

    def attach_endpoint(self, rule, **options):
        if self._app is None:
            raise ValueError("App not initiated.")
        else:
            if options.get('methods', ['POST']) != ['POST']:
                raise ValueError(f'currently the function can be mounted only to a POST verb, was called with methods={options["methods"]}')

            def actual_decorator(fun):
                if options.get('auto_document', False):
                    document_options = options.copy()
                    document_options['methods'] = ['GET']
                    document_options.pop('auto_document', None)

                    @self._app.route(rule, **document_options)
                    def document():
                        doc_html = publish_parts(dedent(fun.__doc__), writer_name='html')['html_body']
                        parameter_descriptions = []
                        for name, attributes in inspect.signature(fun).parameters.items():
                            parameter_descriptions.append({
                                'name': name,
                                'type': repr(attributes.annotation),
                                'default_value': '' if attributes.default == inspect._empty else attributes.default
                            })
                        return Environment(autoescape=True)\
                            .from_string(dedent(self.DOC_HTML))\
                            .render(doc_html=doc_html, parameters=parameter_descriptions, function_name=fun.__name__)


            # deal with the methods
                # see http://werkzeug.pocoo.org/docs/0.12/routing/#werkzeug.routing.Rule
                # Example: allow automatic documentation when one calls GET or use GET
                # parameters to call the function.

                api_options = options.copy()
                api_options['methods'] = ['POST']
                api_options.pop('auto_document', None)

                @wraps(fun)
                @self._app.route(rule, endpoint=rule, **api_options)
                def service():
                    try:
                        with_type_checking = check_args(fun)
                        js = json.dumps(with_type_checking(**request.get_json()))
                        resp = Response(js, status=200, mimetype='application/json')
                        return resp

                    except DetailedTypeError as dte:
                        return Response(json.dumps({
                            "error": "invalid types",
                            "details": [{
                                'parameter': issue.name,
                                'expected': repr(issue.expected_type),
                                'found': issue.value,
                                'missing': issue.missing_parameter,
                                'message': issue.generic_message
                            } for issue in dte.issues]
                        }), status=400, mimetype='application/json')

                return service
        return actual_decorator

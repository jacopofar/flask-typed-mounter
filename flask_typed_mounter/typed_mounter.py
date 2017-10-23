from functools import wraps
import inspect
import json
from pathlib import Path
from shutil import rmtree
import sys
import tempfile
from textwrap import dedent
import traceback

from docutils.core import publish_parts
from flask import Response, request
from jinja2 import Environment
from werkzeug.utils import secure_filename

from runtime_typecheck import check_args, DetailedTypeError


class TypedMounter(object):
    DEFAULT_DOC_HTML = '''
        <html>
        <head>
        <title>{{ function_name }}</title>
        <style>
        body {
            background-color: aliceblue;
            font-family: sans-serif;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            text-align: left;
            padding: 8px;
            border: 1px solid lightgray;
            color: rgba(89, 96, 105, 1.0);
        }
        th {
            color: rgba(36, 41, 46, 1.0);
            background: rgba(209, 230, 254, 0.7);
        }
        .function {
            padding: 10px;
            background-color: rgba(95, 183, 96, 1.0);
            border-radius: 5px;
            color: white;
            display: inline-block;
        }
        </style>
        </head>
        <body>
        <h1 class="function">{{ function_name }}</h1>
        <div class="doc">{{ doc_html|safe }}</div>
        <h4>Type Hints:</h4>
        <table class="type-hints-{{ function_name }}">
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

    def __init__(self, app=None, doc_html_template=DEFAULT_DOC_HTML):
        self._app = app
        self.doc_html = doc_html_template

    def init_app(self, app):
        self._app = app

    def attach_endpoint(self, rule, **options):
        if self._app is None:
            raise ValueError("App not initiated.")
        else:
            if options.get('methods', ['POST']) != ['POST']:
                raise ValueError(f'currently the function can be mounted only to a POST verb, was called with methods={options["methods"]}')

            def actual_decorator(fun):
                # keys used for the wrapper itself and not to be passed to Flask
                own_keys = ['auto_document', 'accept_files', 'allowed_extensions']
                if options.get('auto_document', True):
                    document_options = options.copy()
                    document_options['methods'] = ['GET']
                    for key in own_keys:
                        document_options.pop(key, None)

                    @self._app.route(rule, **document_options, endpoint=f'doc_{rule}')
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
                            .from_string(dedent(self.doc_html))\
                            .render(doc_html=doc_html, parameters=parameter_descriptions, function_name=fun.__name__)


                # see http://werkzeug.pocoo.org/docs/0.12/routing/#werkzeug.routing.Rule
                # Example: allow automatic documentation when one calls GET or use GET
                # parameters to call the function.

                api_options = options.copy()
                api_options['methods'] = ['POST']
                for key in own_keys:
                    api_options.pop(key, None)

                @wraps(fun)
                @self._app.route(rule, endpoint=f'api_{rule}', **api_options)
                def service():

                    with_type_checking = check_args(fun)
                    try:
                        # JSON POST, this is what most of us want
                        if request.get_json() is not None:
                            js = json.dumps(with_type_checking(**request.get_json()))
                            resp = Response(js, status=200, mimetype='application/json')
                            return resp

                        # forms: no types, nor structure
                        # A simple dictionary where all values are strings, not very useful but still provided
                        # Since the input is flat, the desired output is likely plain text too
                        if len(request.values) + len(request.files) > 0:
                            form_params = {k: v for k, v in request.values.items()}
                            # now add the files, if any, to the argument dictionary
                            # presenting them as pathlib.Path instances
                            dir_for_request = None
                            if options.get('accept_files', False):
                                allowed_extensions = [ext.lower() for ext in options.get('allowed_extensions', [])]
                                for arg_name, file in request.files.items():
                                    if len(allowed_extensions) > 0:
                                        if file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
                                            continue
                                    if dir_for_request is None:
                                        dir_for_request = Path(tempfile.mkdtemp())
                                        print('TMP directory:', dir_for_request)
                                    path = dir_for_request / secure_filename(file.filename)
                                    file.save(str(path))
                                    form_params[arg_name] = path
                            txt_response = str(with_type_checking(**form_params))
                            resp = Response(txt_response, status=200, mimetype='text/plain')
                            if dir_for_request is not None:
                                rmtree(str(dir_for_request))
                            return resp
                        return Response(f'Unknown request type. Mimetype was {request.mimetype}', status=400)
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

                    except:
                        exc = sys.exc_info()
                        traceback.print_exc(file=sys.stdout)
                        return Response(str(f'Error in function {fun.__name__}\n {exc[0]}: {exc[1]}'), status=400)

                return service
        return actual_decorator

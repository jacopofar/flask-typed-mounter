import inspect
import json
import sys
import tempfile
import traceback
from functools import wraps
from pathlib import Path
from shutil import rmtree
from textwrap import dedent

from docutils.core import publish_parts
from flask import Response, request
from jinja2 import Environment
from runtime_typecheck import DetailedTypeError, check_args
from werkzeug.utils import secure_filename


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

    # keys used for the wrapper itself and not to be passed to Flask
    OWN_KEYS = ['auto_document', 'accept_files', 'allowed_extensions']

    def __init__(self, app=None, doc_html_template=DEFAULT_DOC_HTML):
        self._app = app
        self.doc_html = dedent(doc_html_template)

    def init_app(self, app):
        self._app = app

    def attach_endpoint(self, rule, **options):
        if self._app is None:
            raise ValueError("App not initiated.")

        if options.get('methods', ['POST']) != ['POST']:
            raise ValueError(f'currently the function can be mounted only to a POST verb, was called with methods={options["methods"]}')

        def actual_decorator(fun):
            if options.get('auto_document', True):
                document_options = self.extract_document_options(options)

                @self._app.route(rule, **document_options, endpoint=f'doc_{rule}')
                def document():
                    doc_html = publish_parts(dedent(fun.__doc__), writer_name='html')['html_body']
                    parameters_description = self.get_parameters_description(fun)

                    return Environment(autoescape=True)\
                        .from_string(self.doc_html)\
                        .render(doc_html=doc_html, parameters=parameters_description, function_name=fun.__name__)


            # see http://werkzeug.pocoo.org/docs/0.12/routing/#werkzeug.routing.Rule
            # Example: allow automatic documentation when one calls GET or use GET
            # parameters to call the function.

            api_options = options.copy()
            api_options['methods'] = ['POST']
            api_options = self.pop_own_keys(api_options)

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
                    if request.values or request.files:
                        form_params = {k: v for k, v in request.values.items()}
                        # now add the files, if any, to the argument dictionary
                        # presenting them as pathlib.Path instances
                        dir_for_request = None

                        if options.get('accept_files', False):
                            allowed_extensions = [ext.lower() for ext in options.get('allowed_extensions', [])]

                            for arg_name, file in request.files.items():
                                if self.not_an_allowed_extension(file, allowed_extensions):
                                    continue
                                if dir_for_request is None:
                                    dir_for_request = Path(tempfile.mkdtemp())
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
                    return self.make_typeerror_response(dte)

                except:
                    exc = sys.exc_info()
                    traceback.print_exc(file=sys.stdout)
                    return Response(str(f'Error in function {fun.__name__}\n {exc[0]}: {exc[1]}'), status=400)

            return service
        return actual_decorator

    def extract_document_options(self, options):
        document_options = options.copy()
        document_options['methods'] = ['GET']
        document_options = self.pop_own_keys(document_options)
        return document_options

    def pop_own_keys(self, options):
        keys = options.copy()
        for key in self.OWN_KEYS:
            keys.pop(key, None)
        return keys

    @staticmethod
    def get_parameters_description(fun):
        parameter_descriptions = []
        for name, attributes in inspect.signature(fun).parameters.items():
            parameter_descriptions.append({
                'name': name,
                'type': repr(attributes.annotation),
                'default_value': '' if attributes.default == inspect._empty else attributes.default
            })
        return parameter_descriptions

    @staticmethod
    def not_an_allowed_extension(file, allowed_extensions):
        return allowed_extensions and file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions

    @staticmethod
    def make_typeerror_response(dte):
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

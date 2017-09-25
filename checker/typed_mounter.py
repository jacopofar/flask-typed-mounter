import json
from functools import wraps

from flask import Response, request

from runtime_typecheck import check_args, DetailedTypeError


class TypedMounter(object):
    def __init__(self, app=None):
        self._app = app

    def init_app(self, app):
        self._app = app

    def attach_endpoint(self, rule, **options):
        if self._app is None:
            raise ValueError("App not initiated.")
        else:
            def actual_decorator(fun):
                # TODO parse options dictionary to retrieve options that are not among werkzeug ones
                # see http://werkzeug.pocoo.org/docs/0.12/routing/#werkzeug.routing.Rule
                # Example: allow automatic documentation when one calls GET or use GET
                # parameters to call the function.
                @wraps(fun)
                @self._app.route(rule, **options)
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

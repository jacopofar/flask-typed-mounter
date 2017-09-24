import json
from functools import wraps

from flask import Flask, Response, request

from runtime_typecheck import check_args, DetailedTypeError

app = Flask(__name__)


def attach_endpoint(rule, **options):
    def actual_decorator(fun):
        # TODO parse options dictionary to retrieve options that are not among werkzeug ones
        # see http://werkzeug.pocoo.org/docs/0.12/routing/#werkzeug.routing.Rule
        # Example: allow automatic documentation when one calls GET or use GET parameters to call the function
        @wraps(fun)
        @app.route(rule, **options)
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


@attach_endpoint('/mul', methods=['GET', 'POST'])
def multiplier(val1: int, val2: int = 5):
    return val1 * val2

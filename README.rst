.. image:: https://travis-ci.org/jacopofar/flask-typed-mounter.svg?branch=master
    :target: https://travis-ci.org/jacopofar/flask-typed-mounter
    :alt: Travis CI badge

Flask typed mounter
###################


Exposes a plain Python function as an HTTP endpoint using Flask, performs type checking bewteen HTTP request and Python 3.6 type hints to give the client a clear error before calling the function. A GET request retrieves the documentation and type hints for that function

Work in progress, don't hesitate forking/asking/suggesting


See `example.py` for a complete example, in short:

.. code-block:: python
    @tm.attach_endpoint('/mul', methods=['POST'], auto_document=True)
    def multiplier(val1: int, val2: int = 5):
        return val1 * val2


this will expose your multiplier function at `/mul`, with the result that a POST of a JSON will be validated against type hints and give a JSON answer or nice error message if not matching. A GET for that endpoint will show the rendered pydoc string and the type hints.

Type checking (based on Python 3.6 typing):

.. image:: error_check.png

Documentation:

.. image:: doc_screenshot.png

Correct call:

.. image:: no_errors.png


A customized doc template can be passed as `doc_html_template` when instantiating the server and documentation endpoint can be disabled on single functions by passing `auto_document=False`
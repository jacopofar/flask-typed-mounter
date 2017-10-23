import json
import unittest

from flask import Flask

from flask_typed_mounter import TypedMounter


class AppTest(unittest.TestCase):
    def setUp(self):
        app = Flask(__name__)
        self.tm = TypedMounter(app)
        self.app = app.test_client()

        @self.tm.attach_endpoint('/mul', methods=['POST'], auto_document=False)
        def multiplier(val1: int, val2: int = 5):
            return val1 * val2

        @self.tm.attach_endpoint('/mul_two', methods=['POST'])
        def multiplier_with_doc(val1: int, val2: int = 5):
            """
            SPECIAL_STRING_FROM_DOCUMENTATION
            """
            return val1 * val2

        @self.tm.attach_endpoint('/concat', methods=['POST'])
        def concat(a: str, b: str = 'yeah'):
            return ''.join([a, b])

    def test_correct_call(self):
        response = self.app.post("/mul",
                                 data=json.dumps({'val1': 4}),
                                 content_type='application/json')
        self.assertEqual(response.status_code, 200)

    def test_wrong_call(self):
        response = self.app.post("/mul",
                                 data=json.dumps({'val1': 'not an integer!'}),
                                 content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_doc_generation(self):
        response = self.app.get("/mul_two")
        self.assertTrue('SPECIAL_STRING_FROM_DOCUMENTATION'.encode('utf-8') in response.data)
        self.assertEqual(response.status_code, 200)

    def test_form_call(self):
        response = self.app.post("/concat",
                                 data=dict(
                                     a='dog',
                                     b='cat'
                                 ))
        self.assertEqual(response.data.decode(), 'dogcat')

    def test_form_call_conversion(self):
        response = self.app.post("/concat",
                                 data=dict(
                                     a=12,
                                     b='monkeys'
                                 ))
        self.assertEqual(response.data.decode(), '12monkeys')

    def test_wrong_form_call(self):
        response = self.app.post("/concat",
                                 data=dict(
                                     b='monkeys'
                                 ))
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()

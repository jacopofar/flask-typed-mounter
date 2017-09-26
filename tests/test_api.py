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
            '''
            SPECIAL_STRING_FROM_DOCUMENTATION
            '''
            return val1 * val2

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

    def test_only_post_is_accepted(self):
        with self.assertRaises(ValueError):
            @self.tm.attach_endpoint('/mul_three', methods=['POST', 'PUT'])
            def foo(val1: int, val2: int = 5):
                return val1 * val2

    def test_doc_generation(self):
        response = self.app.get("/mul_two")
        self.assertTrue('SPECIAL_STRING_FROM_DOCUMENTATION'.encode('utf-8') in response.data)
        self.assertEqual(response.status_code, 200)

if __name__ == "__main__":
    unittest.main()

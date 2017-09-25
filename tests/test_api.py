import json
import unittest

from flask import Flask

from checker import TypedMounter


class AppTest(unittest.TestCase):
    def setUp(self):
        app = Flask(__name__)
        tm = TypedMounter(app)
        self.app = app.test_client()

        @tm.attach_endpoint('/mul', methods=['GET', 'POST'])
        def multiplier(val1: int, val2: int = 5):
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


if __name__ == "__main__":
    unittest.main()

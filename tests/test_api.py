import json
import unittest

from checker import app


class AppTest(unittest.TestCase):
    def setUp(self):
        self.app = app.app.test_client()

    def test_correct_call(self):
        response = self.app.post("/mul", data=json.dumps({'val1': 4}), content_type='application/json')
        self.assertEqual(response.status_code, 200)

    def test_wrong_call(self):
        response = self.app.post("/mul", data=json.dumps({'val1': 'not an integer!'}), content_type='application/json')
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()

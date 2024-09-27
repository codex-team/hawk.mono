import requests
import unittest
import json


class TestErrorsRequestStructure(unittest.TestCase):

    def test_http_empty_access(self):
        response = json.loads(requests.get("http://collector:3000/").text)
        self.assertEqual(response['error'], True)
        self.assertEqual(response['message'], "Invalid JSON format")

    def test_http_random_data(self):
        response = json.loads(requests.post("http://collector:3000/", data="1234567890").text)
        self.assertEqual(response['error'], True)
        self.assertEqual(response['message'], "Invalid JSON format")

    def test_http_empty_payload(self):
        response = json.loads(requests.post("http://collector:3000/", data="{}").text)
        self.assertEqual(response['error'], True)
        self.assertEqual(response['message'], "Payload is empty")

    def test_http_empty_token(self):
        response = json.loads(requests.post("http://collector:3000/", data=json.dumps({"payload": ""})).text)
        self.assertEqual(response['error'], True)
        self.assertEqual(response['message'], "Token is empty")

    def test_http_empty_cather_type(self):
        response = json.loads(requests.post("http://collector:3000/", data=json.dumps({"payload": "", "token": "abcdef"})).text)
        self.assertEqual(response['error'], True)
        self.assertEqual(response['message'], "CatcherType is empty")

    def test_http_invalid_jwt(self):
        response = json.loads(requests.post("http://collector:3000/", data=json.dumps({"payload": "", "token": "abcdef", "CatcherType": "python"})).text)
        self.assertEqual(response['error'], True)
        self.assertEqual(response['message'], "invalid JWT signature")

    def test_http_empty_valid(self):
        response = json.loads(requests.post("http://collector:3000/", data=json.dumps({"payload": "", "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwcm9qZWN0SWQiOiJwcm9qSUQiLCJpYXQiOjE1NjcxMDQ4NDF9.nJveSAXwd38yCSG2PjOjBbQRmWtBtM6x7JWjshwl-sY", "CatcherType": "errors/python"})).text)
        self.assertEqual(response['error'], False)


class TestErrorsRequestLimits(unittest.TestCase):

    def setUp(self) -> None:
        self.valid_payload = {
            "payload": "",
            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwcm9qZWN0SWQiOiJwcm9qSUQiLCJpYXQiOjE1NjcxMDQ4NDF9.nJveSAXwd38yCSG2PjOjBbQRmWtBtM6x7JWjshwl-sY",
            "CatcherType": "errors/python"
        }

    def test_error_small_payload(self):
        response = json.loads(requests.post("http://collector:3000/", data=json.dumps(self.valid_payload)).text)
        self.assertEqual(response['error'], False)

    def test_error_equal_to_limit_payload(self):
        message = {**self.valid_payload, "payload": "a" * 57}  # enlarge payload to 250 bytes
        self.assertEqual(len(json.dumps(message)), 250)
        response = json.loads(requests.post("http://collector:3000/", data=json.dumps(message)).text)
        self.assertEqual(response['error'], False)

    def test_error_large_payload(self):
        message = {**self.valid_payload, "payload": "a" * 58}  # enlarge payload to 251 bytes
        self.assertEqual(len(json.dumps(message)), 251)
        response = json.loads(requests.post("http://collector:3000/", data=json.dumps(message)).text)
        self.assertEqual(response['error'], True)
        self.assertEqual(response['message'], "Request is too large")


class TestSourcemapsRequestLimits(unittest.TestCase):

    def setUp(self) -> None:
        self.headers = {"Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJwcm9qZWN0SWQiOiJwcm9qSUQiLCJpYXQiOjE1NjcxMDQ4NDF9.nJveSAXwd38yCSG2PjOjBbQRmWtBtM6x7JWjshwl-sY"}

    def test_sourcemap_small_payload(self):
        response = json.loads(requests.post(
            "http://collector:3000/sourcemap",
            headers=self.headers,
            files={"release": (None, "1.0.1"), "sourcemap1": "mini"}
        ).text)
        self.assertEqual(response['error'], False)

    def test_sourcemap_equal_to_limit_payload(self):
        response = json.loads(requests.post(
            "http://collector:3000/sourcemap",
            headers=self.headers,
            files={"release": (None, "1.0.1"), "sourcemap1": "equal"}
        ).text)
        self.assertEqual(response['error'], False)

    def test_sourcemap_large_payload(self):
        response = json.loads(requests.post(
            "http://collector:3000/sourcemap",
            headers=self.headers,
            files={"release": (None, "1.0.1"), "sourcemap1": "muuuch"}
        ).text)
        self.assertEqual(response['error'], True)
        self.assertEqual(response['message'], "Request is too large")


if __name__ == '__main__':
    unittest.main()

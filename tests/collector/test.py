import requests
import unittest
import json


class TestStringMethods(unittest.TestCase):

    def test_http_empty_access(self):
        response = json.loads(requests.get("http://collector:3000/").text)
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

if __name__ == '__main__':
    unittest.main()

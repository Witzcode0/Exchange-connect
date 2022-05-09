import unittest
import json
from app import flaskapp

class MyAppCase(unittest.TestCase):
    def setUp(self):
        flaskapp.config['TESTING'] = True
        self.app = flaskapp.test_client()

    # def test_dummy(self):
    #     response = self.app.get("/api/v1.0/event-invites")
    #     # data = json.loads(response.get_data(as_text=True))

    #     self.assertEquals(response.status_code, 200)
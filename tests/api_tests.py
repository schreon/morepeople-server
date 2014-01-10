import unittest
import inspect
import server
import json


class FlaskAppTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        # chooses testing config, i.e. in-memory db:
        self.app = server.app.test_client()
        server.connect("mongodb://localhost:27017/")
        server.queue.remove({})

    def test_server_being_up(self):
        """ Test if server is up. """
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)

    def test_enqueue_user(self):
        """ Test if client is correctly enqueued """
        data = {
            server.USER_ID : '1234567',
            server.MATCH_TYPE : server.MATCH_BEER,
            server.TIME_LEFT : 7200
            }

        headers = [('Content-Type', 'application/json')]


        # should not be there initially
        self.assertTrue(server.queue.find_one(data) is None)

        response = self.app.post('/queue', headers, data=json.dumps(data))

        # should be there now
        self.assertTrue(server.queue.find_one(data) is not None)

    def test_enqueue_multiple_users(self):
        """ Test if multiple clients are enqueued correctly """
        # Generate multiple users
        users = []
        for idx in range(100):
            data = {
                server.USER_ID : 'idx_'+str(idx),
                server.MATCH_TYPE : server.MATCH_BEER,
                server.TIME_LEFT : 7200
                }
            users.append(data)

        # Post enqueue requests to server
        headers = [('Content-Type', 'application/json')]
        for user in users:

            # should not be there initially
            self.assertTrue(server.queue.find_one(user) is None)

            # send request
            response = self.app.post('/queue', headers, data=json.dumps(user))

            # should be there now
            self.assertTrue(server.queue.find_one(user) is not None)

if __name__ == '__main__':
    unittest.main()

import unittest
import inspect
import server
import json
import os

class FlaskAppTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        # chooses testing config, i.e. in-memory db:
        self.app = server.app.test_client()
        server.queue.remove({})
        server.tags.remove({})
        server.users.remove({})

    def setUp(self):
        server.queue.remove({})
        server.tags.remove({})
        server.users.remove({})

    def test_server_being_up(self):
        """ Test if server is up. """
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)

    def test_access_status(self):
        """ Test if status is returned """

        # Generate multiple users
        users = []
        for idx in range(100):
            data = {
                'MATCH_TAG' : "beer",
                'TIME_LEFT' : 7200,
                'USER_ID' : 'idx_'+str(idx),
                'USER_NAME' : 'server_test_user',
                'LOC': {'LONGITUDE' : 100, 'LATITUDE' : 100 }
                }
            users.append(data)

        # Post enqueue requests to server
        headers = [('Content-Type', 'application/json')]
        for user in users:

            # should not be there initially
            self.assertTrue(server.queue.find_one(user) is None)

            # send request
            response = self.app.post('/queue', headers, data=json.dumps(user))

        # get status
        response = self.app.get('/status')
        self.assertEqual(response.status_code, 200)

    def test_enqueue_user(self):
        """ Test if client is correctly enqueued """
        data = {
            'USER_ID' : '1234567',
            'USER_NAME' : 'server_test_user',
            'MATCH_TAG' : "beer",
            'TIME_LEFT' : 7200,
            'LOC': {'LONGITUDE' : 100, 'LATITUDE' : 100 }
            }

        headers = [('Content-Type', 'application/json')]


        # should not be there initially
        self.assertTrue(server.queue.find_one(data) is None)

        response = self.app.post('/queue', headers, data=json.dumps(data))

        # should be there now
        self.assertTrue(server.queue.find_one({'USER_ID' : data['USER_ID']}) is not None)

    def test_enqueue_3_users(self):
        """ Test if client is correctly enqueued """

        # first user
        data = {
            'USER_ID' : '1',
            'USER_NAME' : 'server_test_user 1',
            'MATCH_TAG' : "beer",
            'TIME_LEFT' : 7200,
            'LOC': {'LONGITUDE' : 100, 'LATITUDE' : 100 }
            }

        headers = [('Content-Type', 'application/json')]


        # should not be there initially
        self.assertTrue(server.queue.find_one({'USER_ID' : '1'}) is None)
        self.assertTrue(server.queue.find_one({'USER_ID' : '2'}) is None)
        self.assertTrue(server.queue.find_one({'USER_ID' : '3'}) is None)

        response = self.app.post('/queue', headers, data=json.dumps(data))
        response = json.loads(response.data)
        self.assertEquals(response['STATE'], 'QUEUED')

        # should be there now
        self.assertTrue(server.queue.find_one({'USER_ID' : data['USER_ID']}) is not None)

        # second user
        data = {
            'USER_ID' : '2',
            'USER_NAME' : 'server_test_user 2',
            'MATCH_TAG' : "beer",
            'TIME_LEFT' : 7200,
            'LOC': {'LONGITUDE' : 100, 'LATITUDE' : 100 }
            }

        headers = [('Content-Type', 'application/json')]


        # should not be there initially
        self.assertTrue(server.queue.find_one({'USER_ID' : '1'}) is not None)
        self.assertTrue(server.queue.find_one({'USER_ID' : '2'}) is None)
        self.assertTrue(server.queue.find_one({'USER_ID' : '3'}) is None)

        response = self.app.post('/queue', headers, data=json.dumps(data))

        # should be there now
        self.assertTrue(server.queue.find_one({'USER_ID' : data['USER_ID']}) is not None)

        # third user - should match!
        data = {
            'USER_ID' : '3',
            'USER_NAME' : 'server_test_user 3',
            'MATCH_TAG' : "beer",
            'TIME_LEFT' : 7200,
            'LOC': {'LONGITUDE' : 100, 'LATITUDE' : 100 }
            }

        headers = [('Content-Type', 'application/json')]


        # should not be there initially
        self.assertTrue(server.queue.find_one({'USER_ID' : '1'}) is not None)
        self.assertTrue(server.queue.find_one({'USER_ID' : '2'}) is not None)
        self.assertTrue(server.queue.find_one({'USER_ID' : '3'}) is None)

        response = self.app.post('/queue', headers, data=json.dumps(data))

        # should be removed because match
        self.assertTrue(server.queue.find_one({'USER_ID' : '1'}) is None)
        self.assertTrue(server.queue.find_one({'USER_ID' : '2'}) is None)
        self.assertTrue(server.queue.find_one({'USER_ID' : '3'}) is None)

        # queue again - should still be the same

        response = self.app.post('/queue', headers, data=json.dumps(data))
        self.assertTrue(server.queue.find_one({'USER_ID' : '1'}) is None)
        self.assertTrue(server.queue.find_one({'USER_ID' : '2'}) is None)
        self.assertTrue(server.queue.find_one({'USER_ID' : '3'}) is None)

        self.assertTrue(server.queue.find_one({'USER_ID' : '4'}) is None)
        # fourth user 
        data = {
            'USER_ID' : '4',
            'USER_NAME' : 'server_test_user 4',
            'MATCH_TAG' : "beer",
            'TIME_LEFT' : 7200,
            'LOC': {'LONGITUDE' : 100, 'LATITUDE' : 100 }
            }
        response = self.app.post('/queue', headers, data=json.dumps(data))
        self.assertTrue(server.queue.find_one({'USER_ID' : '1'}) is None)
        self.assertTrue(server.queue.find_one({'USER_ID' : '2'}) is None)
        self.assertTrue(server.queue.find_one({'USER_ID' : '3'}) is None)
        self.assertTrue(server.queue.find_one({'USER_ID' : '4'}) is not None)

        # queue the three which are in the match again - should not appear in queues

        data = {
            'USER_ID' : '1',
            'USER_NAME' : 'server_test_user 1',
            'MATCH_TAG' : "beer",
            'TIME_LEFT' : 7200,
            'LOC': {'LONGITUDE' : 100, 'LATITUDE' : 100 }
            }
        response = self.app.post('/queue', headers, data=json.dumps(data))
        self.assertTrue(server.queue.find_one({'USER_ID' : '1'}) is None)
        self.assertTrue(server.queue.find_one({'USER_ID' : '2'}) is None)
        self.assertTrue(server.queue.find_one({'USER_ID' : '3'}) is None)
        self.assertTrue(server.queue.find_one({'USER_ID' : '4'}) is not None)

        data = {
            'USER_ID' : '2',
            'USER_NAME' : 'server_test_user 2',
            'MATCH_TAG' : "beer",
            'TIME_LEFT' : 7200,
            'LOC': {'LONGITUDE' : 100, 'LATITUDE' : 100 }
            }
        response = self.app.post('/queue', headers, data=json.dumps(data))
        self.assertTrue(server.queue.find_one({'USER_ID' : '1'}) is None)
        self.assertTrue(server.queue.find_one({'USER_ID' : '2'}) is None)
        self.assertTrue(server.queue.find_one({'USER_ID' : '3'}) is None)
        self.assertTrue(server.queue.find_one({'USER_ID' : '4'}) is not None)

        data = {
            'USER_ID' : '3',
            'USER_NAME' : 'server_test_user 3',
            'MATCH_TAG' : "beer",
            'TIME_LEFT' : 7200,
            'LOC': {'LONGITUDE' : 100, 'LATITUDE' : 100 }
            }
        response = self.app.post('/queue', headers, data=json.dumps(data))
        self.assertTrue(server.queue.find_one({'USER_ID' : '1'}) is None)
        self.assertTrue(server.queue.find_one({'USER_ID' : '2'}) is None)
        self.assertTrue(server.queue.find_one({'USER_ID' : '3'}) is None)
        self.assertTrue(server.queue.find_one({'USER_ID' : '4'}) is not None)

if __name__ == '__main__':
    unittest.main()

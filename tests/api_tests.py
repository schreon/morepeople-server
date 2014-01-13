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
        self.assertTrue(server.queue.find_one(data) is not None)

    def test_enqueue_multiple_users(self):
        """ Test if multiple clients are enqueued correctly """
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

            # should be there now
            self.assertTrue(server.queue.find_one(user) is not None)

    def test_nearest_users(self):
        """ test if the nearest users are actually found """
        # Generate multiple users
        users = []
        for idx in range(5):
            data = {
                'MATCH_TAG' : "beer",
                'TIME_LEFT' : 7200,
                'USER_ID' : 'idx_near_'+str(idx),
                'USER_NAME' : 'server_test_user',
                'LOC': {'LONGITUDE' : 100, 'LATITUDE' : 100 }
                }
            users.append(data)
        for idx in range(5):
            data = {
                'MATCH_TAG' : "beer",
                'TIME_LEFT' : 7200,
                'USER_ID' : 'idx_far_'+str(idx),
                'USER_NAME' : 'server_test_user',
                'LOC': {'LONGITUDE' : 30.1, 'LATITUDE' : 100.0 }
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

        # retrieve nearest queues
        nearest_queues = server.nearest_queues('idx_near_0')

        print "_____ NEAREST QUEUES ____"
        for x in nearest_queues:
            print x

    def test_try_matching(self):
        """ If there are enough users who are close enough to each other and who have the same match type, a match should take place and they should be removed from the queue """
        # Generate multiple users
        users = []
        results = []
        for idx in range(5):
            data = {
                'MATCH_TAG' : "beer",
                'TIME_LEFT' : 7200,
                'USER_ID' : 'idx_'+str(idx),
                'USER_NAME' : 'server_test_user',
                'LOC': {'LONGITUDE' : 100, 'LATITUDE' : 100 }
                }
            users.append(data)

        # # Post enqueue requests to server
        # usr_nr = 1
        # headers = [('Content-Type', 'application/json')]
        # for user in users:

        #     # should not be there initially
        #     self.assertTrue(server.queue.find_one(user) is None)

        #     # send request
        #     response = self.app.post('/queue', headers, data=json.dumps(user))

        #     # should be there now
        #     self.assertTrue(server.queue.find_one(user) is not None)


        #     data = json.loads(response.data)
        #     # every 3rd user should get a match
        #     if usr_nr % 3 == 0:
        #         self.assertTrue(data['STATUS']['MATCH_FOUND'])
        #     else:
        #         # the others not
        #         self.assertTrue(data['STATUS']['WAIT'])
        #     usr_nr += 1


    def test_different_matchtypes_no_matching(self):
        """ If there are enough users who are close enough to each other, but they have different match types selected, nothing should happen """
        # TODO
        pass

    def test_too_far_away_no_matching(self):
        """ If there are enough users who are not close enough to each other, even though they have the same match types selected, nothing should happen """
        # TODO
        pass

    def test_closest_place_should_be_chosen(self):
        """ If there are enough users who are close enough to each other, and they have different match types selected, the closest known meeting place should be chosen """
        # TODO
        pass

    def test_add_unknown_match_tag(self):
        """  If a tag is searched which does not exist yet, it should be added """
        data = {
            'MATCH_TAG' : "newtag",
            'USER_NAME' : 'server_test_user',
            'USER_ID' : '123',
            'LONGITUDE' : 123,
            'LATITUDE' : 92
            }

        headers = [('Content-Type', 'application/json')]

        # should not be there initially
        self.assertTrue(server.tags.find_one(data) is None)

        response = self.app.post('/addtag', headers, data=json.dumps(data))

        # should be there now
        self.assertTrue(server.tags.find_one({'MATCH_TAG' : 'newtag'}) is not None)

        data = {
            'MATCH_TAG' : "newt",
            'USER_ID' : '123',
            'USER_NAME' : 'server_test_user',
            'LONGITUDE' : 123,
            'LATITUDE' : 92
            }

        response = self.app.post('/searchtag', headers, data=json.dumps(data))

        data = json.loads(response.data)
        self.assertIn("newtag", data['RESULTS'])



if __name__ == '__main__':
    unittest.main()

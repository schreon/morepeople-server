# -*- coding: utf-8 -*- 
import os
import unittest
import inspect
import json

class FlaskAppTestCase(unittest.TestCase):

    @classmethod
    def setUpClass(self):
        os.environ['MORE_PEOPLE_DB'] = 'localhost'
        os.environ['MORE_PEOPLE_DB_NAME'] = 'morepeople_testing'
        os.environ['MORE_PEOPLE_LOG'] = 'morepeople_test.log'
        import server        
        self.server = server
        # chooses testing config, i.e. in-memory db:
        self.app = self.server.app.test_client()
        

    def setUp(self):
        self.server.users.remove({})
        self.server.queue.remove({})
        self.server.tags.remove({})
        self.server.lobbies.remove({})
        self.server.matches.remove({})
        self.server.evaluations.remove({})

    def test_server_being_up(self):
        """ Test if self.server.is up. """
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)

    def test_access_status(self):
        """ Test if status is returned """

        # Generate multiple users
        users = []
        for idx in range(5):
            data = {
                'MATCH_TAG' : "beer",
                'USER_ID' : 'test_idx_'+str(idx),
                'USER_NAME' : 'test__user',
                'LOC': {'lng' : 40, 'lat' : 9 }
                }
            users.append(data)

        # Post enqueue requests to server
        headers = [('Content-Type', 'application/json')]
        for user in users:

            # should not be there initially
            self.assertTrue(self.server.queue.find_one(user) is None)

            # send request
            response = self.app.post('/queue', headers, data=json.dumps(user))

        # get status
        response = self.app.get('/status')
        self.assertEqual(response.status_code, 200)

    def test_search_tag(self):
        """ Test if tag is returned """

        self.server.tags.insert({ 'MATCH_TAG' : "spaß" })

        self.assertTrue(self.server.tags.find_one({'MATCH_TAG' : 'spaß'}) is not None)
        # Generate multiple users
        users = []
        for idx in range(5):
            data = {
                'MATCH_TAG' : "spa",
                'USER_ID' : 'test_idx_'+str(idx),
                'USER_NAME' : 'test__user',
                'LOC': {'lng' : 40, 'lat' : 9 }
                }
            users.append(data)

        # Post enqueue requests to server
        headers = [('Content-Type', 'application/json')]
        for user in users:
            # send request
            response = self.app.post('/search', headers, data=json.dumps(user))
            response = json.loads(response.data)
            print response
            self.assertTrue('spaß'.decode('utf-8') in response['RESULTS'])

    def test_enqueue_user(self):
        """ test_enqueue_user """
        data = {
            'USER_ID' : 'test_1234567',
            'USER_NAME' : 'test__user',
            'MATCH_TAG' : "beer",
            'LOC': {'lng' : 40, 'lat' : 9 }
            }

        headers = [('Content-Type', 'application/json')]


        # should not be there initially
        self.assertTrue(self.server.queue.find_one(data) is None)

        response = self.app.post('/queue', headers, data=json.dumps(data))

        # should be there now
        self.assertTrue(self.server.queue.find_one({'USER_ID' : data['USER_ID']}) is not None)

    def test_enqueue_3_users(self):
        """ Ttest_enqueue_3_users """

        # first user
        data = {
            'USER_ID' : 'test_1',
            'USER_NAME' : 'test__user 1',
            'MATCH_TAG' : "beer",
            'LOC': {'lng' : 40, 'lat' : 9 }
            }

        headers = [('Content-Type', 'application/json')]


        # should not be there initially
        self.assertTrue(self.server.queue.find_one({'USER_ID' : 'test_1'}) is None)
        self.assertTrue(self.server.queue.find_one({'USER_ID' : 'test_2'}) is None)
        self.assertTrue(self.server.queue.find_one({'USER_ID' : 'test_3'}) is None)

        response = self.app.post('/queue', headers, data=json.dumps(data))
        response = json.loads(response.data)
        self.assertEquals(response['STATE'], 'QUEUED')

        # should be there now
        self.assertTrue(self.server.queue.find_one({'USER_ID' : data['USER_ID']}) is not None)

        # second user
        data = {
            'USER_ID' : 'test_2',
            'USER_NAME' : 'test__user 2',
            'MATCH_TAG' : "beer",
            'LOC': {'lng' : 40, 'lat' : 9 }
            }

        headers = [('Content-Type', 'application/json')]


        # should not be there initially
        self.assertTrue(self.server.queue.find_one({'USER_ID' : 'test_1'}) is not None)
        self.assertTrue(self.server.queue.find_one({'USER_ID' : 'test_2'}) is None)
        self.assertTrue(self.server.queue.find_one({'USER_ID' : 'test_3'}) is None)

        response = self.app.post('/queue', headers, data=json.dumps(data))

        # should be there now
        self.assertTrue(self.server.queue.find_one({'USER_ID' : data['USER_ID']}) is not None)

        # third user - should match!
        data = {
            'USER_ID' : 'test_3',
            'USER_NAME' : 'test__user 3',
            'MATCH_TAG' : "beer",
            'LOC': {'lng' : 40, 'lat' : 9 }
            }

        headers = [('Content-Type', 'application/json')]


        # should not be there initially
        self.assertTrue(self.server.queue.find_one({'USER_ID' : 'test_1'}) is not None)
        self.assertTrue(self.server.queue.find_one({'USER_ID' : 'test_2'}) is not None)
        self.assertTrue(self.server.queue.find_one({'USER_ID' : 'test_3'}) is None)

        response = self.app.post('/queue', headers, data=json.dumps(data))

        # should be removed because match
        self.assertTrue(self.server.queue.find_one({'USER_ID' : 'test_1'}) is None)
        self.assertTrue(self.server.queue.find_one({'USER_ID' : 'test_2'}) is None)
        self.assertTrue(self.server.queue.find_one({'USER_ID' : 'test_3'}) is None)

        # queue again - should still be the same

        response = self.app.post('/queue', headers, data=json.dumps(data))
        self.assertTrue(self.server.queue.find_one({'USER_ID' : 'test_1'}) is None)
        self.assertTrue(self.server.queue.find_one({'USER_ID' : 'test_2'}) is None)
        self.assertTrue(self.server.queue.find_one({'USER_ID' : 'test_3'}) is None)

        self.assertTrue(self.server.queue.find_one({'USER_ID' : 'test_4'}) is None)
        # fourth user 
        data = {
            'USER_ID' : 'test_4',
            'USER_NAME' : 'test__user 4',
            'MATCH_TAG' : "beer",
            'LOC': {'lng' : 40, 'lat' : 9 }
            }
        response = self.app.post('/queue', headers, data=json.dumps(data))
        self.assertTrue(self.server.queue.find_one({'USER_ID' : 'test_1'}) is None)
        self.assertTrue(self.server.queue.find_one({'USER_ID' : 'test_2'}) is None)
        self.assertTrue(self.server.queue.find_one({'USER_ID' : 'test_3'}) is None)
        self.assertTrue(self.server.queue.find_one({'USER_ID' : 'test_4'}) is not None)

        # queue the three which are in the match again - should not appear in queues

        data = {
            'USER_ID' : 'test_1',
            'USER_NAME' : 'test__user 1',
            'MATCH_TAG' : "beer",
            'LOC': {'lng' : 40, 'lat' : 9 }
            }
        response = self.app.post('/queue', headers, data=json.dumps(data))
        self.assertTrue(self.server.queue.find_one({'USER_ID' : 'test_1'}) is None)
        self.assertTrue(self.server.queue.find_one({'USER_ID' : 'test_2'}) is None)
        self.assertTrue(self.server.queue.find_one({'USER_ID' : 'test_3'}) is None)
        self.assertTrue(self.server.queue.find_one({'USER_ID' : 'test_4'}) is not None)

        data = {
            'USER_ID' : 'test_2',
            'USER_NAME' : 'test__user 2',
            'MATCH_TAG' : "beer",
            'LOC': {'lng' : 40, 'lat' : 9 }
            }
        response = self.app.post('/queue', headers, data=json.dumps(data))
        self.assertTrue(self.server.queue.find_one({'USER_ID' : 'test_1'}) is None)
        self.assertTrue(self.server.queue.find_one({'USER_ID' : 'test_2'}) is None)
        self.assertTrue(self.server.queue.find_one({'USER_ID' : 'test_3'}) is None)
        self.assertTrue(self.server.queue.find_one({'USER_ID' : 'test_4'}) is not None)

        data = {
            'USER_ID' : 'test_3',
            'USER_NAME' : 'test__user 3',
            'MATCH_TAG' : "beer",
            'LOC': {'lng' : 40, 'lat' : 9 }
            }
        response = self.app.post('/queue', headers, data=json.dumps(data))
        self.assertTrue(self.server.queue.find_one({'USER_ID' : 'test_1'}) is None)
        self.assertTrue(self.server.queue.find_one({'USER_ID' : 'test_2'}) is None)
        self.assertTrue(self.server.queue.find_one({'USER_ID' : 'test_3'}) is None)
        self.assertTrue(self.server.queue.find_one({'USER_ID' : 'test_4'}) is not None)

        # they all accept now
        data = {
            'USER_ID' : 'test_1',
            'USER_NAME' : 'test__user 3',
            'MATCH_TAG' : "beer",
            'LOC': {'lng' : 40, 'lat' : 9 }
            }
        response = self.app.post('/accept', headers, data=json.dumps(data)) 
        response = json.loads(response.data)      
        self.assertTrue(response['STATE'] == 'ACCEPTED')
        self.assertTrue(self.server.lobbies.find_one({'USER_ID' : 'test_1'})['STATE'] == 'ACCEPTED')

        data = {
            'USER_ID' : 'test_2',
            'USER_NAME' : 'test__user 3',
            'MATCH_TAG' : "beer",
            'LOC': {'lng' : 40, 'lat' : 9 }
            }
        response = self.app.post('/accept', headers, data=json.dumps(data)) 
        response = json.loads(response.data)      
        self.assertTrue(response['STATE'] == 'ACCEPTED')
        self.assertTrue(self.server.lobbies.find_one({'USER_ID' : 'test_2'})['STATE'] == 'ACCEPTED')

        data = {
            'USER_ID' : 'test_3',
            'USER_NAME' : 'test__user 3',
            'MATCH_TAG' : "beer",
            'LOC': {'lng' : 40, 'lat' : 9 }
            }
        response = self.app.post('/accept', headers, data=json.dumps(data)) 
        response = json.loads(response.data)      
        self.assertTrue(response['STATE'] == 'RUNNING')

        # lobby should be deleted now
        self.assertTrue(self.server.lobbies.find_one({'USER_ID' : 'test_1'}) is None)
        self.assertTrue(self.server.lobbies.find_one({'USER_ID' : 'test_2'}) is None)
        self.assertTrue(self.server.lobbies.find_one({'USER_ID' : 'test_3'}) is None)

        # running entries should exist now
        self.assertTrue(self.server.matches.find_one({'USER_ID' : 'test_1'}) is not None)
        self.assertTrue(self.server.matches.find_one({'USER_ID' : 'test_2'}) is not None)
        self.assertTrue(self.server.matches.find_one({'USER_ID' : 'test_3'}) is not None)

        # finish
        data = {
            'USER_ID' : 'test_1',
            'USER_NAME' : 'test__user 3',
            'MATCH_TAG' : "beer",
            'LOC': {'lng' : 40, 'lat' : 9 }
            }
        response = self.app.post('/finish', headers, data=json.dumps(data)) 
        response = json.loads(response.data)      
        self.assertTrue(response['STATE'] == 'FINISHED')

        # evaluate
        data = {
            'USER_ID' : 'test_1',
            'USER_NAME' : 'test__user 3',
            'EVALUATION' : {'foo':'bar'},
            'LOC': {'lng' : 40, 'lat' : 9 }
            }
        response = self.app.post('/evaluate', headers, data=json.dumps(data)) 
        response = json.loads(response.data)      
        self.assertTrue(response['STATE'] == 'OFFLINE')

    def test_view_other_queues(self):
        """ test_view_other_queues """
        # Generate multiple users
        users = []
        for idx in range(5):
            data = {
                'MATCH_TAG' : "beer"+str(idx),
                'USER_ID' : 'test_idx_'+str(idx),
                'USER_NAME' : 'test__user',
                'LOC': {'lng' : 40, 'lat' : 9 }
                }
            users.append(data)

        # Post enqueue requests to server
        headers = [('Content-Type', 'application/json')]
        for user in users:

            # should not be there initially
            self.assertTrue(self.server.queue.find_one(user) is None)

            # send request
            response = self.app.post('/queue', headers, data=json.dumps(user))

        # get status
        response = self.app.get('/status')
        self.assertEqual(response.status_code, 200)

        # get queues
        response = self.app.get('/queue?LON=40&LAT=9&RAD=1000')
        self.assertEqual(response.status_code, 200)
        response = json.loads(response.data)   
        self.assertTrue(len(response['SEARCHENTRIES']) > 0)

    def test_geonear(self):
        """ test geo near """
        users = []
        for idx in range(10):
            data = {
                'MATCH_TAG' : "beer"+str(idx),
                'USER_ID' : 'test_idx_'+str(idx),
                'USER_NAME' : 'test__user',
                'LOC': {'lng' : 40+idx, 'lat' : 40 +idx }
                }
            users.append(data)

        # Post enqueue requests to server
        headers = [('Content-Type', 'application/json')]
        for user in users:

            # should not be there initially
            self.assertTrue(self.server.queue.find_one(user) is None)

            # send request
            response = self.app.post('/queue', headers, data=json.dumps(user))

        from bson.son import SON
        results = self.server.db.command(SON([('geoNear', 'queue'), ('near', [48, 9]), ('num', 2)]))

        print "Testing geo near"
        for res in results['results']:
            print res

    def test_geonear_exact(self):

        user1 = {
                'MATCH_TAG' : "beer",
                'USER_ID' : 'test_idx_1',
                'USER_NAME' : 'test_user_1',
                'LOC': {'lat' : 48.7570286145899, 'lng' : 9.168221599212847 }
            }

        user2 = {
            'MATCH_TAG' : "beer",
            'USER_ID' : 'test_idx_2',
            'USER_NAME' : 'test_user_2',
            'LOC': {'lat' : 48.79405853210483, 'lng' : 9.176261157519184 }
        }

        users = [user1, user2]

        # Post enqueue requests to server
        headers = [('Content-Type', 'application/json')]
        for user in users:

            # should not be there initially
            self.assertTrue(self.server.queue.find_one(user) is None)

            # send request
            response = self.app.post('/queue', headers, data=json.dumps(user))

        response = self.app.get('/queue?LAT=48.7570286145899&LON=9.168221599212847&RAD=1000')
        response = json.loads(response.data)

        print "testing correctness of geo near!"
        for res in response['SEARCHENTRIES']:
            print res['USER_NAME']
            print res['DISTANCE']
            print "---"

        print "----"


if __name__ == '__main__':
    unittest.main()

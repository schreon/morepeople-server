import flask
from flask import Flask, make_response, request
from flask.ext.restful import reqparse

import mimetypes
import cPickle

import json
import csv
import StringIO

import os
import tempfile

static_folder = os.path.join('public')

app = Flask("MatchmakingClient",
            static_folder=static_folder, static_url_path='')


from json import JSONEncoder
from bson.objectid import ObjectId

class MongoEncoder(JSONEncoder):
    def default(self, obj, **kwargs):
        if isinstance(obj, ObjectId):
            return str(obj)
        else:            
            return JSONEncoder.default(obj, **kwargs)
app.json_encoder = MongoEncoder

import logging
from logging.handlers import RotatingFileHandler
file_handler = RotatingFileHandler(os.environ['BOCK_LOG'], maxBytes=1024 * 1024 * 100, backupCount=20)
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
app.logger.addHandler(file_handler)

app.logger.setLevel(logging.INFO)
api = flask.ext.restful.Api(app)

import pymongo
from pymongo import MongoClient
mongoclient, db, queue, tags = None, None, None, None
url = os.environ['BOCK_MONGO_TEST_DB']
mongoclient = MongoClient(url)

db = mongoclient['matchmaking']
tags = db['tags']
users = db['users']
queue = db['queue']
lobbies = db['lobbies']
running_matches = db['running_matches']
evaluations = db['evaluations']

users.remove({})
queue.remove({})
tags.remove({})
lobbies.remove({})
running_matches.remove({})
evaluations.remove({})

tags.insert({ 'MATCH_TAG' : "kaffee" })
tags.insert({ 'MATCH_TAG' : "bier" })
tags.insert({ 'MATCH_TAG' : "kochen" })
tags.insert({ 'MATCH_TAG' : "pizza" })
tags.insert({ 'MATCH_TAG' : "schweinereien" })

@app.route("/")
def get_index():
    app.logger.info("index.html request")
    # return static_folder

    return app.send_static_file("index.html")

@app.route("/status")
def get_status():
    # app.logger.info("status request")
    return flask.jsonify(dict(
        users=[user for user in users.find({})], 
        tags=[tag for tag in tags.find({})],
        queue=[qu for qu in queue.find({})], 
        lobbies=[lobby for lobby in lobbies.find({})], 
        running_matches=[match for match in running_matches.find({})], 
        evaluations=[evaluation for evaluation in evaluations.find({})]
    ))

def matches(user_id):   
    # user's queue 
    res = queue.find_one({'USER_ID' : user_id})

    return queue.find( {
        "LOC" : {
         "$maxDistance" : 1000, # 1km radius
         "$near" : [float(res['LOC']['LONGITUDE']), float(res['LOC']['LATITUDE'])]
        },
        "MATCH_TAG" : res["MATCH_TAG"]
    } )

def sanitize_loc(loc):
    loc['LONGITUDE'] = float(loc['LONGITUDE'])
    loc['LATITUDE'] = float(loc['LATITUDE'])
    return loc

def sanitize_tag(tag):
    return str(tag).lower()

def try_to_match_user(user_id):
    # find the nearest other queues within 1 km
    local_matches = matches(user_id)
    if (local_matches.count() >= 3):
        # generatue UID
        uid = ObjectId()
        # remove them
        for qu in local_matches:
            queue.remove(qu)
            qu['STATUS'] = 'OPEN'
            qu['MATCH_ID'] = uid
            lobbies.insert(qu)

            # Update 
            users.update({
                'USER_ID' : qu['USER_ID']}, {
                '$set' : {
                    'STATUS' : 'LOBBY'
                }})

        return {'STATUS':'MATCH_FOUND'} # new lobby object
    else:
        return {'STATUS':'WAIT'}

@app.route("/queue", methods=['POST'])
def post_queue():
    data = json.loads(request.data)

    app.logger.info("/queue")
    app.logger.info(data)

    user_id = data['USER_ID']
    match_tag = sanitize_tag(data['MATCH_TAG'])  # bier,kaffee,pizza,kochen
    time_left = data['TIME_LEFT']  

    user = users.find_one({'USER_ID' : user_id})
    if user is None:
        user = {
            'USER_ID' : user_id,
            'LOC' : sanitize_loc(data['LOC']),
            'USER_NAME' : data['USER_NAME'],
            'STATUS' : 'QUEUED'
            }
        app.logger.info("Inserting user" + user['USER_NAME'])
        users.insert(user)
    else:
        # Update 
        users.update({
            'USER_ID' : user_id}, {
            '$set' : {
                'LOC' : sanitize_loc(data['LOC']),
                'USER_NAME' : data['USER_NAME']
            }})

    # if the user is in the lobby, notify him that he is found
    if user['STATUS'] == 'LOBBY':
        return flask.jsonify({'STATUS':'MATCH_FOUND'})

    # if the user was offline, he is now online
    if user['STATUS'] == 'OFFLINE':
        users.update({
            'USER_ID' : user_id
            }, {'$set' : {'STATUS':'QUEUED'}})

    # if he was offline or queued, create or update the queue
    if user['STATUS'] in ['OFFLINE', 'QUEUED']:
        # update queue
        if queue.find_one({'USER_ID' : user_id}) is None:
            queue.insert({'USER_ID' : user_id,'TIME_LEFT' : time_left, 'MATCH_TAG' : match_tag, 'LOC' : sanitize_loc(data['LOC'])})
        else:
            queue.update({'USER_ID' : user_id}, {'$set' : {'TIME_LEFT' : time_left, 'MATCH_TAG' : match_tag, 'LOC' : sanitize_loc(data['LOC'])}})
    
        # update the geolocation index
        queue.ensure_index([('LOC', pymongo.GEO2D)])

        # try to match
        return flask.jsonify( try_to_match_user(user_id) )

    # if we arrive here, something went wrong
    return flask.jsonify({'STATUS':'INVALID'})

@app.route("/lobby", methods=['POST'])
def show_lobby():
    """ Return information about the accept state of the other two people """
    data = json.loads(request.data)
    user_id = data['USER_ID']

    app.logger.info("/lobby")
    app.logger.info(data)

    lobby = lobbies.find_one({'USER_ID' : user_id})
    if lobby is not None:
        group = lobbies.find({'MATCH_ID' : lobby['MATCH_ID']})
        others = []
        for person in group:
            if person['USER_ID'] != user_id:
                others.append(person)
        return flask.jsonify({'STATUS':lobby['STATUS'], 'OTHERS' : others })
    else:
        return flask.jsonify({'STATUS':'INVALID'})

@app.route("/accept", methods=['POST'])
def accept():
    """ Accept and simultaneously check if everyone has accepted already """

    data = json.loads(request.data)
    user_id = data['USER_ID']

    app.logger.info("/accept")
    app.logger.info(data)
    # is the user in a lobby? 
    lobby = lobbies.find_one({'USER_ID' : user_id})
    if lobby is not None:
        match_id = lobby['MATCH_ID']
        group = lobbies.find({'MATCH_ID' : match_id})
        others = []
        for person in group:
            if person['USER_ID'] != user_id:
                others.append(person)
        group.rewind()

        # if already running, say so:
        if running_matches.find_one({'USER_ID' : user_id}):
            return flask.jsonify({'STATUS':'RUNNING', 'OTHERS':others})

        # set flag to accepted
        lobbies.update({'USER_ID' : user_id},
        {    
            '$set' : {
                'STATUS' : 'ACCEPTED'
            }
        })

        # check if everone has accepted
        group = lobbies.find({'MATCH_ID' : match_id})
        accepted = True
        user_ids = []
        for person in group:
            user_ids.append(person['USER_ID'])
            app.logger.info(person['USER_ID'] + " - STATUS: " +person['STATUS'])
            if person['STATUS']  != 'ACCEPTED':
                accepted = False
        group.rewind()

        # if they all have accepted, remove them and add them to the running matches
        if (accepted):
            users.update({'USER_ID' : {'$in' : user_ids}}, {'$set' : {'STATUS':'RUNNING'}}, upsert=False, multi=True)
            for person in group:
                running_matches.insert({'USER_ID':person['USER_ID'], 'MATCH_ID':person['MATCH_ID'], 'MATCH_TAG':person['MATCH_TAG']})
            # remove all from lobby
            lobbies.remove({'MATCH_ID' : match_id })
            return flask.jsonify({'STATUS':'RUNNING', 'OTHERS':others})
        else:
            app.logger.info("Not everyone has accepted ...")
            return flask.jsonify({'STATUS':'OPEN', 'OTHERS':others})

    # if we arrive here, something went wrong.
    return flask.jsonify( { 'STATUS' : 'INVALID' } )


@app.route("/addtag", methods=['POST'])
def post_add_tag():
    data = json.loads(request.data)
    user_id = data['USER_ID']


    app.logger.info("/addtag")
    app.logger.info(data)

    if users.find_one({'USER_ID' : user_id}) is None:
        users.insert({'USER_ID' : user_id, 'LOC' : sanitize_loc(data['LOC']), 'USER_NAME' : data['USER_NAME']})
    else:
        users.update({'USER_ID' : user_id}, {'$set' : {'LOC' : sanitize_loc(data['LOC']), 'USER_NAME' : data['USER_NAME']}})
        

    match_tag = sanitize_tag(data['MATCH_TAG'])
    # if the user is not enqueued right now, add him/her
    
    if tags.find_one({'MATCH_TAG' : match_tag}) is None:
        tags.insert({ 'MATCH_TAG' : match_tag })

    return flask.jsonify({'STATUS':'OKAY'})

@app.route("/searchtag", methods=['POST'])
def post_search_tag():
    data = json.loads(request.data)


    app.logger.info("/searchtag")
    app.logger.info(data)

    match_tag = sanitize_tag(data['MATCH_TAG'])  # bier,kaffee,pizza,kochen

    user_id = data['USER_ID']

    if not "USER_NAME" in data.keys():
        data['USER_NAME'] = "server got no username!"

    if users.find_one({'USER_ID' : user_id}) is None:
        users.insert({'USER_ID' : user_id, 'LOC' : sanitize_loc(data['LOC']), 'USER_NAME' : data['USER_NAME'], 'STATUS':'OFFLINE'})
    else:
        users.update({'USER_ID' : user_id}, {'$set' : {'LOC' : sanitize_loc(data['LOC']), 'USER_NAME' : data['USER_NAME']}})
    

    foundtags = tags.find({'MATCH_TAG' : {'$regex': '.*'+match_tag+'.*'}})

    result = []
    for tag in foundtags:
        result.append(tag['MATCH_TAG'])

    # TODO: fuzzy search
    return flask.jsonify({'RESULTS' : result})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

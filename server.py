# -*- coding: utf-8 -*- 
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
file_handler = RotatingFileHandler(os.environ['MORE_PEOPLE_LOG'], maxBytes=1024 * 1024 * 100, backupCount=20)
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
app.logger.addHandler(file_handler)

app.logger.setLevel(logging.INFO)
api = flask.ext.restful.Api(app)

import pymongo
from pymongo import MongoClient
mongoclient, db, queue, tags = None, None, None, None
url = os.environ['MORE_PEOPLE_DB']
mongoclient = MongoClient(url)

db = mongoclient['matchmaking']
tags = db['tags']
users = db['users']
queue = db['queue']
lobbies = db['lobbies']
matches = db['matches']
evaluations = db['evaluations']

users.remove({})
queue.remove({})
tags.remove({})
lobbies.remove({})
matches.remove({})
evaluations.remove({})

tags.insert({ 'MATCH_TAG' : "kaffee" })
tags.insert({ 'MATCH_TAG' : "bier" })
tags.insert({ 'MATCH_TAG' : "kochen" })
tags.insert({ 'MATCH_TAG' : "pizza" })
tags.insert({ 'MATCH_TAG' : "schweinereien" })


def sanitize_loc(loc):
    loc['LONGITUDE'] = float(loc['LONGITUDE'])
    loc['LATITUDE'] = float(loc['LATITUDE'])
    return loc

def sanitize_tag(tag):

    return tag.lower()
@app.route("/")
def get_frontend():
    app.logger.info("frontend.html request")
    # return static_folder

    return app.send_static_file("frontend.html")

@app.route("/backend/")
def get_backend():
    app.logger.info("backend.html request")
    # return static_folder

    return app.send_static_file("backend.html")

@app.route("/status")
def get_status():
    """ Returns the full server status """
    # app.logger.info("status request")
    return flask.jsonify(dict(
        users=[user for user in users.find({})], 
        tags=[tag for tag in tags.find({})],
        queue=[qu for qu in queue.find({})], 
        lobbies=[lobby for lobby in lobbies.find({})], 
        matches=[match for match in matches.find({})], 
        evaluations=[evaluation for evaluation in evaluations.find({})]
    ))


@app.route("/reset")
def get_reset_server():
    users.remove({})
    queue.remove({})
    tags.remove({})
    lobbies.remove({})
    matches.remove({})
    evaluations.remove({})
    return flask.jsonify({'STATUS' : 'OKAY'})

def offline_response(user):
    """ Response if user is offline """
    return flask.jsonify({'STATE' : 'OFFLINE'})

def queued_response(user):
    """ Response if user if currently queued """
    # get queue item
    user_id = user['USER_ID']
    qu = queue.find_one({'USER_ID' : user_id})
    return flask.jsonify({
        'STATE' : 'QUEUED',
        'MATCH_TAG' : qu['MATCH_TAG']
        })

def open_response(user):
    """ Response if user is currently in a lobby and open """
    user_id = user['USER_ID']
    lobby = lobbies.find_one({'USER_ID' : user_id})
    # others in the lobby
    others = []
    for user in lobbies.find({'MATCH_ID' : lobby['MATCH_ID']}, upserv=False, multi=True):
        if user['USER_ID'] != user_id:
            others.append(user)

    return flask.jsonify({
        'STATE' : 'OPEN',
        'MATCH_TAG' : lobby['MATCH_TAG'],
        'OTHERS' : others
        })

def accepted_response(user):
    """ Response if user is currently in a lobby and open """
    user_id = user['USER_ID']
    lobby = lobbies.find_one({'USER_ID' : user_id})
    # others in the lobby
    others = []
    for user in lobbies.find({'MATCH_ID' : lobby['MATCH_ID']}, upserv=False, multi=True):
        if user['USER_ID'] != user_id:
            others.append(user)

    return flask.jsonify({
        'STATE' : 'ACCEPTED',
        'MATCH_TAG' : lobby['MATCH_TAG'],
        'OTHERS' : others
        })

def running_response(user):
    """ Response if user is in a running match """
    user_id = user['USER_ID']
    match = matches.find_one({'USER_ID' : user_id})
    if match is None:
        raise ">>>> AHHH MATCH IS NONE <<<<"
    # others in the lobby
    others = []
    for user in matches.find({'MATCH_ID' : match['MATCH_ID']}, upserv=False, multi=True):
        if user['USER_ID'] != user_id:
            others.append(user)

    return flask.jsonify({
        'STATE' : 'RUNNING',
        'OTHERS' : others
        })

def finished_response(user):
    """ Response if user has finished his match """
    user_id = user['USER_ID']
    match = matches.find_one({'USER_ID' : user_id})
    # others in the lobby
    others = []
    for user in matches.find({'MATCH_ID' : match['MATCH_ID']}, upserv=False, multi=True):
        if user['USER_ID'] != user_id:
            others.append(user)

    return flask.jsonify({
        'STATE' : 'FINISHED',
        'OTHERS' : others
        })

def cancelled_response(user):
    """ Resposne if user is in cancelled state """
    return flask.jsonify({
        'STATE' : 'CANCELLED',
        'SERVERMESSAGE' : user['SERVERMESSAGE']
        })

response_map = {
    'OFFLINE' : offline_response,
    'QUEUED' : queued_response,
    'OPEN' : open_response,
    'ACCEPTED' : accepted_response,
    'RUNNING' : running_response,
    'FINISHED' : finished_response,
    'CANCELLED' : cancelled_response
}

def user_response(user_id):
    """ Generates a response dependent on the current user state """
    user = users.find_one({'USER_ID':user_id})
    if user is None:
        raise ">>>>> AHHH USER IS NONE <<<<"
    # creates a response depending on the state of the user
    state = user['STATE']
    # switch statement
    app.logger.info("User Response: " + user['USER_NAME'] + " is " + state)
    return response_map[state](user)

@app.route("/state", methods=['POST'])
def get_userstate():
    """ Returns the state of the given user so the client can reconstruct the session """

    app.logger.info("/state")
    data = json.loads(request.data)
    app.logger.info(data)
    user_id = data['USER_ID']
    app.logger.info(user_id)
    # Create the user if he does not exist yet
    user = users.find_one({'USER_ID' : user_id})
    if user is None:
        app.logger.info("User is None")
        user = {
            'USER_ID' : user_id,
            'LOC' : sanitize_loc(data['LOC']),
            'USER_NAME' : data['USER_NAME'],
            'STATE' : 'OFFLINE', # initially offline, set to queued later!
            'SERVERMESSAGE' : ''
            }
        app.logger.info("Inserting user")
        app.logger.info(user)
        users.insert(user)
    else:   
        app.logger.info("User is updated")
        # Update 
        users.update({'USER_ID' : user_id},
           {
            '$set' : {
                'LOC' : sanitize_loc(data['LOC']),
                'USER_NAME' : data['USER_NAME']
            }})

    app.logger.info("Finished, sending response")

    return user_response(data['USER_ID'])

@app.route("/search", methods=['POST'])
def get_tag():
    """ Returns tags similar to the given tag """

    app.logger.info("/search")
    data = json.loads(request.data)

    app.logger.info(data)
    tag = sanitize_tag(data['MATCH_TAG'])
    match_tag = sanitize_tag(tag)  # bier,kaffee,pizza,kochen

    foundtags = tags.find({'MATCH_TAG' : {'$regex': '.*'+match_tag+'.*'}})

    result = []
    for tag in foundtags:
        result.append(tag['MATCH_TAG'])


    app.logger.info("sending results")
    app.logger.info(result)
    # TODO: fuzzy search
    return flask.jsonify({'RESULTS' : result})

def try_to_match(user_id):
    # find the nearest other queues within 1 km
    res = queue.find_one({'USER_ID' : user_id})
    if res is None:
        return;
    app.logger.info('try_to_match')
    app.logger.info(res)
    local_matches = queue.find( {
        "LOC" : {
         "$maxDistance" : 1000, # 1km radius
         "$near" : [float(res['LOC']['LONGITUDE']), float(res['LOC']['LATITUDE'])]
        },
        "MATCH_TAG" : res["MATCH_TAG"]
    } )

    if (local_matches.count() >= 3):
        app.logger.info("!!! MATCH !!!")
        # generatue UID
        uid = ObjectId()
        # remove them
        for qu in local_matches:

            # remove queue entry
            queue.remove({'USER_ID' : qu['USER_ID']})

            # Create lobby entry
            qu['STATE'] = 'OPEN'
            qu['MATCH_ID'] = uid
            lobbies.insert(qu)

            # Update user
            users.update({
                'USER_ID' : qu['USER_ID']}, {
                '$set' : {
                    'STATE' : 'OPEN'
                }})
    else:
        app.logger.info("No Match")

@app.route("/queue", methods=["GET"])
def get_queue():
    """ Returns list of nearby queues """

    longitude = float(request.args['LON'])
    latitude = float(request.args['LAT'])
    radius = int(request.args['RAD'])

    local_results = queue.find( {
        "LOC" : {
         "$maxDistance" : radius, # radius in meters
         "$near" : [longitude, latitude]
        }
    } )

    #return flask.jsonify({})
    return flask.jsonify(dict(results=[result for result in local_results]))

@app.route("/queue", methods=["POST"])
def post_queue():
    """ Enqueues the user, create him if he does not exist yet, and adds the tag to the known tags. """

    app.logger.info("/queue")

    data = json.loads(request.data)

    app.logger.info(data)
    user_id = data['USER_ID']
    match_tag = sanitize_tag(data['MATCH_TAG'])

    # add tag to database if not existent yet
    if tags.find_one({'MATCH_TAG' : match_tag}) is None:
        tags.insert({'MATCH_TAG' : match_tag})

    # Create the user if he does not exist yet
    user = users.find_one({'USER_ID' : user_id})
    if user is None:
        user = {
            'USER_ID' : user_id,
            'LOC' : sanitize_loc(data['LOC']),
            'USER_NAME' : data['USER_NAME'],
            'STATE' : 'OFFLINE', # initially offline, set to queued later!
            'SERVERMESSAGE' : ''
            }
        app.logger.info("Inserting user")
        app.logger.info(user)
        users.insert(user)
    else:   
        # Update 
        users.update({'USER_ID' : user_id},
           {
            '$set' : {
                'LOC' : sanitize_loc(data['LOC']),
                'USER_NAME' : data['USER_NAME']
            }})

    # If the user is in offline mode, create queue and set user state to queued
    if (user['STATE'] == 'OFFLINE'):
        queue.insert({'USER_ID' : user_id, 'MATCH_TAG' : match_tag, 'LOC' : sanitize_loc(data['LOC']), 'USER_NAME' : user['USER_NAME']})
        users.update({'USER_ID':user['USER_ID']}, { '$set' : {'STATE' : 'QUEUED'}})

    # If he is already queued, update the queue entry
    if (user['STATE'] == 'QUEUED'):
        queue.update({'USER_ID' : user_id}, {'$set' : {'MATCH_TAG' : match_tag, 'LOC' : sanitize_loc(data['LOC'])}})


    # refresh user
    user = users.find_one({'USER_ID' : user_id})

    if(user['STATE'] == 'QUEUED'):

        # Update the geolocation index
        queue.ensure_index([('LOC', pymongo.GEO2D)])

        # Try to match the users
        try_to_match(user_id)

    # Update the geolocation index
    queue.ensure_index([('LOC', pymongo.GEO2D)])

    # Create response dependent on user state
    return user_response(user_id)

@app.route("/lobby", methods=['GET'])
def get_lobby():
    """ List participants in the lobby """

    user_id = request.args['USER_ID']

    lobby = lobbies.find_one({
        'USER_ID' : user_id
        })

    if lobby is None:
        return flask.jsonify(dict(participants=[]))

    match_id = lobby['MATCH_ID']

    match_lobbies = lobbies.find({
        'MATCH_ID' : match_id
        })

    participants = []
    for match_lobby in match_lobbies:
        match_user = users.find_one({'USER_ID' : match_lobby['USER_ID']})
        participants.append(match_user)

    return flask.jsonify(dict(participants=participants))

@app.route("/confirmcancel", methods=['POST'])
def post_cancelconfirm():
    """ Confirm the cancel. """
    data = json.loads(request.data)

    app.logger.info("/confirmcancel")
    app.logger.info(data)
    user_id = data['USER_ID']

    user = users.find_one({'USER_ID' : user_id})

    if user['STATE'] == 'CANCELLED':
        # set state to cancelled
        users.update({'USER_ID' : user['USER_ID']}, {'$set' : {'STATE' : 'OFFLINE'}})

    return user_response(user_id)

@app.route("/cancel", methods=["POST"])
def post_cancel():
    """ Cancels, if allowed. """
    data = json.loads(request.data)

    app.logger.info("/cancel")
    app.logger.info(data)
    user_id = data['USER_ID']

    user = users.find_one({'USER_ID' : user_id})


    if user['STATE'] == 'QUEUED':        
        # remove queue entry
        queue.remove({'USER_ID' : user['USER_ID']})

    if user['STATE'] == 'OPEN':
        # from open switch to CANCELLED state
        lobby = lobbies.find_one({'USER_ID' : user_id})
        match_id = lobby['MATCH_ID']

        # get user id_s
        u = []
        for lobby_entry in lobbies.find({'MATCH_ID' : match_id}):
            u.append(lobby_entry['USER_ID'])
        # remove match entries
        lobbies.remove({'MATCH_ID' : match_id})
        # set user states to cancelled and message accordingly
        users.update({'USER_ID' : {'$in' : u}}, {'$set' : {'STATE' : 'CANCELLED', 'SERVERMESSAGE' : 'Ein Nutzer hat das Match abgebrochen :('}})
    

    # the cancelling user himself directly goes to OFFLINE
    if user['STATE'] in ['QUEUED', 'OPEN']:  
        users.update({'USER_ID' : user['USER_ID']}, {'$set' : {'STATE' : 'OFFLINE'}})

    return user_response(user_id)

@app.route("/accept", methods=["POST"])
def post_accept():
    """ The user accepts a match """

    app.logger.info("/accept")

    data = json.loads(request.data)
    user_id = data['USER_ID']

    app.logger.info(data)

    user = users.find_one({'USER_ID' : user_id})

    if user['STATE'] == 'OPEN':
        # Set his state to accepted
        users.update({'USER_ID' : user_id}, {'$set' : {'STATE' : 'ACCEPTED'} })

        # Set lobby state to accepted
        lobbies.update({'USER_ID' : user_id}, {'$set' : {'STATE' : 'ACCEPTED'}})
        # get user's match ide
        match_id = lobbies.find_one({'USER_ID' : user_id})['MATCH_ID']

        # check if everone in the lobby has accepted
        group = lobbies.find({'MATCH_ID' : match_id})
        accepted = True
        user_ids = []
        for person in group:
            user_ids.append(person['USER_ID'])
            app.logger.info(person['USER_ID'] + " - STATE: " +person['STATE'])
            if person['STATE']  != 'ACCEPTED':
                accepted = False

        # TODO: send GCM message to all participants

        if accepted:
            app.logger.info("Inserting RUNNING MATCH")
            # If everyone has accepted, set them to running,
            users.update({'USER_ID' : {'$in' : user_ids}}, {'$set' : {'STATE' : 'RUNNING'}}, upsert=False, multi=True)

            # Delete lobby entries
            lobbies.remove({'MATCH_ID' : match_id})

            # And create match entries
            for user_id in user_ids:
                matches.insert({'USER_ID' : user_id, 'MATCH_ID' : match_id, 'STATE' : 'RUNNING'})

    # create user response
    return user_response(user_id)

@app.route("/chat/<match_id>", methods=["GET"])
def get_chat():
    """ Returns the chat of the match """
    return None

@app.route("/chat/<match_id>", methods=["POST"])
def post_chat():
    """ The user sends a chat message """
    # TODO
    return None

@app.route("/finish", methods=["POST"])
def post_finish():
    data = json.loads(request.data)
    user_id = data['USER_ID']

    user = users.find_one({'USER_ID' : user_id})
    app.logger.info("finish user " + str(user_id))
    app.logger.info("finish user state " + str(user['STATE']))
    if user['STATE'] == 'RUNNING':
        # set user state to finished
        users.update({'USER_ID' : user_id}, {'$set': {'STATE' : 'FINISHED'}})
        # set match entry to finished
        matches.update({'USER_ID' : user_id}, {'$set': {'STATE' : 'FINISHED'}})
        pass

    app.logger.info("sucessfully finished user " + str(user_id))
    return user_response(user_id)

@app.route("/evaluate", methods=["POST"])
def post_evaluation():
    data = json.loads(request.data)
    user_id = data['USER_ID']

    user = users.find_one({'USER_ID' : user_id})

    # Only accept evaluation if in finished state
    if user['STATE'] == 'FINISHED':
        # set user state to offline
        # set user state to finished
        users.update({'USER_ID' : user_id}, {'$set': {'STATE' : 'OFFLINE'}})

        # remove match entry
        matches.remove({'USER_ID' : user_id})

        # insert evaluation entry
        evaluations.insert({'USER_ID' : user_id, 'EVALUATION' : data['EVALUATION']})

    return user_response(user_id)
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

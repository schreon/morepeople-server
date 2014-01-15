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


@app.route("/")
def get_index():
    app.logger.info("index.html request")
    # return static_folder

    return app.send_static_file("index.html")

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

def offline_response(user_id):
	""" Response if user is offline """
	return flask.jsonify({'STATUS' : 'OFFLINE'})

def queued_response(user_id):
	""" Response if user if currently queued """
	# get queue item
	qu = queue.find_one({'USER_ID' : user_id})
	return flask.jsonify({
		'STATUS' : 'QUEUED',
		'MATCH_TAG' : qu['MATCH_TAG'],
		'TIME_LEFT' : qu['TIME_LEFT']
		})

def open_response(user_id):
	""" Response if user is currently in a lobby and open """
	lobby = lobbies.find_one({'USER_ID' : user_id})
	# others in the lobby
	others = []
	for user in lobbies.find({'MATCH_ID' : lobby['MATCH_ID']}, upserv=False, multi=True):
		if user['USER_ID'] != user_id:
			others.append(user)

	return flask.jsonify({
		'STATUS' : 'OPEN',
		'OTHERS' : others,
		'TIME_LEFT' : lobby['TIME_LEFT']
		})

def accepted_response(user_id):
	""" Response if user is currently in a lobby and open """
	lobby = lobbies.find_one({'USER_ID' : user_id})
	# others in the lobby
	others = []
	for user in lobbies.find({'MATCH_ID' : lobby['MATCH_ID']}, upserv=False, multi=True):
		if user['USER_ID'] != user_id:
			others.append(user)

	return flask.jsonify({
		'STATUS' : 'ACCEPTED',
		'OTHERS' : others,
		'TIME_LEFT' : lobby['TIME_LEFT']
		})

def running_response(user_id):
	""" Response if user is in a running match """
	match = matches.find_one({'USER_ID' : user_id})
	# others in the lobby
	others = []
	for user in matches.find({'MATCH_ID' : lobby['MATCH_ID']}, upserv=False, multi=True):
		if user['USER_ID'] != user_id:
			others.append(user)

	return flask.jsonify({
		'STATUS' : 'RUNNING',
		'OTHERS' : others
		})

def finished_response(user_id):
	""" Response if user has finished his match """
	match = matches.find_one({'USER_ID' : user_id})
	# others in the lobby
	others = []
	for user in matches.find({'MATCH_ID' : lobby['MATCH_ID']}, upserv=False, multi=True):
		if user['USER_ID'] != user_id:
			others.append(user)

	return flask.jsonify({
		'STATUS' : 'FINISHED',
		'OTHERS' : others
		})

def cancelled_response(user_id):
	""" Resposne if user is in cancelled state """
	user = users.find_one({'USER_ID' : user_id})
	return flask.jsonify({
		'STATUS' : 'CANCELLED',
		'SERVERMESSAGE' : user['SERVERMESSAGE']
		})

def user_response(user_id):
	""" Generates a response dependent on the current user state """
	user = users.find_one({'USER_ID':user_id})
	# creates a response depending on the state of the user
	state = user['STATE']
	# switch statement
	return {
		'OFFLINE' : offline_response(user_id),
		'QUEUED' : queued_response(user_id),
		'OPEN' : open_response(user_id),
		'ACCEPTED' : accepted_response(user_id),
		'RUNNING' : running_response(user_id),
		'FINISHED' : finished_response(user_id),
		'CANCELLED' : cancelled_response(user_id)
	}[state]

@app.route("/state/<user_id>")
def get_userstate(user_id):
	""" Returns the state of the given user so the client can reconstruct the session """
	return user_response(user_id)

@app.route("/search/<tag>")
def get_tag(tag):
	""" Returns tags similar to the given tag """

    app.logger.info("/search/"+str(tag))
    app.logger.info(data)

    match_tag = sanitize_tag(tag)  # bier,kaffee,pizza,kochen

    foundtags = tags.find({'MATCH_TAG' : {'$regex': '.*'+match_tag+'.*'}})

    result = []
    for tag in foundtags:
        result.append(tag['MATCH_TAG'])

    # TODO: fuzzy search
    return flask.jsonify({'RESULTS' : result})

def try_to_match_user(user_id):
    # find the nearest other queues within 1 km
    local_matches = queue(user_id)
    if (local_matches.count() >= 3):
        # generatue UID
        uid = ObjectId()
        # remove them
        for qu in local_matches:
        	# Remove queue entry
            queue.remove(qu)

            # Create lobby entry
            qu['STATUS'] = 'OPEN'
            qu['MATCH_ID'] = uid
            lobbies.insert(qu)

            # Update user
            users.update({
                'USER_ID' : qu['USER_ID']}, {
                '$set' : {
                    'STATUS' : 'OPEN'
                }})


@app.route("/queue", methods="POST")
def post_queue():
	""" Enqueues the user, create him if he does not exist yet, and adds the tag to the known tags"""
    data = json.loads(request.data)

    app.logger.info("/queue")
    app.logger.info(data)

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
        app.logger.info("Inserting user " + user['USER_NAME'])
        users.insert(user)
    else:
        # Update 
        users.update({
            'USER_ID' : user_id}, {
            '$set' : {
                'LOC' : sanitize_loc(data['LOC']),
                'USER_NAME' : data['USER_NAME']
            }})

    # If the user is in offline mode, create queue and set user state to queued
    if (user['STATE'] == 'OFFLINE'):
        queue.insert({'USER_ID' : user_id,'TIME_LEFT' : time_left, 'MATCH_TAG' : match_tag, 'LOC' : sanitize_loc(data['LOC'])})
    	users.update({'USER_ID':user['USER_ID']}, {'STATE' : 'QUEUED'})

    # If he is already queued, update the queue entry
    if (user['STATE'] == 'QUEUED'):
        queue.update({'USER_ID' : user_id}, {'$set' : {'TIME_LEFT' : time_left, 'MATCH_TAG' : match_tag, 'LOC' : sanitize_loc(data['LOC'])}})

    # Update the geolocation index
    queue.ensure_index([('LOC', pymongo.GEO2D)])

    # Try to match the users
    try_to_match(user['USER_ID'])

	# Create response dependent on user state
	return user_response(user['USER_ID'])

@app.route("/cancel", methods="POST")
def post_cancel():
	""" Cancels, if allowed. """
    user = users.find_one({'USER_ID' : user_id})

    if user['STATE'] == 'QUEUED':
    	# set state to cancelled
    	users.update({'USER_ID' : user['USER_ID']}, {'STATUS' : 'CANCELLED'})
    	# remove queue entry
    	queue.remove({'USER_ID' : user['USER_ID']})

    if user['STATE'] == 'OPEN':
    	match_id = queue.find_one({'USER_ID' : user['USER_ID']})['MATCH_ID']

    	# get user id_s
    	u = []
    	for queue_entry in queue.find({'MATCH_ID' : match_id}):
    		u.append(queue_entry['USER_ID'])
    	# remove queue entries
    	queue.remove({'MATCH_ID' : match_id})
    	# set user states to cancelled and message accordingly
    	users.update({'USER_ID' : {'$in' : u}}, {'STATUS' : 'CANCELLED', 'SERVERMESSAGE' : 'Ein Nutzer hat das Match abgebrochen :('})
    
    # else, do nothing.

	return user_response(user['USER_ID'])

@app.route("/accept", methods="POST")
def post_accept():
	""" The user accepts a match """
	# TODO
	return None

@app.route("/chat/<match_id>", methods="GET")
def get_chat():
	""" Returns the chat of the match """
	return None

@app.route("/chat/<match_id>", methods="POST")
def post_chat():
	""" The user sends a chat message """
	# TODO
	return None

@app.route("/finish")


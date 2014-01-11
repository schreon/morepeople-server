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
import json

static_folder = os.path.join('public')

app = Flask("MatchmakingClient",
            static_folder=static_folder, static_url_path='')

api = flask.ext.restful.Api(app)

USER_ID = "USER_ID"
MATCH_TAG = "MATCH_TAG"
TIME_LEFT = "TIME_LEFT"
TIMESTAMP = "TIMESTAMP"
STATUS = "STATUS"
OKAY = "OKAY"
RESULTS = "RESULTS"

from pymongo import MongoClient
mongoclient, db, queue, tags = None, None, None, None
def connect(url):
    global mongoclient, db, queue, tags
    mongoclient = MongoClient(url)

    db = mongoclient['matchmaking']
    queue = db['queue']
    tags = db['tags']

@app.route("/")
def get_index():
    # return static_folder
    return app.send_static_file('index.html')

@app.route("/queue", methods=['POST'])
def post_queue():
    data = json.loads(request.data)
    user_id = data[USER_ID]
    match_tag = data[MATCH_TAG]  # bier,kaffee,pizza,kochen
    time_left = data[TIME_LEFT]  
    # if the user is not enqueued right now, add him/her
    if queue.find_one({USER_ID : user_id}) is None:
        queue.insert(data)
    else:
        queue.update({USER_ID : user_id}, {'$set' : {TIME_LEFT : time_left}})

    # TODO: proper queue handling
    return flask.jsonify({MATCH_ID: 'test_id_1234'})


@app.route("/addtag", methods=['POST'])
def post_add_tag():
    data = json.loads(request.data)
    match_tag = data[MATCH_TAG]
    # if the user is not enqueued right now, add him/her
    
    if tags.find_one({MATCH_TAG : match_tag}) is None:
        tags.insert({ MATCH_TAG : match_tag })

    return flask.jsonify({STATUS:OKAY})

@app.route("/searchtag", methods=['POST'])
def post_search_tag():
    data = json.loads(request.data)
    match_tag = data[MATCH_TAG]  # bier,kaffee,pizza,kochen

    foundtags = tags.find({MATCH_TAG : {'$regex': '.*'+match_tag+'.*'}})

    result = []
    for tag in foundtags:
        result.append(tag[MATCH_TAG])

    # TODO: fuzzy search
    return flask.jsonify({RESULTS : result})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

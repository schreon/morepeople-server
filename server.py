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

MATCH_BEER = "MATCH_TYPE_BEER"
MATCH_COFFEE = "MATCH_TYPE_COFFEE"
MATCH_COOKING = "MATCH_TYPE_COOKING"
MATCH_PIZZA = "MATCH_TYPE_PIZZA"
MATCH_ID = "MATCH_ID"
USER_ID = "USER_ID"
MATCH_TYPE = "MATCH_TYPE"
TIME_LEFT = "TIME_LEFT"
TIMESTAMP = "TIMESTAMP"

from pymongo import MongoClient
mongoclient, db, queue = None, None, None
def connect(url):
    global mongoclient, db, queue
    mongoclient = MongoClient(url)

    db = mongoclient['matchmaking']
    queue = db['queue']

@app.route("/")
def get_index():
    # return static_folder
    return app.send_static_file('index.html')


@app.route("/queue", methods=['POST'])
def post_register():
    data = json.loads(request.data)
    user_id = data[USER_ID]
    match_type = data[MATCH_TYPE]  # bier,kaffee,pizza,kochen
    time_left = data[TIME_LEFT]  
    # if the user is not enqueued right now, add him/her
    if queue.find_one({USER_ID : user_id}) is None:
        queue.insert(data)
    else:
        queue.update({USER_ID : user_id}, {'$set' : {TIME_LEFT : time_left}})
    return flask.jsonify({MATCH_ID: 'test_id_1234'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

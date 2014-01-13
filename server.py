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



import logging
from logging.handlers import RotatingFileHandler
file_handler = RotatingFileHandler(os.environ['BOCK_LOG'], maxBytes=1024 * 1024 * 100, backupCount=20)
file_handler.setLevel(logging.ERROR)
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
queue = db['queue']
tags = db['tags']
users = db['users']

users.remove({})
queue.remove({})
tags.remove({})

tags.insert({ 'MATCH_TAG' : "kaffee" })
tags.insert({ 'MATCH_TAG' : "bier" })
tags.insert({ 'MATCH_TAG' : "kochen" })
tags.insert({ 'MATCH_TAG' : "pizza" })
tags.insert({ 'MATCH_TAG' : "schweinereien" })

@app.route("/")
def get_index():
    app.logger.info("index.html request")
    # return static_folder

    from flask import render_template
    return render_template('index.html',users=users.find({}), tags=tags.find({}))

def nearest_queues(user_id):   
    # user's queue 
    qu = queue.find_one({'USER_ID' : user_id})

    return queue.find( {
        "LOC" : {
         "$maxDistance" : 1000.0 / 111.12,
         "$near" : [float(qu['LOC']['LONGITUDE']), float(qu['LOC']['LATITUDE'])]
    } } )




def try_to_match_user(user_id):
    # get the users queue entry
    qu = queue.find_one({'USER_ID' : user_id})

    # find the nearest other queues within 1 km


@app.route("/queue", methods=['POST'])
def post_queue():
    data = json.loads(request.data)
    user_id = data['USER_ID']
    match_tag = data['MATCH_TAG']  # bier,kaffee,pizza,kochen
    time_left = data['TIME_LEFT']  

    if users.find_one({'USER_ID' : user_id}) is None:
        users.insert({
            'USER_ID' : user_id,
            'LOC' : data['LOC'],
            'USER_NAME' : data['USER_NAME']
            })
    else:
        users.update({
            'USER_ID' : user_id}, {
            '$set' : {
                'LOC' : data['LOC'],
                'USER_NAME' : data['USER_NAME']
            }})

    # if the user is not enqueued right now, add him/her
    if queue.find_one({'USER_ID' : user_id}) is None:
        queue.insert(data)
    else:
        queue.update({'USER_ID' : user_id}, {'$set' : {'TIME_LEFT' : time_left}})

    queue.ensure_index([('LOC', pymongo.GEO2D)])

    #match_result = try_to_match_user(user_id)
    match_result = {'nothing':'nothing'}
    if match_result is None:
        return flask.jsonify(match_result)
    else:
        return flask.jsonify(match_result)


@app.route("/addtag", methods=['POST'])
def post_add_tag():
    data = json.loads(request.data)
    user_id = data['USER_ID']
    app.logger.info(data)

    if users.find_one({'USER_ID' : user_id}) is None:
        users.insert({'USER_ID' : user_id, 'LONGITUDE' : data['LONGITUDE'], 'LATITUDE' : data['LATITUDE'], 'USER_NAME' : data['USER_NAME']})
    else:
        users.update({'USER_ID' : user_id}, {'$set' : {'LONGITUDE' : data['LONGITUDE'], 'LATITUDE' : data['LATITUDE'], 'USER_NAME' : data['USER_NAME']}})
        

    match_tag = data['MATCH_TAG']
    # if the user is not enqueued right now, add him/her
    
    if tags.find_one({'MATCH_TAG' : match_tag}) is None:
        tags.insert({ 'MATCH_TAG' : match_tag })

    return flask.jsonify({'STATUS':'OKAY'})

@app.route("/searchtag", methods=['POST'])
def post_search_tag():
    data = json.loads(request.data)
    app.logger.info(data)

    match_tag = data['MATCH_TAG']  # bier,kaffee,pizza,kochen

    user_id = data['USER_ID']

    if not "USER_NAME" in data.keys():
        data['USER_NAME'] = "server got no username!"

    if users.find_one({'USER_ID' : user_id}) is None:
        users.insert({'USER_ID' : user_id, 'LONGITUDE' : data['LONGITUDE'], 'LATITUDE' : data['LATITUDE'], 'USER_NAME' : data['USER_NAME']})
    else:
        users.update({'USER_ID' : user_id}, {'$set' : {'LONGITUDE' : data['LONGITUDE'], 'LATITUDE' : data['LATITUDE'], 'USER_NAME' : data['USER_NAME']}})
        

    foundtags = tags.find({'MATCH_TAG' : {'$regex': '.*'+match_tag+'.*'}})

    result = []
    for tag in foundtags:
        result.append(tag['MATCH_TAG'])

    # TODO: fuzzy search
    return flask.jsonify({'RESULTS' : result})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

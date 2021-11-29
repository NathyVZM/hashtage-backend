# app.py

from flask import Flask, session
from flask_mongoengine import MongoEngine
from flask_cors import CORS
from config import *
import os

app = Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    print('Hello World')
    return 'Hello World'

app.config.from_object(ProductionConfig)
app.secret_key = os.environ['SECRET_KEY']
app.config['MAX_CONTENT_LENGTH'] = 20 * 1000 * 1000 # 20MB


# MongoEngine
app.config['MONGODB_SETTINGS'] = { 'db': os.environ['MONGODB_DB'], 'host': os.environ['MONGODB_HOST'] }
db = MongoEngine(app)


# Enabling CORS
cors = CORS(app, supports_credentials=True)
# app.py

from flask import Flask, session
from flask_mongoengine import MongoEngine
from flask_cors import CORS
from config import *
import os

app = Flask(__name__)

app.config.from_object(ProductionConfig)
app.config['MAX_CONTENT_LENGTH'] = 20 * 1000 * 1000 # 20MB

# MongoEngine
db = MongoEngine(app)

# Enabling CORS
cors = CORS(app, supports_credentials=True)


# Blueprints
from controllers.user import user_bp

app.register_blueprint(user_bp)
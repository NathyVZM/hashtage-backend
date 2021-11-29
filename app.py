# app.py

from flask import Flask
from flask_mongoengine import MongoEngine
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from config import *
from datetime import timedelta

app = Flask(__name__)

app.config.from_object(ProductionConfig)

# MongoEngine
db = MongoEngine(app)

# JWT Configuration
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)
jwt = JWTManager(app)

# Enabling CORS
cors = CORS(app, supports_credentials=True)

# Blueprints
from controllers.user import user_bp
from controllers.post import post_bp

app.register_blueprint(user_bp)
app.register_blueprint(post_bp)
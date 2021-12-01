# app.py

from flask import Flask
from flask_mongoengine import MongoEngine
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from config import *
from datetime import timedelta
from cloudinary import config

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

# Cloudinary
config(cloud_name=os.environ['CLOUD_NAME'], api_key=os.environ['API_KEY'], api_secret=os.environ['API_SECRET'])

# Blueprints
from controllers.user import user_bp
from controllers.post import post_bp

app.register_blueprint(user_bp)
app.register_blueprint(post_bp)
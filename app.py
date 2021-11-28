from flask import Flask, session
from config import *
import os

app = Flask(__name__)

app.config.from_object(DevelopmentConfig)
app.secret_key = os.environ['SECRET_KEY']
app.config['MAX_CONTENT_LENGTH'] = 20 * 1000 * 1000 # 20MB
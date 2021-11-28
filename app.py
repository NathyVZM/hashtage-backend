from flask import Flask, session
from config import *
import os

app = Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    return 'Hello World'

app.config.from_object(ProductionConfig)
app.secret_key = os.environ['SECRET_KEY']
app.config['MAX_CONTENT_LENGTH'] = 20 * 1000 * 1000 # 20MB
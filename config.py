# config.py
import os
import certifi

class Config(object):
    DEBUG = False
    CSRF_ENABLED = False
    SECRET_KEY = os.environ['SECRET_KEY']
    MONGODB_SETTINGS = { 'host': f'{os.environ["MONGODB_HOST"]}{certifi.where()}' }


class ProductionConfig(Config):
    DEBUG = False


class DevelopmentConfig(Config):
    DEVELOPMENT = True
    DEBUT = True

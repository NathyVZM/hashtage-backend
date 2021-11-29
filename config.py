# config.py
import os
import certifi

class Config(object):
    DEBUG = False
    CSRF_ENABLED = False
    MAX_CONTENT_LENGTH = 20 * 1000 * 1000 # 20MB
    SECRET_KEY = os.environ['SECRET_KEY']
    MONGODB_SETTINGS = { 'host': f'{os.environ["MONGODB_HOST"]}{certifi.where()}' }
    JWT_SECRET_KEY = os.environ['JWT_SECRET_KEY']


class ProductionConfig(Config):
    DEBUG = False


class DevelopmentConfig(Config):
    DEVELOPMENT = True
    DEBUT = True

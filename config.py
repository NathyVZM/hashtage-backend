# config.py

class Config(object):
    DEBUG = False
    CSRF_ENABLED = False


class ProductionConfig(Config):
    DEBUG = False


class DevelopmentConfig(Config):
    DEVELOPMENT = True
    DEBUT = True

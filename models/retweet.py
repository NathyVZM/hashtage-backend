# retweet.py

from app import db

class Retweet(db.Document):
    user_id = db.ReferenceField('User', required=True)
    post_id = db.ReferenceField('Post', required=True)
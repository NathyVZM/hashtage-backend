# retweet.py

import mongoengine
from app import db

class Retweet(db.Document):
    user_id = db.ReferenceField('User', required=True, reverse_delete_rule=mongoengine.CASCADE)
    post_id = db.ReferenceField('Post', required=True, reverse_delete_rule=mongoengine.CASCADE)
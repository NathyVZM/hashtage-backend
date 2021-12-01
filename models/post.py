# post.py

import datetime

import mongoengine
from app import db

class Post(db.Document):
    author = db.ReferenceField('User', required=True, reverse_delete_rule=mongoengine.CASCADE)
    text = db.StringField(required=True, max_length=280)
    date = db.DateTimeField(default=datetime.datetime.utcnow())
    img_path = db.StringField()
    parent = db.ReferenceField('self', reverse_delete_rule=mongoengine.CASCADE)

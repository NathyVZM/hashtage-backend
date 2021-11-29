# post.py

import datetime
from app import db

class Post(db.Document):
    author = db.ReferenceField('User', required=True)
    text = db.StringField(required=True, max_length=280)
    date = db.DateTimeField(default=datetime.datetime.utcnow())
    img_path = db.StringField()
    parent = db.ReferenceField('self')

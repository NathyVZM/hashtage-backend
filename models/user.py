# user.py

from app import db

class User(db.Document):
    full_name = db.StringField(required=True, max_length=50)
    username = db.StringField(required=True, max_length=30)
    password = db.StringField(required=True, password=True)
    address = db.StringField()
    birthday = db.DateTimeField()
    bio = db.StringField()
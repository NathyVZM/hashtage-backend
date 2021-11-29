# user.py

from app import db
from flask_bcrypt import Bcrypt

bcrypt = Bcrypt()

class User(db.Document):
    full_name = db.StringField(required=True, max_length=50)
    username = db.StringField(required=True, max_length=30, unique=True)
    password = db.StringField(required=True, password=True)
    address = db.StringField()
    birthday = db.DateTimeField()
    bio = db.StringField()
    followers = db.ListField(db.ReferenceField('self'))
    following = db.ListField(db.ReferenceField('self'))

    # createPassword()
    def createPassword(password):
        return bcrypt.generate_password_hash(password).decode('utf-8')

    # verifyPassword()
    def verifyPassword(self, password):
        return bcrypt.check_password_hash(self.password, password)
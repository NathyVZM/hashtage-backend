from app import db
from flask import Blueprint
from models.user import User

user_bp = Blueprint('user_bp', __name__)

@user_bp.route('/', methods=['GET'])
def create_user():
    # users = User.objects().all()

    # for user in users:
    #     print(user.full_name)
    #     print(user.username)
    #     print(user.password)

    # return {
    #     'users': users
    # }

    user = User(full_name='Victoria Molero', username='NathyVZM', password='a password here')
    user.save()

    return user.to_json()

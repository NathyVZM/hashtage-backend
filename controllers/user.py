from app import db
from flask import Blueprint, request
from models.user import User

user_bp = Blueprint('user_bp', __name__)

@user_bp.route('/register', methods=['POST'])
def create_user():
    data = request.json
    full_name = data['full_name']
    username = data['username']
    password = data['password']

    user = User(full_name=full_name, username=username, password=password)
    user.save()

    return {
        'id': str(user.pk),
        'full_name': user.full_name,
        'username': user.username,
        'password': user.password
    }

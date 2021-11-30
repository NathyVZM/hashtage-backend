# user.py

from flask import Blueprint, request
from flask_jwt_extended import create_access_token, create_refresh_token ,get_jwt_identity, jwt_required
from models.user import User

user_bp = Blueprint('user_bp', __name__)

# register()
@user_bp.route('/register', methods=['POST'])
def register():
    data = request.json
    full_name = data['full_name']
    username = data['username']
    password = data['password']

    user = User(full_name=full_name, username=username, password=User.createPassword(password))

    try:
        user.save()
        return {
            'created': True,
            'user': {
                'id': str(user.pk),
                'full_name': user.full_name,
                'username': user.username,
                'password': user.password
            }
        }, 201
    except:
        return { 'message': 'username already exists' }


# login()
@user_bp.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data['username']
    password = data['password']

    user = User.objects(username=username).first()

    if user is not None and user.verifyPassword(password):
        accessToken = create_access_token(identity=str(user.pk))
        refreshToken = create_refresh_token(identity=str(user.pk))

        return {
            'login': True,
            'accessToken': accessToken,
            'refreshToken': refreshToken
        }, 200
    
    else:
        return { 'message': 'Wrong credentials' }


# refresh_token()
@user_bp.route('/refresh-token', methods=['POST'])
@jwt_required(refresh=True)
def refresh_token():
    id_jwt = get_jwt_identity()
    accessToken = create_access_token(identity=id_jwt)

    return { 'accessToken': accessToken }, 200


# logout()
@user_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    return { 'logout': True }, 200

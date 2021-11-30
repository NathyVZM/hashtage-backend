# user.py

from flask import Blueprint, request
from flask_jwt_extended import create_access_token, create_refresh_token ,get_jwt_identity, jwt_required
from models.user import User
from models.post import Post

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
        return { 'created': False, 'message': 'Username already exists' }


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
        return { 'login': False, 'message': 'Wrong credentials' }


# refresh_token()
@user_bp.route('/refresh-token', methods=['POST'])
@jwt_required(refresh=True)
def refresh_token():
    id_jwt = get_jwt_identity()
    accessToken = create_access_token(identity=id_jwt)

    return { 'accessToken': accessToken }, 200


# get_user_posts()
@user_bp.route('/user/<string:user_id>', methods=['GET'])
@jwt_required()
def get_user_posts(user_id):
    try:
        user_posts = Post.objects(author=user_id)

        user = {
            'id': str(user_posts[0].author.pk),
            'full_name': user_posts[0].author.full_name,
            'username': user_posts[0].author.username,
            'address': user_posts[0].author.address,
            'birthday': user_posts[0].author.birthday,
            'bio': user_posts[0].author.bio,
            'followers': user_posts[0].author.followers,
            'following': user_posts[0].author.following
        }

        posts = []

        for post in user_posts:
            p = {
                'id': str(post.pk),
                'text': post.text,
                'date': post.date,
                'img_path': post.img_path
            }
            posts.append(p)

        return {
            'get': True,
            'user': user,
            'posts': posts
        }, 200
    except:
        return { 'get': False, 'message': 'No posts on this user'}


# logout()
@user_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    return { 'logout': True, 'user_id': get_jwt_identity() }, 200

# user.py

import datetime
from flask import Blueprint, request
from flask_jwt_extended import create_access_token, create_refresh_token ,get_jwt_identity, jwt_required
from models.user import User
from models.post import Post
from models.retweet import Retweet
from cloudinary import api
import pprint

user_bp = Blueprint('user_bp', __name__)

# register()
@user_bp.route('/register', methods=['POST'])
def register():
    data = request.json
    full_name = data['full_name']
    username = data['username']
    password = data['password']

    user = User(full_name=full_name, username=username, password=User.createPassword(password))
    duplicated = User.objects(username__iexact=username)

    if not duplicated:
        user.save()
        return {
            'created': True,
            'user': {
                'id': str(user.id),
                'full_name': user.full_name,
                'username': user.username,
                'password': user.password
            }
        }, 201
    else:
        return { 'created': False, 'message': 'Username already exists' }, 409


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
        return { 'login': False, 'message': 'Wrong credentials' }, 409


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
    user_data = User.objects(id=user_id).aggregate([
        {
            '$lookup': {
                'from': 'post',
                'let': { 'author': '$_id' },
                'pipeline': [
                    { '$match': { '$expr': { '$eq': ['$author', '$$author'] } } },
                    { '$sort': { 'date': -1 } },
                    {
                        '$lookup': {
                            'from': 'post',
                            'let': { 'parent': '$parent' },
                            'pipeline': [
                                { '$match': { '$expr': { '$eq': ['$$parent', '$_id'] } } },
                                {
                                    '$lookup': {
                                        'from': 'user',
                                        'localField': 'author',
                                        'foreignField': '_id',
                                        'as': 'author'
                                    }
                                },
                                { '$unwind': '$author' }
                            ],
                            'as': 'parent'
                        }
                    },
                    { '$unwind': { 'path': '$parent', 'preserveNullAndEmptyArrays': True } },
                    { '$project': {
                        '_id': 1,
                        'text': 1,
                        'date': 1,
                        'img_path': 1,
                        'parent': 1
                    } }
                ],
                'as': 'posts'
            }
        },
        {
            '$lookup': {
                'from': 'retweet',
                'let': { 'user_id': '$_id'},
                'pipeline': [
                    { '$match': { '$expr': { '$eq': ['$user_id', '$$user_id']} } },
                    {
                        '$lookup': {
                            'from': 'post',
                            'let': { 'post_id': '$post_id' },
                            'pipeline': [
                                { '$match': { '$expr': { '$eq': ['$_id', '$$post_id']} } },
                                {
                                    '$lookup': {
                                        'from': 'user',
                                        'localField': 'author',
                                        'foreignField': '_id',
                                        'as': 'author'
                                    }
                                },
                                { '$unwind': '$author' }
                            ],
                            'as': 'post_id'
                        }
                    },
                    { '$unwind': '$post_id' },
                    {
                        '$project': {
                            '_id': 1,
                            'post_id': 1,
                        }
                    }
                ],
                'as': 'retweets'
            }
        }
    ])

    pp = pprint.PrettyPrinter(sort_dicts=False)

    user_dict = user_data.next()

    # USER
    user = {
        'id': str(user_dict['_id']),
        'full_name': user_dict['full_name'],
        'username': user_dict['username'],
        'address': user_dict['address'] if 'address' in user_dict else None,
        'birthday': user_dict['birthday'] if 'birthday' in user_dict else None,
        'bio': user_dict['bio'] if 'bio' in user_dict else None,
        'followers': user_dict['followers'],
        'following': user_dict['following']
    }

    # POSTS
    posts = [{('id' if key == '_id' else key):(str(value) if key == '_id' else value) for key, value in post.items()} for post in user_dict['posts']]

    for post in posts:
        if 'img_path' in post:
            images_resources = api.resources(type='upload', prefix=post['img_path'])['resources']
            images = [image['secure_url'] for image in images_resources]
        else:
            images = []
        
        post['images'] = images
        post['comments_count'] = Post.objects(parent=post['id']).count()
        post['retweets_count'] = Retweet.objects(post_id=post['id']).count()

        didRetweet = False
        for retweet in Retweet.objects(post_id=post['id']):
            if str(retweet.user_id.id) == get_jwt_identity():
                didRetweet = True
        
        post['didRetweet'] = didRetweet

        if 'parent' in post:
            post['parent'] = {('id' if key == '_id' else key):(str(value) if key == '_id' or key == 'parent' else value) for key, value in post['parent'].items()}

            post['parent']['author'] = {('id' if key == '_id' else key):(str(value) if key == '_id' else value) for key, value in post['parent']['author'].items()}

    
    # RETWEETS
    retweets = [{('id' if key == '_id' else key):(str(value) if key == '_id' else value) for key, value in retweet.items()} for retweet in user_dict['retweets']]

    for retweet in retweets:
        retweet['comments_count'] = Post.objects(parent=retweet['id']).count()
        retweet['retweets_count'] = Retweet.objects(post_id=retweet['id']).count()

        retweet['post_id'] = {('id' if key == '_id' else key):(str(value) if key == '_id' or key == 'parent' else value) for key, value in retweet['post_id'].items()}

        retweet['post_id']['author'] = {('id' if key == '_id' else key):(str(value) if key == '_id' else value) for key, value in retweet['post_id']['author'].items()}

        didRetweet = False
        for r in Retweet.objects(post_id=retweet['post_id']['id']):
            if str(r.user_id.id) == get_jwt_identity():
                didRetweet = True
        
        retweet['didRetweet'] = didRetweet
        retweet['isAuthor'] = True if retweet['post_id']['author']['id'] == get_jwt_identity() else False

        if 'img_path' in retweet['post_id']:
            images_resources = api.resources(type='upload', prefix=retweet['post_id']['img_path'])['resources']
            images = [image['secure_url'] for image in images_resources]
        else:
            images = []

        retweet['post_id']['images'] = images

    pp.pprint({ 'user': user, 'posts': posts, 'retweets': retweets })

    return {
        'get': True,
        'user': user,
        'posts': posts,
        'retweets': retweets
    }, 200
    

# logout()
@user_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    return { 'logout': True, 'user_id': get_jwt_identity() }, 200

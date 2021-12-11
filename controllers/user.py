# user.py

from datetime import datetime
from flask import Blueprint, request
from flask_jwt_extended import create_access_token, create_refresh_token ,get_jwt_identity, jwt_required
from models.user import User
from models.post import Post
from models.retweet import Retweet
from models.like import Like
from cloudinary import api
import pprint
from bson.objectid import ObjectId

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
    user_obj = User.objects(id=user_id).aggregate([
        {
            '$lookup': {
                'from': 'post', # getting posts
                'let': { 'author': '$_id' },
                'pipeline': [
                    { '$match': { '$expr': { '$eq': ['$$author', '$author'] } } },
                    { '$sort': { '_id': -1 } },
                    {
                        '$lookup': {
                            'from': 'post', # getting posts parent
                            'let': { 'parent': '$parent' },
                            'pipeline': [
                                { '$match': { '$expr': { '$eq': ['$$parent', '$_id'] } } },
                                {
                                    '$lookup': {
                                        'from': 'user', # getting parent author
                                        'let': { 'author': '$author' },
                                        'pipeline': [
                                            { '$match': { '$expr': { '$eq': ['$$author', '$_id'] } } },
                                            {
                                                '$project': {
                                                    '_id': 1,
                                                    'full_name': 1,
                                                    'username': 1
                                                }
                                            }
                                        ],
                                        'as': 'author'
                                    }
                                },
                                { '$unwind': '$author' },
                                {
                                    '$project': {
                                        '_id': 1,
                                        'author': 1,
                                        'text': 1,
                                        'date': 1,
                                        'img_path': { '$ifNull': ['$img_path', None] }
                                    }
                                }
                            ],
                            'as': 'parent'
                        }
                    },
                    {
                        '$lookup': { # getting retweets count
                            'from': 'retweet',
                            'let': { 'post_id': '$_id' },
                            'pipeline': [
                                { '$match': { '$expr': { '$eq': ['$$post_id', '$post_id'] } } },
                                { '$count': 'count' }
                            ],
                            'as': 'retweets_count'
                        }
                        
                    },
                    {
                        '$lookup': { # getting comments count
                            'from': 'post',
                            'let': { 'id': '$_id' },
                            'pipeline': [
                                { '$match': { '$expr': { '$eq': ['$$id', '$parent'] } } },
                                { '$count': 'count' }
                            ],
                            'as': 'comments_count'
                        }
                    },
                    {
                        '$lookup': { # getting likes count
                            'from': 'like',
                            'let': { 'post_id': '$_id' },
                            'pipeline': [
                                { '$match': { '$expr': { '$eq': ['$$post_id', '$post_id'] } } },
                                { '$count': 'count' }
                            ],
                            'as': 'likes_count'
                        }
                    },
                    { '$unwind': { 'path': '$parent', 'preserveNullAndEmptyArrays': True } },
                    { '$unwind': { 'path': '$retweets_count', 'preserveNullAndEmptyArrays': True } },
                    { '$unwind': { 'path': '$comments_count', 'preserveNullAndEmptyArrays': True } },
                    { '$unwind': { 'path': '$likes_count', 'preserveNullAndEmptyArrays': True }},
                    {
                        '$project': {
                            '_id': 1,
                            'text': 1,
                            'date': 1,
                            'img_path': { '$ifNull': ['$img_path', None] },
                            'parent': { '$ifNull': ['$parent', None] },
                            'retweets_count': '$retweets_count.count',
                            'comments_count': '$comments_count.count',
                            'likes_count': '$likes_count.count'
                        }
                    }
                ],
                'as': 'posts'
            }
        },
        {
            '$lookup': {
                'from': 'retweet', # getting retweets
                'let': { 'id': '$_id' },
                'pipeline': [
                    { '$match': { '$expr': { '$eq': ['$$id', '$user_id'] } } },
                    { '$sort': { '_id': -1 } },
                    {
                        '$lookup': { # getting post for retweets
                            'from': 'post',
                            'let': { 'post_id': '$post_id' },
                            'pipeline': [
                                { '$match': { '$expr': { '$eq': ['$$post_id', '$_id'] } } },
                                {
                                    '$lookup': {
                                        'from': 'user', # getting post author
                                        'let': { 'author': '$author' },
                                        'pipeline': [
                                            { '$match': { '$expr': { '$eq': ['$$author', '$_id'] } } },
                                            {
                                                '$project': {
                                                    '_id': 1,
                                                    'full_name': 1,
                                                    'username': 1
                                                }
                                            }
                                        ],
                                        'as': 'author'
                                    }
                                },
                                {
                                    '$lookup': {
                                        'from': 'retweet',
                                        'let': { 'post_id': '$_id' },
                                        'pipeline': [
                                            { '$match': { '$expr': { '$eq': ['$$post_id', '$post_id'] } } },
                                            { '$count': 'count' }
                                        ],
                                        'as': 'retweets_count'
                                    }
                                },
                                {
                                    '$lookup': {
                                        'from': 'post',
                                        'let': { 'id': '$_id' },
                                        'pipeline': [
                                            { '$match': { '$expr': { '$eq': ['$$id', '$parent'] } } },
                                            { '$count': 'count' }
                                        ],
                                        'as': 'comments_count'
                                    }
                                },
                                {
                                    '$lookup': {
                                        'from': 'like',
                                        'let': { 'post_id': '$_id' },
                                        'pipeline': [
                                            { '$match': { '$expr': { '$eq': ['$$post_id', '$post_id'] } } },
                                            { '$count': 'count'}
                                        ],
                                        'as': 'likes_count'
                                    }
                                },
                                { '$unwind': '$author' },
                                { '$unwind': { 'path': '$retweets_count', 'preserveNullAndEmptyArrays': True }},
                                { '$unwind': { 'path': '$comments_count', 'preserveNullAndEmptyArrays': True }},
                                { '$unwind': { 'path': '$likes_count', 'preserveNullAndEmptyArrays': True }},
                                {
                                    '$project': {
                                        '_id': 1,
                                        'author': 1,
                                        'text': 1,
                                        'date': 1,
                                        'img_path': { '$ifNull': ['$img_path', None] },
                                        'retweets_count': '$retweets_count.count',
                                        'comments_count': '$comments_count.count',
                                        'likes_count': '$likes_count.count'
                                    }
                                }
                            ],
                            'as': 'post_id'
                        }
                    },
                    { '$unwind': '$post_id' },
                    {
                        '$project': {
                            'user_id': 0
                        }
                    }
                ],
                'as': 'retweets'
            }
        },
        {
            '$project': {
                '_id': 1,
                'full_name': 1,
                'username': 1,
                'address': 1,
                'birthday': 1,
                'bio': 1,
                'followers': 1,
                'following': 1,
                'posts': 1,
                'retweets': 1
            }
        }
    ])

    pp = pprint.PrettyPrinter(sort_dicts=False)

    user_dict = user_obj.next()

    isFollower = False
    for follower in user_dict['followers']:
        if str(follower) == get_jwt_identity():
            isFollower = True

    # USER
    user = {
        'id': str(user_dict['_id']),
        'full_name': user_dict['full_name'],
        'username': user_dict['username'],
        'address': user_dict['address'] if 'address' in user_dict else None,
        'birthday': user_dict['birthday'] if 'birthday' in user_dict else None,
        'bio': user_dict['bio'] if 'bio' in user_dict else None,
        'followers': len(user_dict['followers']),
        'following': len(user_dict['following']),
        'isFollower': isFollower
    }

    # POST
    posts = [{('id' if key == '_id' else key):(str(value) if key == '_id' else value) for key, value in post.items()} for post in user_dict['posts']]

    for post in posts:
        if post['parent'] is not None: # checking if parent exists in post
            post['parent'] = {('id' if key == '_id' else key):(str(value) if key == '_id' else value) for key, value in post['parent'].items()}

            post['parent']['author'] = {('id' if key == '_id' else key):(str(value) if key == '_id' else value) for key, value in post['parent']['author'].items()}

            # adding images to parent
            if post['parent']['img_path'] is not None:
                parent_resources = api.resources(type='upload', prefix=post['parent']['img_path'])['resources']
                parent_images = [image['secure_url'] for image in parent_resources]
            else:
                parent_images = []
                
            post['parent']['images'] = parent_images

        # adding images to post
        if post['img_path'] is not None:
            images_resources = api.resources(type='upload', prefix=post['img_path'])['resources']
            images = [image['secure_url'] for image in images_resources]
        else:
            images = []
        
        post['images'] = images

        if 'retweets_count' not in post:
            post['retweets_count'] = 0
            
        if 'comments_count' not in post:
            post['comments_count'] = 0

        if 'likes_count' not in post:
            post['likes_count'] = 0
        
        # didRetweet
        didRetweet = False
        for retweet in Retweet.objects(post_id=post['id']):
            if str(retweet.user_id.id) == get_jwt_identity():
                didRetweet = True
        
        post['didRetweet'] = didRetweet

        # didLike
        didLike = False
        for like in Like.objects(post_id=post['id']):
            if str(like.user_id.id) == get_jwt_identity():
                didLike = True
        
        post['didLike'] = didLike


    # RETWEET
    retweets = [{('id' if key == '_id' else key):(str(value) if key == '_id' else value) for key, value in retweet.items()} for retweet in user_dict['retweets']]

    for retweet in retweets:
        retweet['post_id'] = {('id' if key == '_id' else key):(str(value) if key == '_id' else value) for key, value in retweet['post_id'].items()}

        retweet['post_id']['author'] = {('id' if key == '_id' else key):(str(value) if key == '_id' else value) for key, value in retweet['post_id']['author'].items()}


        # adding images to post retweet
        if retweet['post_id']['img_path'] is not None:
            retweet_resources = api.resources(type='upload', prefix=retweet['post_id']['img_path'])['resources']
            retweet_images = [image['secure_url'] for image in retweet_resources]
        else:
            retweet_images = []
        
        retweet['post_id']['images'] = retweet_images

        if 'retweets_count' not in retweet['post_id']:
            retweet['post_id']['retweets_count'] = 0
        
        if 'comments_count' not in retweet['post_id']:
            retweet['post_id']['comments_count'] = 0
        
        if 'likes_count' not in retweet['post_id']:
            retweet['post_id']['likes_count'] = 0
        
        # didRetweet
        didRetweetPost = False
        for r in Retweet.objects(post_id=retweet['post_id']['id']):
            if str(r.user_id.id) == get_jwt_identity():
                didRetweetPost = True
        
        retweet['post_id']['didRetweet'] = didRetweetPost

        # didLike
        didLikePost = False
        for like in Like.objects(post_id=retweet['post_id']['id']):
            if str(like.user_id.id) == get_jwt_identity():
                didLikePost = True
        
        retweet['post_id']['didLike'] = didLikePost


    return {
        'user': user,
        'posts': posts,
        'retweets': retweets
    }, 200

    # user_obj = User.objects(id=user_id).first()

    # isFollower = False
    # for follower in user_obj.followers:
    #     if str(follower.id) == get_jwt_identity():
    #         isFollower = True

    # user = {
    #     'id': str(user_obj.pk),
    #     'full_name': user_obj.full_name,
    #     'username': user_obj.username,
    #     'address': user_obj.address,
    #     'birthday': user_obj.birthday,
    #     'bio': user_obj.bio,
    #     'followers': len(user_obj.followers),
    #     'following': len(user_obj.following),
    #     'isFollower': isFollower
    # }

    # posts = []

    # for post in Post.objects(author=user_id).order_by('-id'):
    #     if post.img_path is not None:
    #         images_resources = api.resources(type='upload', prefix=post.img_path)['resources']
    #         images = [image['secure_url'] for image in images_resources]
    #     else:
    #         images = []
        
    #     didRetweet = False
    #     for retweet in Retweet.objects(post_id=str(post.id)):
    #         if str(retweet.user_id.id) == get_jwt_identity():
    #             didRetweet = True
        
    #     didLike = False
    #     for like in Like.objects(post_id=str(post.id)):
    #         if str(like.user_id.id) == get_jwt_identity():
    #             didLike = True
        
    #     posts.append({
    #         'id': str(post.pk),
    #         'text': post.text,
    #         'date': post.date,
    #         'images': images,
    #         'retweets_count': Retweet.objects(post_id=str(post.pk)).count(),
    #         'comments_count': Post.objects(parent=str(post.id)).count(),
    #         'likes_count': Like.objects(post_id=str(post.id)).count(),
    #         'didRetweet': didRetweet,
    #         'didLike': didLike,
    #         'parent': post.parent
    #     })

    # retweets = []

    # for retweet in Retweet.objects(user_id=user_id).order_by('-id'):
    #     if retweet.post_id.img_path is not None:
    #         retweet_resources = api.resources(type='upload', prefix=retweet.post_id.img_path)['resources']
    #         retweet_images = [image['secure_url'] for image in retweet_resources]
    #     else:
    #         retweet_images = []
        
    #     didRetweetPost = False
    #     for r in Retweet.objects(post_id=str(retweet.post_id.id)):
    #         if str(r.user_id.id) == get_jwt_identity():
    #             didRetweetPost = True
        
    #     didLikePost = False
    #     for like in Like.objects(post_id=str(retweet.post_id.id)):
    #         if str(like.user_id.id) == get_jwt_identity():
    #             didLikePost = True

    #     retweets.append({
    #         'id': str(retweet.id),
    #         'post_id': {
    #             'id': str(retweet.post_id.id),
    #             'author': retweet.post_id.author,
    #             'text': retweet.post_id.text,
    #             'date': retweet.post_id.date,
    #             'images': retweet_images,
    #             'didRetweet': didRetweetPost,
    #             'didLike': didLikePost,
    #             'retweets_count': Retweet.objects(post_id=str(retweet.post_id.id)).count(),
    #             'comments_count': Post.objects(parent=str(retweet.post_id.id)).count(),
    #             'likes_count': Like.objects(post_id=str(retweet.post_id.id)).count()
    #         }
    #     })

    # return {
    #         'get': True,
    #         'user': user,
    #         'posts': posts,
    #         'retweets': retweets
    #     }, 200


# get_user_likes
@user_bp.route('/user/likes/<string:user_id>', methods=['GET'])
@jwt_required()
def get_user_likes(user_id):
    likes = []

    for like in Like.objects(user_id=user_id).order_by('-id'):
        if like.post_id.img_path is not None:
            like_resources = api.resources(type='upload', prefix=like.post_id.img_path)['resources']
            like_images = [image['secure_url'] for image in like_resources]
        else:
            like_images = []
        
        didRetweetLike = False
        for retweet in Retweet.objects(post_id=str(like.post_id.id)):
            if str(retweet.user_id.id) == get_jwt_identity():
                didRetweetLike = True
        
        didLike_Like = False
        for l in Like.objects(post_id=str(like.post_id.id)):
            if str(l.user_id.id) == get_jwt_identity():
                didLike_Like = True
        

        likes.append({
            'id': str(like.id),
            'post_id': {
                'id': str(like.post_id.id),
                'author': like.post_id.author,
                'text': like.post_id.text,
                'date': like.post_id.date,
                'images': like_images,
                'didRetweet': didRetweetLike,
                'didLike': didLike_Like,
                'retweets_count': Retweet.objects(post_id=str(like.post_id.id)).count(),
                'comments_count': Post.objects(parent=str(like.post_id.id)).count(),
                'likes_count': Like.objects(post_id=str(like.post_id.id)).count()
            }
        })
    
    return { 'likes': likes }



# logout()
@user_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    return { 'logout': True, 'user_id': get_jwt_identity() }, 200


# follow_user()
@user_bp.route('/follow/<string:user_id>', methods=['POST'])
@jwt_required()
def follow_user(user_id):
    user_following = User.objects(id=get_jwt_identity()).first()
    user_followed = User.objects(id=user_id).first()

    if user_following is not None and user_followed is not None:
        User.objects(id=get_jwt_identity()).update_one(push__following=user_followed)
        User.objects(id=user_id).update_one(push__followers=user_following)

        return {
            'follow': True,
            'user_following': str(user_following.id),
            'user_followed': str(user_followed.id)
        }, 201
    else:
        return { 'follow': False, 'message': 'Users not found' }, 409


# unfollow_user()
@user_bp.route('/follow/<string:user_id>', methods=['DELETE'])
@jwt_required()
def unfollow_user(user_id):
    user_unfollowing = User.objects(id=get_jwt_identity()).first()
    user_unfollowed = User.objects(id=user_id).first()

    if user_unfollowing is not None and user_unfollowed is not None:
        User.objects(id=get_jwt_identity()).update_one(pull__following=user_unfollowed)
        User.objects(id=user_id).update_one(pull__followers=user_unfollowing)

        return {
            'unfollow': True,
            'user_unfollowing': str(user_unfollowing.id),
            'user_unfollowed': str(user_unfollowed.id)
        }, 200
    else:
        return { 'unfollow': False, 'message': 'Users not found' }, 409


# edit_user
@user_bp.route('/user', methods=['PUT'])
@jwt_required()
def edit_user():
    data = request.json
    
    full_name = data['full_name']
    username = data['username']
    password = data['password']
    address = data['address']
    birthday = data['birthday']
    bio = data['bio']

    birthday_obj = datetime.strptime(birthday, '%d/%m/%Y')
    print(birthday_obj)

    user = User.objects(id=get_jwt_identity()).first()

    if user is not None:
        user.update(full_name=full_name, username=username, password=User.createPassword(password), address=address, birthday=birthday_obj, bio=bio)
        user.reload()

        return {
            'edit': True,
            'user': {
                'id': str(user.id),
                'full_name': user.full_name,
                'username': user.username,
                'password': user.password,
                'address': user.address,
                'birthday': user.birthday,
                'bio': user.bio
            }
        }, 200
    else:
        return { 'edit': False, 'message': 'User not found' }, 409
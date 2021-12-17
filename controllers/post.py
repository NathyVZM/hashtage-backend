# post.py

from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.user import User
from models.post import Post
from models.retweet import Retweet
from models.like import Like
from mongoengine.queryset.visitor import Q
from cloudinary import uploader, api
import time
from bson.objectid import ObjectId

post_bp = Blueprint('post_bp', __name__)

# create_post()
@post_bp.route('/post', methods=['POST'])
@jwt_required()
def create_post():
    data = request.form
    author = get_jwt_identity()
    text = data['text']

    post = Post(author=author, text=text)
    post.save()

    if 'images' in request.files:
        post.update(img_path=f'hashtage/{str(post.author.pk)}/{str(post.pk)}')
        post.reload()

        for index, image in enumerate(request.files.getlist('images'), start=1):
            print(index, image.filename)
            uploader.upload_image(image, folder=f'hashtage/{str(post.author.pk)}/{str(post.pk)}', 
            public_id=str(time.time()))
        
    post_data = Post.objects(id=str(post.id)).aggregate([
        {
            '$lookup': {
                'from': 'user', # getting author for post
                'let': { 'author': '$author' },
                'pipeline': [
                    { '$match': { '$expr': { '$eq': ['$$author', '$_id']} } },
                    {
                        '$project': {
                            '_id': 0,
                            'id': { '$toString': '$_id'},
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
                'from': 'retweet', # getting retweets count
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
                'from': 'post', # getting comments count
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
                'from': 'like', # getting likes count
                'let': { 'post_id': '$_id' },
                'pipeline': [
                    { '$match': { '$expr': { '$eq': ['$$post_id', '$post_id'] } } },
                    { '$count': 'count' }
                ],
                'as': 'likes_count'
            }
        },
        {
            '$lookup': {
                'from': 'retweet', # getting retweets for didRetweet
                'let': { 'post_id': '$_id' },
                'pipeline': [
                    { '$match': { '$expr': { '$eq': ['$$post_id', '$post_id'] } } },
                    {
                        '$project': {
                            '_id': 0,
                            'user_id': { '$toString': '$user_id' }
                        }
                    }
                ],
                'as': 'retweets'
            }
        },
        {
            '$lookup': {
                'from': 'like', # getting likes for didLike
                'let': { 'post_id': '$_id' },
                'pipeline': [
                    { '$match': { '$expr': { '$eq': ['$$post_id', '$post_id'] } } },
                    {
                        '$project': {
                            '_id': 0,
                            'user_id': { '$toString': '$user_id' }
                        }
                    }
                ],
                'as': 'likes'
            }
        },
        { '$unwind': '$author' },
        { '$unwind': { 'path': '$retweets_count', 'preserveNullAndEmptyArrays': True } },
        { '$unwind': { 'path': '$comments_count', 'preserveNullAndEmptyArrays': True } },
        { '$unwind': { 'path': '$likes_count', 'preserveNullAndEmptyArrays': True } },
        {
            '$project': {
                '_id': 0,
                'id': { '$toString': '$_id' },
                'author': 1,
                'text': 1,
                'date': 1,
                'img_path': { '$ifNull': ['$img_path', None] },
                'retweets_count': '$retweets_count.count',
                'comments_count': '$comments_count.count',
                'likes_count': '$likes_count.count',
                'retweets': 1,
                'likes': 1
            }
        }
    ])

    post_dict = post_data.next()

    if post_dict['img_path'] is not None:
        images_resources = api.resources(type='upload', prefix=post_dict['img_path'])['resources']
        images = [image['secure_url'] for image in images_resources]
    else:
        images = []
    
    post_dict['images'] = images

    if 'retweets_count' not in post_dict:
        post_dict['retweets_count'] = 0
    
    if 'comments_count' not in post_dict:
        post_dict['comments_count'] = 0
    
    if 'likes_count' not in post_dict:
        post_dict['likes_count'] = 0
    
    # didRetweet
    didRetweet = False
    for retweet in post_dict['retweets']:
        if retweet['user_id'] == get_jwt_identity():
            didRetweet = True
    
    post_dict['didRetweet'] = didRetweet

    # didLike
    didLike = False
    for like in post_dict['likes']:
        if like['user_id'] == get_jwt_identity():
            didLike = True
    
    post_dict['didLike'] = didLike
    
    return {
        'created': True,
        'post': post_dict
    }, 201


# FUNCTION deleteChildrenImages
def deleteChildrenImages(comment_parent):
    for comment in Post.objects(parent=comment_parent):
        if comment.img_path is not None:
            api.delete_resources_by_prefix(comment.img_path)
            api.delete_folder(comment.img_path)
        
        deleteChildrenImages(str(comment.pk))


# delete_post()
@post_bp.route('/post/<string:post_id>', methods=['DELETE'])
@jwt_required()
def delete_post(post_id):
    post = Post.objects(id=post_id).first()

    if post is not None:
        if post.img_path is not None:
            api.delete_resources_by_prefix(post.img_path)
            api.delete_folder(post.img_path)
        
        comments = Post.objects(parent=str(post.pk))

        for comment in Post.objects(parent=str(post.pk)):
            if comment.img_path is not None:
                print(comment.img_path)
                api.delete_resources_by_prefix(comment.img_path)
                api.delete_folder(comment.img_path)
                
            deleteChildrenImages(str(comment.pk))
        
        post.delete()

        return {
            'deleted': True,
            'post': {
                'id': str(post.pk),
                'author': post.author,
                'text': post.text,
                'date': post.date,
                'img_path': post.img_path,
                'comments': comments
            }
        }, 200
    else:
        return { 'deleted': False, 'message': 'Post not found' }, 409


# get_all_posts()
@post_bp.route('/post', methods=['GET'])
@jwt_required()
def get_all_posts():

    posts_data = Post.objects(parent=None).aggregate([
        { '$sort': { '_id': -1 }},
        {
            '$lookup': {
                'from': 'user', # getting post author
                'let': { 'author': '$author' },
                'pipeline': [
                    { '$match': { '$expr': { '$eq': ['$$author', '$_id'] } } },
                    {
                        '$project': {
                            '_id': 0,
                            'id': { '$toString': '$_id' },
                            'full_name': 1,
                            'username': 1
                        }
                    }
                ],
                'as': 'author'
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
        { '$unwind': '$author' },
        { '$unwind': { 'path': '$retweets_count', 'preserveNullAndEmptyArrays': True } },
        { '$unwind': { 'path': '$comments_count', 'preserveNullAndEmptyArrays': True } },
        { '$unwind': { 'path': '$likes_count', 'preserveNullAndEmptyArrays': True } },
        {
            '$lookup': {
                'from': 'retweet', # getting retweets
                'let': { 'post_id': '$_id' },
                'pipeline': [
                    { '$match': { '$expr': { '$eq': ['$$post_id', '$post_id'] } } },
                    { '$sort': { '_id': -1 } },
                    {
                        '$lookup': {
                            'from': 'user', # getting user_id for retweets
                            'let': { 'user_id': '$user_id' },
                            'pipeline': [
                                { '$match': { '$expr': { '$eq': ['$$user_id', '$_id'] } } },
                                {
                                    '$project': {
                                        '_id': 0,
                                        'id': { '$toString': '$_id' },
                                        'full_name': 1,
                                        'username': 1
                                    }   
                                }
                            ],
                            'as': 'user_id'
                        }
                    },
                    {
                        '$lookup': {
                            'from': 'post', # getting post for retweets
                            'let': { 'post_id': '$post_id' },
                            'pipeline': [
                                { '$match': { '$expr': { '$eq': ['$$post_id', '$_id'] } } },
                                {
                                    '$lookup': {
                                        'from': 'user', # getting author for post retweet
                                        'let': { 'author': '$author' },
                                        'pipeline': [
                                            { '$match': { '$expr': { '$eq': ['$$author', '$_id'] } } },
                                            {
                                                '$project': {
                                                    '_id': 0,
                                                    'id': { '$toString': '$_id' },
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
                                        'from': 'retweet', # getting retweets count
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
                                        'from': 'post', # getting comments count
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
                                        'from': 'like', # getting likes count
                                        'let': { 'post_id': '$_id' },
                                        'pipeline': [
                                            { '$match': { '$expr': { '$eq': ['$$post_id', '$post_id'] } } },
                                            { '$count': 'count' }
                                        ],
                                        'as': 'likes_count'
                                    }
                                },
                                {
                                    '$lookup': {
                                        'from': 'retweet',
                                        'let': { 'post_id': '$_id' },
                                        'pipeline': [
                                            { '$match': { '$expr': { '$eq': ['$$post_id', '$post_id'] } } },
                                            {
                                                '$project': {
                                                    '_id': 0,
                                                    'user_id': { '$toString': '$user_id' }
                                                }
                                            }
                                        ],
                                        'as': 'retweets'
                                    }
                                },
                                {
                                    '$lookup': {
                                        'from': 'like',
                                        'let': { 'post_id': '$_id' },
                                        'pipeline': [
                                            { '$match': { '$expr': { '$eq': ['$$post_id', '$post_id'] } } },
                                            {
                                                '$project': {
                                                    '_id': 0,
                                                    'user_id': { '$toString': '$user_id' }
                                                }
                                            }
                                        ],
                                        'as': 'likes'
                                    }
                                },
                                { '$unwind': '$author' },
                                { '$unwind': { 'path': '$retweets_count', 'preserveNullAndEmptyArrays': True } },
                                { '$unwind': { 'path': '$comments_count', 'preserveNullAndEmptyArrays': True } },
                                { '$unwind': { 'path': '$likes_count', 'preserveNullAndEmptyArrays': True } },
                                {
                                    '$project': {
                                        '_id': 0,
                                        'id': { '$toString': '$_id' },
                                        'author': 1,
                                        'text': 1,
                                        'date': 1,
                                        'img_path': { '$ifNull': ['$img_path', None] },
                                        'retweets_count': '$retweets_count.count',
                                        'comments_count': '$comments_count.count',
                                        'likes_count': '$likes_count.count',
                                        'retweets': 1,
                                        'likes': 1
                                    }
                                }
                            ],
                            'as': 'post_id'
                        }
                    },
                    { '$unwind': '$user_id' },
                    { '$unwind': '$post_id' },
                    {
                        '$project': {
                            '_id': 0,
                            'id': { '$toString': '$_id' },
                            'user_id': 1,
                            'post_id': 1
                        }
                    }
                ],
                'as': 'retweets'
            }
        },
        {
            '$lookup': {
                'from': 'like',
                'let': { 'post_id': '$_id' },
                'pipeline': [
                    { '$match': { '$expr': { '$eq': ['$$post_id', '$post_id'] } } },
                    {
                        '$project': {
                            '_id': 0,
                            'user_id': { '$toString': '$user_id' }
                        }
                    }
                ],
                'as': 'likes'
            }
        },
        {
            '$project': {
                '_id': 0,
                'id': { '$toString': '$_id' },
                'author': 1,
                'text': 1,
                'date': 1,
                'img_path': { '$ifNull': ['$img_path', None] },
                'retweets_count': '$retweets_count.count',
                'comments_count': '$comments_count.count',
                'likes_count': '$likes_count.count',
                'retweets': 1,
                'likes': 1
            }
        }
    ])

    posts = []

    for post in posts_data:
        # looping through retweets
        for retweet in post['retweets']:
            if retweet['post_id']['img_path'] is not None: # getting images for retweet
                retweet_resources = api.resources(type='upload', prefix=retweet['post_id']['img_path'])['resources']
                retweet_images = [image['secure_url'] for image in retweet_resources]
            else:
                retweet_images = []
            
            retweet['post_id']['images'] = retweet_images

            # didRetweet
            didRetweetPost = False
            for r in retweet['post_id']['retweets']:
                if r['user_id'] == get_jwt_identity():
                    didRetweetPost = True
            
            retweet['post_id']['didRetweet'] = didRetweetPost

            # didLike
            didLikePost = False
            for like in retweet['post_id']['likes']:
                if like['user_id'] == get_jwt_identity():
                    didLikePost = True
            
            retweet['post_id']['didLike'] = didLikePost

            if 'retweets_count' not in retweet['post_id']:
                retweet['post_id']['retweets_count'] = 0
            
            if 'comments_count' not in retweet['post_id']:
                retweet['post_id']['comments_count'] = 0
            
            if 'likes_count' not in retweet['post_id']:
                retweet['post_id']['likes_count'] = 0

            posts.append(retweet)
            del retweet['post_id']['retweets']
            del retweet['post_id']['likes']
        # end of loop of retweets

        # getting images for post
        if post['img_path'] is not None:
            images_resources = api.resources(type='upload', prefix=post['img_path'])['resources']
            images = [image['secure_url'] for image in images_resources]
        else:
            images = []
        
        post['images'] = images

        # didRetweet
        didRetweet = False
        for r in post['retweets']:
            if r['user_id']['id'] == get_jwt_identity():
                didRetweet = True
        
        post['didRetweet'] = didRetweet

        # didLike
        didLike = False
        for like in post['likes']:
            if like['user_id'] == get_jwt_identity():
                didLike = True

        post['didLike'] = didLike

        if 'retweets_count' not in post:
            post['retweets_count'] = 0
        
        if 'comments_count' not in post:
            post['comments_count'] = 0
        
        if 'likes_count' not in post:
            post['likes_count'] = 0
        
        # delete retweets and likes fields from post dictionary
        del post['retweets']
        del post['likes']

        posts.append(post)
    
    posts_sorted = sorted(posts, key = lambda i:ObjectId(i['id']).generation_time, reverse=True)

    return { 'get': True, 'posts': posts_sorted }, 200


# create_comment()
@post_bp.route('/post/comment/<string:post_id>', methods=['POST'])
@jwt_required()
def create_comment(post_id):
    data = request.form
    author = get_jwt_identity()
    text = data['text']

    comment = Post(author=author, text=text, parent=post_id)
    comment.save()

    if 'images' in request.files:
        comment.update(img_path=f'hashtage/{str(comment.author.pk)}/{str(comment.pk)}')
        for index, image in enumerate(request.files.getlist('images'), start=1):
            print(index, image.filename)
            uploader.upload_image(image, folder=f'hashtage/{str(comment.author.pk)}/{str(comment.pk)}',
            public_id=str(time.time()))
    
    comment_data = Post.objects(id=str(comment.id)).aggregate([
        {
            '$lookup': {
                'from': 'user', # getting author for comment
                'let': { 'author': '$author' },
                'pipeline': [
                    { '$match': { '$expr': { '$eq': ['$$author', '$_id'] } } },
                    {
                        '$project': {
                            '_id': 0,
                            'id': { '$toString': '$_id' },
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
                'from': 'post', # getting parent for comment
                'let': { 'parent': '$parent' },
                'pipeline': [
                    { '$match': { '$expr': { '$eq': ['$$parent', '$_id'] } } },
                    {
                        '$project': {
                            '_id': 0,
                            'id': { '$toString': '$_id' }
                        }
                    }
                ],
                'as': 'parent'
            }
        },
        {
            '$lookup': {
                'from': 'retweet', # getting retweets count
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
                'from': 'post', # getting comments count
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
                'from': 'like', # getting likes count
                'let': { 'post_id': '$_id' },
                'pipeline': [
                    { '$match': { '$expr': { '$eq': ['$$post_id', '$post_id'] } } },
                    { '$count': 'count' }
                ],
                'as': 'likes_count'
            }
        },
        {
            '$lookup': {
                'from': 'retweet', # getting retweets for didRetweet
                'let': { 'post_id': '$_id' },
                'pipeline': [
                    { '$match': { '$expr': { '$eq': ['$$post_id', '$post_id'] } } },
                    {
                        '$project': {
                            '_id': 0,
                            'user_id': { '$toString': '$user_id' }
                        }
                    }
                ],
                'as': 'retweets'
            }
        },
        {
            '$lookup': {
                'from': 'like', # getting likes for didLike
                'let': { 'post_id': '$_id' },
                'pipeline': [
                    { '$match': { '$expr': { '$eq': ['$$post_id', '$post_id'] } } },
                    {
                        '$project': {
                            '_id': 0,
                            'user_id': { '$toString': '$user_id' }
                        }
                    }
                ],
                'as': 'likes'
            }
        },
        { '$unwind': '$author' },
        { '$unwind': '$parent' },
        { '$unwind': { 'path': '$retweets_count', 'preserveNullAndEmptyArrays': True } },
        { '$unwind': { 'path': '$comments_count', 'preserveNullAndEmptyArrays': True } },
        { '$unwind': { 'path': '$likes_count', 'preserveNullAndEmptyArrays': True } },
        {
            '$project': {
                '_id': 0,
                'id': { '$toString': '$_id' },
                'author': 1,
                'text': 1,
                'date': 1,
                'img_path': { '$ifNull': ['$img_path', None] },
                'parent': { '$ifNull': ['$parent', None] },
                'retweets_count': '$retweets_count.count',
                'comments_count': '$comments_count.count',
                'likes_count': '$likes_count.count',
                'retweets': 1,
                'likes': 1
            }
        }
    ])

    comment_dict = comment_data.next()

    if comment_dict['img_path'] is not None:
        images_resources = api.resources(type='upload', prefix=comment_dict['img_path'])['resources']
        images = [image['secure_url'] for image in images_resources]
    else:
        images = []
    
    comment_dict['images'] = images

    if 'retweets_count' not in comment_dict:
        comment_dict['retweets_count'] = 0
    
    if 'comments_count' not in comment_dict:
        comment_dict['comments_count'] = 0
    
    if 'likes_count' not in comment_dict:
        comment_dict['likes_count'] = 0
    
    # didRetweet
    didRetweet = False
    for retweet in comment_dict['retweets']:
        if retweet['user_id'] == get_jwt_identity():
            didRetweet = True
    
    comment_dict['didRetweet'] = didRetweet

    # didLike
    didLike = False
    for like in comment_dict['likes']:
        if like['user_id'] == get_jwt_identity():
            didLike = True
    
    comment_dict['didLike'] = didLike

    return {
        'created': True,
        'comment': comment_dict
    }, 201
   

# get_post_info()
@post_bp.route('/post/<string:post_id>', methods=['GET'])
@jwt_required()
def get_post_info(post_id):
    post_data = Post.objects(id=post_id).aggregate([
        {
            '$lookup': {
                'from': 'user', # getting author for post
                'let': { 'author': '$author' },
                'pipeline': [
                    { '$match': { '$expr': { '$eq': ['$$author', '$_id'] } } },
                    {
                        '$project': {
                            '_id': 0,
                            'id': { '$toString': '$_id' },
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
                'from': 'post', # getting comments
                'let': { 'id': '$_id' },
                'pipeline': [
                    { '$match': { '$expr': { '$eq': ['$$id', '$parent'] } } },
                    {
                        '$lookup': {
                            'from': 'user', # getting author for comments
                            'let': { 'author': '$author' },
                            'pipeline': [
                                { '$match': { '$expr': { '$eq': ['$$author', '$_id'] } } },
                                {
                                    '$project': {
                                        '_id': 0,
                                        'id': { '$toString': '$_id' },
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
                            'from': 'retweet', # getting retweets count for comments
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
                            'from': 'post', # getting comments count for comments
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
                            'from': 'like', # getting likes count for comments
                            'let': { 'post_id': '$_id' },
                            'pipeline': [
                                { '$match': { '$expr': { '$eq': ['$$post_id', '$post_id'] } } },
                                { '$count': 'count' }
                            ],
                            'as': 'likes_count'
                        }
                    },
                    {
                        '$lookup': {
                            'from': 'retweet', # getting retweets for didRetweet
                            'let': { 'post_id': '$_id' },
                            'pipeline': [
                                { '$match': { '$expr': { '$eq': ['$$post_id', '$post_id'] } } },
                                {
                                    '$project': {
                                        '_id': 0,
                                        'user_id': { '$toString': '$user_id' }
                                    }
                                }
                            ],
                            'as': 'retweets'
                        }
                    },
                    {
                        '$lookup': {
                            'from': 'like', # getting likes for didLike
                            'let': { 'post_id': '$_id' },
                            'pipeline': [
                                { '$match': { '$expr': { '$eq': ['$$post_id', '$post_id'] } } },
                                {
                                    '$project': {
                                        '_id': 0,
                                        'user_id': { '$toString': '$user_id' }
                                    }
                                }
                            ],
                            'as': 'likes'
                        }
                    },
                    { '$unwind': '$author' },
                    { '$unwind': { 'path': '$retweets_count', 'preserveNullAndEmptyArrays': True } },
                    { '$unwind': { 'path': '$comments_count', 'preserveNullAndEmptyArrays': True } },
                    { '$unwind': { 'path': '$likes_count', 'preserveNullAndEmptyArrays': True } },
                    {
                        '$project': {
                            '_id': 0,
                            'id': { '$toString': '$_id' },
                            'author': 1,
                            'text': 1,
                            'date': 1,
                            'img_path': { '$ifNull': ['$img_path', None] },
                            'retweets_count': '$retweets_count.count',
                            'comments_count': '$comments_count.count',
                            'likes_count': '$likes_count.count',
                            'isAuthor': { '$cond': { 'if': { '$eq': ['$author.id', get_jwt_identity()] }, 'then': True, 'else': False } },
                            'retweets': 1,
                            'likes': 1
                        }
                    }
                ],
                'as': 'children'
            }
        },
        {
            '$lookup': {
                'from': 'post', # getting parent
                'let': { 'parent': '$parent' },
                'pipeline': [
                    { '$match': { '$expr': { '$eq': ['$$parent', '$_id'] } } },
                    {
                        '$project': {
                            '_id': 0,
                            'id': { '$toString': '$_id' }
                        }
                    }
                ],
                'as': 'parent'
            }
        },
        {
            '$lookup': {
                'from': 'retweet', # getting retweets count
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
                'from': 'post', # getting comments count
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
                'from': 'like', # getting likes count
                'let': { 'post_id': '$_id' },
                'pipeline': [
                    { '$match': { '$expr': { '$eq': ['$$post_id', '$post_id'] } } },
                    { '$count': 'count' }
                ],
                'as': 'likes_count'
            }
        },
        {
            '$lookup': {
                'from': 'retweet', # getting retweets for didRetweet
                'let': { 'post_id': '$_id' },
                'pipeline': [
                    { '$match': { '$expr': { '$eq': ['$$post_id', '$post_id'] } } },
                    {
                        '$project': {
                            '_id': 0,
                            'user_id': { '$toString': '$user_id' }
                        }
                    }
                ],
                'as': 'retweets'
            }
        },
        {
            '$lookup': {
                'from': 'like', # getting likes for didLike
                'let': { 'post_id': '$_id' },
                'pipeline': [
                    { '$match': { '$expr': { '$eq': ['$$post_id', '$post_id'] } } },
                    {
                        '$project': {
                            '_id': 0,
                            'user_id': { '$toString': '$user_id' }
                        }
                    }
                ],
                'as': 'likes'
            }
        },
        { '$unwind': '$author' },
        { '$unwind': { 'path': '$parent', 'preserveNullAndEmptyArrays': True } },
        { '$unwind': { 'path': '$retweets_count', 'preserveNullAndEmptyArrays': True } },
        { '$unwind': { 'path': '$comments_count', 'preserveNullAndEmptyArrays': True } },
        { '$unwind': { 'path': '$likes_count', 'preserveNullAndEmptyArrays': True } },
        {
            '$project': {
                '_id': 0,
                'id': { '$toString': '$_id' },
                'author': 1,
                'text': 1,
                'date': 1,
                'img_path': { '$ifNull': ['$img_path', None] },
                'parent': { '$ifNull': ['$parent', None] },
                'children': 1,
                'retweets_count': '$retweets_count.count',
                'comments_count': '$comments_count.count',
                'likes_count': '$likes_count.count',
                'isAuthor': { '$cond': { 'if': { '$eq': ['$author.id', get_jwt_identity()] }, 'then': True, 'else': False } },
                'retweets': 1,
                'likes': 1
            }
        }
    ])

    post = post_data.next()

    if 'retweets_count' not in post:
        post['retweets_count'] = 0
    
    if 'comments_count' not in post:
        post['comments_count'] = 0
    
    if 'likes_count' not in post:
        post['likes_count'] = 0
    
    # adding images to post
    if post['img_path'] is not None:
        images_resources = api.resources(type='upload', prefix=post['img_path'])['resources']
        images = [image['secure_url'] for image in images_resources]
    else:
        images = []
    
    post['images'] = images

    # didRetweet
    didRetweet = False
    for retweet in post['retweets']:
        if retweet['user_id'] == get_jwt_identity():
            didRetweet = True
    
    post['didRetweet'] = didRetweet

    # didLike
    didLike = False
    for like in post['likes']:
        if like['user_id'] == get_jwt_identity():
            didLike = True

    post['didLike'] = didLike


    # children
    for child in post['children']:
        if 'retweets_count' not in child:
            child['retweets_count'] = 0
        
        if 'comments_count' not in child:
            child['comments_count'] = 0
        
        if 'likes_count' not in child:
            child['likes_count'] = 0
        
        # adding images to child
        if child['img_path'] is not None:
            child_resources = api.resources(type='upload', prefix=child['img_path'])['resources']
            child_images = [image['secure_url'] for image in child_resources]
        else:
            child_images = []
        
        child['images'] = child_images

        # didRetweet
        didRetweetChild = False
        for retweet in child['retweets']:
            if retweet['user_id'] == get_jwt_identity():
                didRetweetChild = True
        
        child['didRetweet'] = didRetweetChild

        # didLike
        didLike = False
        for like in child['likes']:
            if like['user_id'] == get_jwt_identity():
                didLike = True
        
        child['didLike'] = didLike

        del child['retweets']
        del child['likes']
    
    del post['retweets']
    del post['likes']

    return post, 200


# retweet()
@post_bp.route('/post/retweet/<string:post_id>', methods=['POST'])
@jwt_required()
def retweet(post_id):
    retweet = Retweet(user_id=get_jwt_identity(), post_id=post_id)
    retweet.save()

    return {
        'created': True,
        'retweet': {
            'id': str(retweet.pk),
            'user_id': retweet.user_id,
            'post_id': retweet.post_id
        }
    }, 201


# unretweet()
@post_bp.route('/post/retweet/<string:post_id>', methods=['DELETE'])
@jwt_required()
def unretweet(post_id):
    retweet = Retweet.objects(user_id=get_jwt_identity(), post_id=post_id).first()

    if retweet is not None:
        retweet.delete()

        return {
            'deleted': True,
            'retweet': {
                'id': str(retweet.pk),
                'user_id': retweet.user_id,
                'post_id': retweet.post_id
            }
        }, 200
    else:
        return { 'deleted': False, 'message': 'Retweet not found' }, 409
    

# search()
@post_bp.route('/search/<string:text>', methods=['GET'])
@jwt_required()
def search(text):
    # POSTS
    posts_data = Post.objects(text__icontains=text).aggregate([
        { '$sort': { '_id': -1 } },
        {
            '$lookup': {
                'from': 'user',
                'let': { 'author': '$author' },
                'pipeline': [
                    { '$match': { '$expr': { '$eq': ['$$author', '$_id'] } } },
                    {
                        '$project': {
                            '_id': 0,
                            'id': { '$toString': '$_id' },
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
                    { '$count': 'count' }
                ],
                'as': 'likes_count'
            }
        },
        {
            '$lookup': {
                'from': 'retweet', # getting retweets for didRetweet
                'let': { 'post_id': '$_id' },
                'pipeline': [
                    { '$match': { '$expr': { '$eq': ['$$post_id', '$post_id'] } } },
                    {
                        '$project': {
                            '_id': 0,
                            'user_id': { '$toString': '$user_id' }
                        }
                    }
                ],
                'as': 'retweets'
            }
        },
        {
            '$lookup': {
                'from': 'like',
                'let': { 'post_id': '$_id' },
                'pipeline': [
                    { '$match': { '$expr': { '$eq': ['$$post_id', '$post_id'] } } },
                    {
                        '$project': {
                            '_id': 0,
                            'user_id': { '$toString': '$user_id' }
                        }
                    }
                ],
                'as': 'likes'
            }
        },
        { '$unwind': '$author' },
        { '$unwind': { 'path': '$retweets_count' ,'preserveNullAndEmptyArrays': True } },
        { '$unwind': { 'path': '$comments_count' ,'preserveNullAndEmptyArrays': True } },
        { '$unwind': { 'path': '$likes_count' ,'preserveNullAndEmptyArrays': True } },
        {
            '$project': {
                '_id': 0,
                'id': { '$toString': '$_id' },
                'author': 1,
                'text': 1,
                'date': 1,
                'img_path': { '$ifNull': ['$img_path', None] },
                'retweets_count': '$retweets_count.count',
                'comments_count': '$comments_count.count',
                'likes_count': '$likes_count.count',
                'retweets': 1,
                'likes': 1
            }
        }
    ])

    posts = []

    for post in posts_data:
        if 'retweets_count' not in post:
            post['retweets_count'] = 0
        
        if 'comments_count' not in post:
            post['comments_count'] = 0
        
        if 'likes_count' not in post:
            post['likes_count'] = 0
        
        # adding images to post
        if post['img_path'] is not None:
            images_resources = api.resources(type='upload', prefix=post['img_path'])['resources']
            images = [image['secure_url'] for image in images_resources]
        else:
            images = []
        
        post['images'] = images

        # didRetweet
        didRetweet = False
        for retweet in post['retweets']:
            if retweet['user_id'] == get_jwt_identity():
                didRetweet = True
        
        post['didRetweet'] = didRetweet

        # didLike
        didLike = False
        for like in post['likes']:
            if like['user_id'] == get_jwt_identity():
                didLike = True
        
        post['didLike'] = didLike

        posts.append(post)

    # USERS
    users = [{
        'id': str(user.id),
        'full_name': user.full_name,
        'username': user.username
    } for user in User.objects(Q(username__icontains=text) | Q(full_name__icontains=text))]

    return { 'users': users, 'posts': posts }, 200


# like()
@post_bp.route('/post/like/<string:post_id>', methods=['POST'])
@jwt_required()
def like(post_id):
    like = Like(user_id=get_jwt_identity(), post_id=post_id)
    like.save()

    return {
        'created': True,
        'like': {
            'id': str(like.id),
            'user_id': like.user_id,
            'post_id': like.post_id
        }
    }, 201


# unlike()
@post_bp.route('/post/like/<string:post_id>', methods=['DELETE'])
@jwt_required()
def unlike(post_id):
    like = Like.objects(user_id=get_jwt_identity(), post_id=post_id).first()

    if like is not None:
        like.delete()

        return {
            'deleted': True,
            'like': {
                'id': str(like.id),
                'user_id': like.user_id,
                'post_id': like.post_id
            }
        }, 200
    else:
        return { 'deleted': False, 'message': 'Like not found' }, 409


# timeline()
@post_bp.route('/timeline', methods=['GET'])
@jwt_required()
def timeline():
    user_timeline_data = User.objects(id=get_jwt_identity()).aggregate([
        {
            '$lookup': {
                'from': 'user',
                'let': { 'following': '$following' },
                'pipeline': [
                    { '$match': { '$expr': { '$in': ['$_id', { '$ifNull': ['$$following', []] }] } } },
                    {
                        '$lookup': {
                            'from': 'post', # getting posts for following
                            'let': { 'id': '$_id' },
                            'pipeline': [
                                { '$match': { '$expr': { '$and': [
                                    { '$eq': ['$$id', '$author'] },
                                    { '$eq': [{ '$ifNull': ['$parent', None] }, None] }
                                ]} } },
                                { '$sort': { '_id': -1 } },
                                {
                                    '$lookup': {
                                        'from': 'retweet', # getting retweets count
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
                                        'from': 'post', # getting comments count
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
                                        'from': 'like', # getting likes count
                                        'let': { 'post_id': '$_id' },
                                        'pipeline': [
                                            { '$match': { '$expr': { '$eq': ['$$post_id', '$post_id'] } } },
                                            { '$count': 'count' }
                                        ],
                                        'as': 'likes_count'
                                    }
                                },
                                {
                                    '$lookup': {
                                        'from': 'retweet', # getting retweets for didRetweet
                                        'let': { 'post_id': '$_id' },
                                        'pipeline': [
                                            { '$match': { '$expr': { '$eq': ['$$post_id', '$post_id'] } } },
                                            {
                                                '$project': {
                                                    '_id': 0,
                                                    'user_id': { '$toString': '$user_id' }
                                                }
                                            }
                                        ],
                                        'as': 'retweets'
                                    }
                                },
                                {
                                    '$lookup': {
                                        'from': 'like', # getting likes for didLike
                                        'let': { 'post_id': '$_id' },
                                        'pipeline': [
                                            { '$match': { '$expr': { '$eq': ['$$post_id', '$post_id'] } } },
                                            {
                                                '$project': {
                                                    '_id': 0,
                                                    'user_id': { '$toString': '$user_id' }
                                                }
                                            }
                                        ],
                                        'as': 'likes'
                                    }
                                },
                                { '$unwind': { 'path': '$retweets_count', 'preserveNullAndEmptyArrays': True } },
                                { '$unwind': { 'path': '$comments_count', 'preserveNullAndEmptyArrays': True } },
                                { '$unwind': { 'path': '$likes_count', 'preserveNullAndEmptyArrays': True } },
                                {
                                    '$project': {
                                        '_id': 0,
                                        'id': { '$toString': '$_id' },
                                        'text': 1,
                                        'date': 1,
                                        'img_path': { '$ifNull': ['$img_path', None] },
                                        'retweets_count': '$retweets_count.count',
                                        'comments_count': '$comments_count.count',
                                        'likes_count': '$likes_count.count',
                                        'retweets': 1,
                                        'likes': 1
                                    }
                                }
                            ],
                            'as': 'posts'
                        }
                    },
                    {
                        '$lookup': {
                            'from': 'retweet', # getting retweets for following
                            'let': { 'user_id': '$_id' },
                            'pipeline': [
                                { '$match': { '$expr': { '$eq': ['$$user_id', '$user_id'] } } },
                                { '$sort': { '_id': -1 } },
                                {
                                    '$lookup': {
                                        'from': 'post', # getting post for retweets
                                        'let': { 'post_id': '$post_id' },
                                        'pipeline': [
                                            { '$match': { '$expr': { '$and': [
                                                { '$eq': ['$$post_id', '$_id'] },
                                                { '$eq': [{ '$ifNull': ['$parent', None] }, None] }
                                            ] } } },
                                            {
                                                '$lookup': {
                                                    'from': 'user', # getting author for post
                                                    'let': { 'author': '$author' },
                                                    'pipeline': [
                                                        { '$match': { '$expr': { '$eq': ['$$author', '$_id'] } } },
                                                        {
                                                            '$project': {
                                                                '_id': 0,
                                                                'id': { '$toString': '$_id'},
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
                                                    'from': 'retweet', # getting retweets count
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
                                                    'from': 'post', # getting comments count
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
                                                    'from': 'like', # getting likes count
                                                    'let': { 'post_id': '$_id' },
                                                    'pipeline': [
                                                        { '$match': { '$expr': { '$eq': ['$$post_id', '$post_id'] } } },
                                                        { '$count': 'count' }
                                                    ],
                                                    'as': 'likes_count'
                                                }
                                            },
                                            {
                                                '$lookup': {
                                                    'from': 'retweet', # getting retweets for didRetweet
                                                    'let': { 'post_id': '$_id' },
                                                    'pipeline': [
                                                        { '$match': { '$expr': { '$eq': ['$$post_id', '$post_id'] } } },
                                                        {
                                                            '$project': {
                                                                '_id': 0,
                                                                'user_id': { '$toString': '$user_id' }
                                                            }
                                                        }
                                                    ],
                                                    'as': 'retweets'
                                                }
                                            },
                                            {
                                                '$lookup': {
                                                    'from': 'like', # getting likes for didLike
                                                    'let': { 'post_id': '$_id' },
                                                    'pipeline': [
                                                        { '$match': { '$expr': { '$eq': ['$$post_id', '$post_id'] } } },
                                                        {
                                                            '$project': {
                                                                '_id': 0,
                                                                'user_id': { '$toString': '$user_id' }
                                                            }
                                                        }
                                                    ],
                                                    'as': 'likes'
                                                }
                                            },
                                            { '$unwind': '$author' },
                                            { '$unwind': { 'path': '$retweets_count', 'preserveNullAndEmptyArrays': True } },
                                            { '$unwind': { 'path': '$comments_count', 'preserveNullAndEmptyArrays': True } },
                                            { '$unwind': { 'path': '$likes_count', 'preserveNullAndEmptyArrays': True } },
                                            {
                                                '$project': {
                                                    '_id': 0,
                                                    'id': { '$toString': '$_id' },
                                                    'author': 1,
                                                    'text': 1,
                                                    'date': 1,
                                                    'img_path': { '$ifNull': ['$img_path', None] },
                                                    'retweets_count': '$retweets_count.count',
                                                    'comments_count': '$comments_count.count',
                                                    'likes_count': '$likes_count.count',
                                                    'retweets': 1,
                                                    'likes': 1,
                                                }
                                            }
                                        ],
                                        'as': 'post_id'
                                    }
                                },
                                { '$unwind': '$post_id' },
                                {
                                    '$project': {
                                        '_id': 0,
                                        'id': { '$toString': '$_id' },
                                        'post_id': 1
                                    }
                                }
                            ],
                            'as': 'retweets'
                        }
                    },
                    {
                        '$project': {
                            '_id': 0,
                            'id': { '$toString': '$_id' },
                            'full_name': 1,
                            'username': 1,
                            'posts': 1,
                            'retweets': 1
                        }
                    }
                ],
                'as': 'timeline'
            }
        },
        {
            '$lookup': {
                'from': 'post', # getting user logued posts
                'let': { 'id': '$_id' },
                'pipeline': [
                    { '$match': { '$expr': { '$and': [
                        { '$eq': ['$$id', '$author'] },
                        { '$eq': [{ '$ifNull': ['$parent', None] }, None]}
                    ] } } },
                    { '$sort': { '_id': -1 } },
                    {
                        '$lookup': {
                            'from': 'retweet', # getting retweets count
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
                            'from': 'like', # getting retweets count
                            'let': { 'post_id': '$_id' },
                            'pipeline': [
                                { '$match': { '$expr': { '$eq': ['$$post_id', '$post_id'] } } },
                                { '$count': 'count' }
                            ],
                            'as': 'likes_count'
                        }
                    },
                    {
                        '$lookup': {
                            'from': 'retweet', # getting retweets for didRetweet
                            'let': { 'post_id': '$_id' },
                            'pipeline': [
                                { '$match': { '$expr': { '$eq': ['$$post_id', '$post_id'] } } },
                                {
                                    '$project': {
                                        '_id': 0,
                                        'user_id': { '$toString': '$user_id' }
                                    }
                                }
                            ],
                            'as': 'retweets'
                        }
                    },
                    {
                        '$lookup': {
                            'from': 'like', # getting likes for didLike
                            'let': { 'post_id': '$_id' },
                            'pipeline': [
                                { '$match': { '$expr': { '$eq': ['$$post_id', '$post_id'] } } },
                                {
                                    '$project': {
                                        '_id': 0,
                                        'user_id': { '$toString': '$user_id' }
                                    }
                                }
                            ],
                            'as': 'likes'
                        }
                    },
                    { '$unwind': { 'path': '$retweets_count', 'preserveNullAndEmptyArrays': True } },
                    { '$unwind': { 'path': '$comments_count', 'preserveNullAndEmptyArrays': True } },
                    { '$unwind': { 'path': '$likes_count', 'preserveNullAndEmptyArrays': True } },
                    {
                        '$project': {
                            '_id': 0,
                            'id': { '$toString': '$_id' },
                            'text': 1,
                            'date': 1,
                            'img_path': { '$ifNull': ['$img_path', None] },
                            'retweets_count': '$retweets_count.count',
                            'comments_count': '$comments_count.count',
                            'likes_count': '$likes_count.count',
                            'retweets': 1,
                            'likes': 1
                        }
                    }
                ],
                'as': 'posts'
            }
        },
        {
            '$lookup': {
                'from': 'retweet', # getting retweets for user logued
                'let': { 'id': '$_id' },
                'pipeline': [
                    { '$match': { '$expr': { '$eq': ['$$id', '$user_id'] } } },
                    { '$sort': { '_id': -1 } },
                    {
                        '$lookup': {
                            'from': 'post',
                            'let': { 'post_id': '$post_id' },
                            'pipeline': [
                                { '$match': { '$expr': { '$and': [
                                    { '$eq': ['$$post_id', '$_id'] },
                                    { '$eq': [{ '$ifNull': ['$parent', None] }, None]}
                                ] } } },
                                {
                                    '$lookup': {
                                        'from': 'user',
                                        'let': { 'author': '$author' },
                                        'pipeline': [
                                            { '$match': { '$expr': { '$eq': ['$$author', '$_id'] } } },
                                            {
                                                '$project': {
                                                    '_id': 0,
                                                    'id': { '$toString': '$_id' },
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
                                        'from': 'retweet', # getting retweets count
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
                                        'from': 'like', # getting retweets count
                                        'let': { 'post_id': '$_id' },
                                        'pipeline': [
                                            { '$match': { '$expr': { '$eq': ['$$post_id', '$post_id'] } } },
                                            { '$count': 'count' }
                                        ],
                                        'as': 'likes_count'
                                    }
                                },
                                {
                                    '$lookup': {
                                        'from': 'retweet', # getting retweets for didRetweet
                                        'let': { 'post_id': '$_id' },
                                        'pipeline': [
                                            { '$match': { '$expr': { '$eq': ['$$post_id', '$post_id'] } } },
                                            {
                                                '$project': {
                                                    '_id': 0,
                                                    'user_id': { '$toString': '$user_id' }
                                                }
                                            }
                                        ],
                                        'as': 'retweets'
                                    }
                                },
                                {
                                    '$lookup': {
                                        'from': 'like', # getting likes for didLike
                                        'let': { 'post_id': '$_id' },
                                        'pipeline': [
                                            { '$match': { '$expr': { '$eq': ['$$post_id', '$post_id'] } } },
                                            {
                                                '$project': {
                                                    '_id': 0,
                                                    'user_id': { '$toString': '$user_id' }
                                                }
                                            }
                                        ],
                                        'as': 'likes'
                                    }
                                },
                                { '$unwind': '$author' },
                                { '$unwind': { 'path': '$retweets_count', 'preserveNullAndEmptyArrays': True } },
                                { '$unwind': { 'path': '$comments_count', 'preserveNullAndEmptyArrays': True } },
                                { '$unwind': { 'path': '$likes_count', 'preserveNullAndEmptyArrays': True } },
                                {
                                    '$project': {
                                        '_id': 0,
                                        'id': { '$toString': '$_id' },
                                        'author': 1,
                                        'text': 1,
                                        'date': 1,
                                        'img_path': { '$ifNull': ['$img_path', None] },
                                        'retweets_count': '$retweets_count.count',
                                        'comments_count': '$comments_count.count',
                                        'likes_count': '$likes_count.count',
                                        'retweets': 1,
                                        'likes': 1
                                    }
                                }
                            ],
                            'as': 'post_id'
                        }
                    },
                    { '$unwind': '$post_id' },
                    {
                        '$project': {
                            '_id': 0,
                            'id': { '$toString': '$_id' },
                            'post_id': 1
                        }
                    }
                ],
                'as': 'retweets'
            }
        },
        {
            '$project': {
                '_id': 0,
                'id': { '$toString': '$_id' },
                'full_name': 1,
                'username': 1,
                'timeline': 1,
                'posts': 1,
                'retweets': 1
            }
        }
    ])

    posts = []

    user_timeline = user_timeline_data.next()

    for user in user_timeline['timeline']:
        for post in user['posts']:
            # adding images to post
            if post['img_path'] is not None:
                images_resources = api.resources(type='upload', prefix=post['img_path'])['resources']
                images = [image['secure_url'] for image in images_resources]
            else:
                images = []
            
            post['images'] = images

            # adding author to post
            post['author'] = { 'id': user['id'], 'full_name': user['full_name'], 'username': user['username'] }

            if 'retweets_count' not in post:
                post['retweets_count'] = 0
            
            if 'comments_count' not in post:
                post['comments_count'] = 0
            
            if 'likes_count' not in post:
                post['likes_count'] = 0
            
            # didRetweet
            didRetweet = False
            for retweet in post['retweets']:
                if retweet['user_id'] == get_jwt_identity():
                    didRetweet = True
            
            post['didRetweet'] = didRetweet

            # didLike
            didLike = False
            for like in post['likes']:
                if like['user_id'] == get_jwt_identity():
                    didLike = True
            
            post['didLike'] = didLike

            # deleting retweets and likes fields
            del post['retweets']
            del post['likes']

            posts.append(post)
        
        for retweet in user['retweets']:
            # adding images to retweet
            if retweet['post_id']['img_path'] is not None:
                images_resources = api.resources(type='upload', prefix=retweet['post_id']['img_path'])['resources']
                images = [image['secure_url'] for image in images_resources]
            else:
                images = []
            
            retweet['post_id']['images'] = images

            # adding user_id to retweet
            retweet['user_id'] = { 'id': user['id'], 'full_name': user['full_name'], 'username': user['username'] }

            if 'retweets_count' not in retweet['post_id']:
                retweet['post_id']['retweets_count'] = 0
            
            if 'comments_count' not in retweet['post_id']:
                retweet['post_id']['comments_count'] = 0
            
            if 'likes_count' not in retweet['post_id']:
                retweet['post_id']['likes_count'] = 0
            
            # didRetweet
            didRetweetPost = False
            for r in retweet['post_id']['retweets']:
                if r['user_id'] == get_jwt_identity():
                    didRetweetPost = True
            
            retweet['post_id']['didRetweet'] = didRetweetPost

            # didLike
            didLikePost = False
            for like in retweet['post_id']['likes']:
                if like['user_id'] == get_jwt_identity():
                    didLikePost = True
            
            retweet['post_id']['didLike'] = didLikePost

            # deleting retweets and likes fields
            del retweet['post_id']['retweets']
            del retweet['post_id']['likes']

            posts.append(retweet)
    
    # USER POSTS
    for post in user_timeline['posts']:
        # adding images for post
        if post['img_path'] is not None:
            images_resources = api.resources(type='upload', prefix=post['img_path'])['resources']
            images = [image['secure_url'] for image in images_resources]
        else:
            images = []
        
        post['images'] = images

        # adding author for post
        post['author'] = { 'id': user_timeline['id'], 'full_name': user_timeline['full_name'], 'username': user_timeline['username'] }

        if 'retweets_count' not in post:
            post['retweets_count'] = 0
        
        if 'comments_count' not in post:
            post['comments_count'] = 0
        
        if 'likes_count' not in post:
            post['likes_count'] = 0
        
        # didRetweet
        didRetweet = False
        for retweet in post['retweets']:
            if retweet['user_id'] == get_jwt_identity():
                didRetweet = True
            
        post['didRetweet'] = didRetweet

        # didLike
        didLike = False
        for like in post['likes']:
            if like['user_id'] == get_jwt_identity():
                didLike = True
            
        post['didLike'] = didLike

        # deleting retweets and likes fields
        del post['retweets']
        del post['likes']

        posts.append(post)
    

    # USER RETWEETS
    for retweet in user_timeline['retweets']:
        # adding images to retweet
        if retweet['post_id']['img_path'] is not None:
            images_resources = api.resources(type='upload', prefix=retweet['post_id']['img_path'])['resources']
            images = [image['secure_url'] for image in images_resources]
        else:
            images = []
        
        retweet['post_id']['images'] = images

        # adding user_id to retweet
        retweet['user_id'] = { 'id': user_timeline['id'], 'full_name': user_timeline['full_name'], 'username': user_timeline['username'] }

        if 'retweets_count' not in retweet['post_id']:
            retweet['post_id']['retweets_count'] = 0
            
        if 'comments_count' not in retweet['post_id']:
            retweet['post_id']['comments_count'] = 0
            
        if 'likes_count' not in retweet['post_id']:
            retweet['post_id']['likes_count'] = 0
            
        # didRetweet
        didRetweetPost = False
        for r in retweet['post_id']['retweets']:
            if r['user_id'] == get_jwt_identity():
                didRetweetPost = True
            
        retweet['post_id']['didRetweet'] = didRetweetPost

        # didLike
        didLikePost = False
        for like in retweet['post_id']['likes']:
            if like['user_id'] == get_jwt_identity():
                didLikePost = True
            
        retweet['post_id']['didLike'] = didLikePost

        # deleting retweets and likes fields
        del retweet['post_id']['retweets']
        del retweet['post_id']['likes']

        posts.append(retweet)
    
    posts_sorted = sorted(posts, key = lambda i:ObjectId(i['id']).generation_time, reverse=True)

    return { 'get': True, 'posts': posts_sorted }, 200
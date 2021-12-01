# post.py

from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.user import User
from models.post import Post
from models.retweet import Retweet
from mongoengine.queryset.visitor import Q
from cloudinary import uploader
import time
import pprint

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

        for index, image in enumerate(request.files.getlist('images'), start=1):
            print(index, image.filename)
            uploader.upload_image(image, folder=f'hashtage/{str(post.author.pk)}/{str(post.pk)}', 
            public_id=str(time.time()))
    
    return {
        'created': True,
        'post': {
            'id': str(post.pk),
            'author': post.author,
            'text': post.text,
            'date': post.date,
            'img_path': post.img_path
        }
    }, 201


# delete_post()
@post_bp.route('/post/<string:post_id>', methods=['DELETE'])
@jwt_required()
def delete_post(post_id):
    post = Post.objects(id=post_id).first()

    if post is not None:
        post.delete()
        return {
            'deleted': True,
            'post': {
                'id': str(post.pk),
                'author': post.author,
                'text': post.text,
                'date': post.date,
                'img_path': post.img_path
            }
        }, 200
    else:
        return { 'deleted': False, 'message': 'Post not found' }, 409


# get_all_posts()
@post_bp.route('/post', methods=['GET'])
@jwt_required()
def get_all_posts():
    try:
        posts = []

        for post in Post.objects(parent=None):
            posts.append({
                'id': str(post.pk),
                'author': post.author,
                'text': post.text,
                'date': post.date,
                'img_path': post.img_path,
                'retweets_count': Retweet.objects(post_id=str(post.pk)).count()
            })

        return { 'get': True, 'posts': posts }, 200
    except:
        return { 'get': False, 'message': 'No posts' }, 409


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

    return {
        'created': True,
        'comment': {
            'id': str(comment.pk),
            'text': comment.text,
            'author': comment.author,
            'date': comment.date,
            'img_path': comment.img_path,
            'parent': comment.parent
        }
    }, 201


# FUNCTION getChildren()
def getChildren(comment_parent):
    children = []
    for comment in Post.objects(parent=comment_parent):
        children.append({
            'id': str(comment.pk),
            'author': comment.author,
            'text': comment.text,
            'date': comment.date,
            'img_path': comment.img_path,
            'parent': comment.parent,
            'retweets_count': Retweet.objects(post_id=str(comment.pk)).count(),
            'children': getChildren(str(comment.pk))
        })
    
    return children
    

# get_post_info()
@post_bp.route('/post/<string:post_id>', methods=['GET'])
@jwt_required()
def get_post_info(post_id):
    post = Post.objects(id=post_id).first()
    
    comments = []

    for comment in Post.objects(parent=post_id):
        comments.append({
            'id': str(comment.pk),
            'author': comment.author,
            'text': comment.text,
            'date': comment.date,
            'img_path': comment.img_path,
            'parent': comment.parent,
            'retweets_count': Retweet.objects(post_id=str(comment.pk)).count(),
            'children': getChildren(str(comment.pk))
        })

    return {
        'id': str(post.pk),
        'author': post.author,
        'text': post.text,
        'date': post.date,
        'img_path': post.img_path,
        'retweets_count': Retweet.objects(post_id=post_id).count(),
        'children': comments
    }


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
@post_bp.route('/post/retweet/<string:retweet_id>', methods=['DELETE'])
@jwt_required()
def unretweet(retweet_id):
    retweet = Retweet.objects(id=retweet_id).first()

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
@post_bp.route('/search/<string:text>', methods=['POST'])
@jwt_required()
def search(text):
    posts = []

    for post in Post.objects(text__contains=text, parent=None):
        posts.append({
            'id': str(post.pk),
            'author': post.author,
            'text': post.text,
            'date': post.date,
            'img_path': post.img_path,
            'retweets_count': Retweet.objects(post_id=str(post.pk)).count()
        })
    
    users = []

    for user in User.objects(Q(username__contains=text) | Q(full_name__contains=text)):
        users.append({
            'id': str(user.pk),
            'full_name': user.full_name,
            'username': user.username,
            'address': user.address,
            'birthday': user.birthday,
            'bio': user.bio,
            'followers': user.followers,
            'following': user.following
        })
    return {
        'posts': posts,
        'users': users
    }, 200
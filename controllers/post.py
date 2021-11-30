# post.py

from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.post import Post

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
    
    return {
        'created': True,
        'post': {
            '_id': str(post.pk),
            'author': post.author,
            'text': post.text,
            'date': post.date
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
            'delete': True,
            'post': {
                '_id': str(post.pk),
                'author': post.author,
                'text': post.text,
                'date': post.date
            }
        }, 200
    else:
        return { 'delete': False, 'message': 'Post not found' }


# get_all_posts()
@post_bp.route('/post', methods=['GET'])
@jwt_required()
def get_all_posts():
    posts_obj = Post.objects()

    posts = []

    for post in posts_obj:
        p = {
            '_id': str(post.pk),
            'author': post.author,
            'text': post.text,
            'date': post.date
        }
        posts.append(p)

    return { 'posts': posts }, 200


# get_user_posts()
@post_bp.route('/user/<string:user_id>', methods=['GET'])
@jwt_required()
def get_user_posts(user_id):
    user_posts = Post.objects(author=user_id)

    user = {
        '_id': str(user_posts[0].author.pk),
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
            '_id': str(post.pk),
            'text': post.text,
            'date': post.date
        }
        posts.append(p)

    return { 'user': user, 'posts': posts }, 200


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
            '_id': str(comment.pk),
            'text': comment.text,
            'author': comment.author,
            'date': comment.date,
            'img_path': comment.img_path,
            'parent': comment.parent
        }
    }
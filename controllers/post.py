# post.py

from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.post import Post
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
        return { 'deleted': False, 'message': 'Post not found' }


# get_all_posts()
@post_bp.route('/post', methods=['GET'])
@jwt_required()
def get_all_posts():
    try:
        posts = []

        for post in Post.objects(parent=None):
            p = {
                'id': str(post.pk),
                'author': post.author,
                'text': post.text,
                'date': post.date
            }
            posts.append(p)

        return { 'get': True, 'posts': posts }, 200
    except:
        return { 'get': False, 'message': 'No posts' }


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
            'children': getChildren(str(comment.pk))
        })

    post_dict = {
        'id': str(post.pk),
        'author': post.author,
        'text': post.text,
        'date': post.date,
        'img_path': post.img_path,
        'children': comments
    }

    pp = pprint.PrettyPrinter(sort_dicts=False)
    pp.pprint(post_dict)


    return {
        'id': str(post.pk),
        'author': post.author,
        'text': post.text,
        'date': post.date,
        'img_path': post.img_path,
        'children': comments
    }
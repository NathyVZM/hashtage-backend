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

    return {
        '_id': str(post.pk),
        'author': post.author,
        'text': post.text,
        'date': post.date
    }, 201


@post_bp.route('/post/<string:post_id>', methods=['DELETE'])
def delete_post(post_id):
    pass
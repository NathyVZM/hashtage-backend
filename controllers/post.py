# post.py

import pprint
from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.user import User
from models.post import Post
from models.retweet import Retweet
from models.like import Like
from mongoengine.queryset.visitor import Q
from cloudinary import uploader, api
import time

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
    try:
        posts = []

        for post in Post.objects(parent=None).order_by('-id'):
            if post.img_path is not None:
                images_resources = api.resources(type='upload', prefix=post.img_path)['resources']
                images = [image['secure_url'] for image in images_resources]
            else:
                images = []
            
            isAuthor = True if str(post.author.id) == get_jwt_identity() else False
            
            didRetweet = False
            for retweet in Retweet.objects(post_id=str(post.pk)).order_by('-id'):
                if str(retweet.user_id.pk) == get_jwt_identity():
                    didRetweet = True
            
            didLike = False
            for like in Like.objects(post_id=str(post.id)).order_by('-id'):
                if str(like.user_id.id) == get_jwt_identity():
                    didLike = True

                posts.append({
                    'id': str(retweet.pk),
                    'user_id': {
                        'id': str(retweet.user_id.pk),
                        'full_name': retweet.user_id.full_name,
                        'username': retweet.user_id.username
                    },
                    'post_id': {
                        'id': str(retweet.post_id.pk),
                        'author': retweet.post_id.author,
                        'text': retweet.post_id.text,
                        'date': retweet.post_id.date,
                        'images': images,
                        'retweets_count': Retweet.objects(post_id=str(retweet.post_id.pk)).count(),
                        'didRetweet': didRetweet,
                        'didLike': didLike,
                        'comments_count': Post.objects(parent=str(retweet.post_id.pk)).count(),
                        'likes_count': Like.objects(post_id=str(retweet.post_id.id)).count(),
                        'isAuthor': isAuthor
                    }
                })
            
            posts.append({
                'id': str(post.pk),
                'author': post.author,
                'text': post.text,
                'date': post.date,
                'images': images,
                'retweets_count': Retweet.objects(post_id=str(post.pk)).count(),
                'didRetweet': didRetweet,
                'didLike': didLike,
                'comments_count': Post.objects(parent=str(post.pk)).count(),
                'likes_count': Like.objects(post_id=str(post.id)).count(),
                'isAuthor': isAuthor
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
        for index, image in enumerate(request.files.getlist('images'), start=1):
            print(index, image.filename)
            uploader.upload_image(image, folder=f'hashtage/{str(comment.author.pk)}/{str(comment.pk)}',
            public_id=str(time.time()))

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
        if comment.img_path is not None:
            images_resources = api.resources(type='upload', prefix=comment.img_path)['resources']
            images = [image['secure_url'] for image in images_resources]
        else:
            images = []
        
        didRetweet = False
        for retweet in Retweet.objects(post_id=str(comment.pk)):
            if str(retweet.user_id.pk) == get_jwt_identity():
                didRetweet = True

        didLike = False
        for like in Like.objects(post_id=str(comment.id)):
            if str(like.user_id.id) == get_jwt_identity():
                didLike = True
        
        isAuthor = True if str(comment.author.id) == get_jwt_identity() else False
        
        children.append({
            'id': str(comment.pk),
            'author': {
                'id': str(comment.author.id),
                'full_name': comment.author.full_name,
                'username': comment.author.username
            },
            'text': comment.text,
            'date': comment.date,
            'images': images,
            'parent': str(comment.parent.id),
            'retweets_count': Retweet.objects(post_id=str(comment.pk)).count(),
            'didRetweet': didRetweet,
            'didLike': didLike,
            'comments_count': Post.objects(parent=str(comment.pk)).count(),
            'likes_count': Like.objects(post_id=str(comment.id)).count(),
            'children': getChildren(str(comment.pk)),
            'isAuthor': isAuthor
        })
    
    return children
    

# get_post_info()
@post_bp.route('/post/<string:post_id>', methods=['GET'])
@jwt_required()
def get_post_info(post_id):
    post = Post.objects(id=post_id).first()

    if post.img_path is not None:
        images_resources = api.resources(type='upload', prefix=post.img_path)['resources']
        images = [image['secure_url'] for image in images_resources]
    else:
        images = []

    didRetweet = False
    for retweet in Retweet.objects(post_id=str(post.pk)):
        if str(retweet.user_id.pk) == get_jwt_identity():
            didRetweet = True
    
    didLike = False
    for like in Like.objects(post_id=str(post.id)):
        if str(like.user_id.id) == get_jwt_identity():
            didLike = True

    comments = []

    for comment in Post.objects(parent=post_id):
        if comment.img_path is not None:
            comment_resources = api.resources(type='upload', prefix=comment.img_path)['resources']
            comment_images = [image['secure_url'] for image in comment_resources]
        else:
            comment_images = []
        
        didRetweetComment = False
        for retweet in Retweet.objects(post_id=str(comment.pk)):
            if str(retweet.user_id.pk) == get_jwt_identity():
                didRetweetComment = True
        
        didLikeComment = False
        for like in Like.objects(post_id=str(comment.id)):
            if str(like.user_id.id) == get_jwt_identity():
                didLikeComment = True

        isAuthorComment = True if get_jwt_identity() == str(comment.author.id) else False

        comments.append({
            'id': str(comment.pk),
            'author': comment.author,
            'text': comment.text,
            'date': comment.date,
            'images': comment_images,
            'parent': comment.parent,
            'retweets_count': Retweet.objects(post_id=str(comment.pk)).count(),
            'didRetweet': didRetweetComment,
            'didLike': didLikeComment,
            'comments_count': Post.objects(parent=str(comment.pk)).count(),
            'likes_count': Like.objects(post_id=str(comment.id)).count(),
            'children': getChildren(str(comment.pk)),
            'isAuthor': isAuthorComment
        })

    isAuthor = True if get_jwt_identity() == str(post.author.id) else False
        
    return {
        'id': str(post.pk),
        'author': post.author,
        'text': post.text,
        'date': post.date,
        'images': images,
        'retweets_count': Retweet.objects(post_id=post_id).count(),
        'didRetweet': didRetweet,
        'didLike': didLike,
        'comments_count': Post.objects(parent=post_id).count(),
        'likes_count': Like.objects(post_id=post_id).count(),
        'children': comments,
        'isAuthor': isAuthor
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
    posts = []

    for post in Post.objects(text__icontains=text).order_by('-id'):
        if post.img_path is not None:
            images_resources = api.resources(type='upload', prefix=post.img_path)['resources']
            images = [image['secure_url'] for image in images_resources]
        else:
            images = []
        
        didRetweet = False
        for retweet in Retweet.objects(post_id=str(post.pk)):
            if str(retweet.user_id.pk) == get_jwt_identity():
                didRetweet = True
        
        didLike = False
        for like in Like.objects(post_id=str(post.id)):
            if str(like.user_id.id) == get_jwt_identity():
                didLike = True
        
        posts.append({
            'id': str(post.pk),
            'author': post.author,
            'text': post.text,
            'date': post.date,
            'images': images,
            'parent': post.parent,
            'retweets_count': Retweet.objects(post_id=str(post.pk)).count(),
            'didRetweet': didRetweet,
            'didLike': didLike,
            'comments_count': Post.objects(parent=str(post.pk)).count(),
            'likes_count': Like.objects(post_id=str(post.id)).count()
        })

    users = [{
        'id': str(user.pk),
        'full_name': user.full_name,
        'username': user.username,
        'address': user.address,
        'birthday': user.birthday,
        'bio': user.bio,
        'followers': len(user.followers),
        'following': len(user.following)
    } for user in User.objects(Q(username__icontains=text) | Q(full_name__icontains=text))]

    return {
        'posts': posts,
        'users': users
    }, 200


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
    user = User.objects(id=get_jwt_identity()).first()

    posts = []

    for following in user.following:

        for post in Post.objects(author=str(following.id), parent=None).order_by('-id'):
            if post.img_path is not None:
                images_resources = api.resources(type='upload', prefix=post.img_path)['resources']
                images = [image['secure_url'] for image in images_resources]
            else:
                images = []

            didRetweet = False
            for retweet in Retweet.objects(post_id=str(post.id)):
                if str(retweet.user_id.id) == get_jwt_identity():
                    didRetweet = True
            
            didLike = False
            for like in Like.objects(post_id=str(post.id)):
                if str(like.user_id.id) == get_jwt_identity():
                    didLike = True
                
            isAuthor = True if str(post.author.id) == get_jwt_identity() else False

            posts.append({
                'id': str(post.id),
                'author': post.author,
                'text': post.text,
                'date': post.date,
                'images': images,
                'retweets_count': Retweet.objects(post_id=str(post.id)).count(),
                'comments_count': Post.objects(parent=str(post.id)).count(),
                'likes_count': Like.objects(post_id=str(post.id)).count(),
                'didRetweet': didRetweet,
                'didLike': didLike,
                'isAuthor': isAuthor
            })
        for retweet in Retweet.objects(user_id=str(following.id)).order_by('-id'):
            if retweet.post_id.img_path is not None:
                retweet_resources = api.resources(type='upload', prefix=retweet.post_id.img_path)['resources']
                retweet_images = [image['secure_url'] for image in retweet_resources]
            else:
                retweet_images = []

            didRetweetPost = False
            for r in Retweet.objects(post_id=str(retweet.post_id.id)):
                if str(r.user_id.id) == get_jwt_identity():
                    didRetweetPost = True
            
            didLikePost = False
            for like in Like.objects(post_id=str(retweet.post_id.id)):
                if str(like.user_id.id) == get_jwt_identity():
                    didLikePost = True
            
            isAuthorPost = True if str(retweet.post_id.author.id) == get_jwt_identity() else False

            posts.append({
                'id': str(retweet.id),
                'post_id': {
                    'id': str(retweet.post_id.id),
                    'author': retweet.post_id.author,
                    'text': retweet.post_id.text,
                    'date': retweet.post_id.date,
                    'images': retweet_images,
                    'retweets_count': Retweet.objects(post_id=str(retweet.post_id.id)).count(),
                    'comments_count': Post.objects(parent=str(retweet.post_id.id)).count(),
                    'likes_count': Like.objects(post_id=str(retweet.post_id.id)).count(),
                    'didRetweet': didRetweetPost,
                    'didLike': didLikePost,
                    'isAuthor': isAuthorPost
                },
                'user_id': {
                    'id': str(retweet.user_id.id),
                    'full_name': retweet.user_id.full_name,
                    'username': retweet.user_id.username
                }
            })

    return {
        'get': True,
        'posts': posts
    }, 200
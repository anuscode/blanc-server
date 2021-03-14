import json
import uuid
import pendulum

from flask import abort
from flask import Blueprint
from flask import Response
from flask import request
from firebase_admin import storage
from model.models import Alarm, AlarmRecord, User, Post, Comment, Resource
from shared import message_service
from shared.annotation import time_lapse
from shared.json_encoder import encode

posts_blueprint = Blueprint('posts_blueprint', __name__)


@posts_blueprint.route('/posts', methods=['POST'])
def route_create_post():
    uid = request.headers.get("uid", None)
    if not uid:
        abort(401)

    params = request.form.to_dict(flat=True)
    post_images = request.files.values()
    description = params.get("description", None)
    title = params.get("title", None)
    enable_comment = params.get("enable_comment", 'false')
    enable_comment = True if enable_comment == "true" else False

    user = User.objects(uid=uid).get_or_404()

    resources = []
    for post_image in post_images:
        # update to image server
        bucket = storage.bucket()
        blob = bucket.blob('post_images/{uid}/{uuid}_{timestamp}'.format(
            uid=uid,
            uuid=uuid.uuid1(),
            timestamp=pendulum.now().int_timestamp)
        )
        blob.upload_from_file(post_image)
        resource = Resource(type="IMAGE", url=blob.public_url)
        resources.append(resource)

    if not post_images and not params.get("description", ""):
        raise ValueError("이미지 및 게시글 중 최소 한개는 충족 되어야 합니다.")

    # create a post in mongo db.
    post = Post.create(
        author=user,
        title=title,
        description=description,
        resources=resources,
        created_at=pendulum.now().int_timestamp,
        enable_comment=enable_comment
    )

    response = json.dumps(dict(_id=str(post.id)))
    return Response(response, mimetype="application/json")


@posts_blueprint.route('/posts', methods=['GET'])
@time_lapse
def route_list_posts():
    uid = request.headers.get("uid", None)
    user = User.get(uid=uid)
    opposite_sex = "M" if user.sex == "F" else "F"

    last_id: str = request.args.get("last_id", None)
    per_page: int = int(request.args.get("per_page", 30))

    params = dict(author_sex=opposite_sex)
    if last_id:
        params["id__lt"] = last_id

    result = Post.list_posts(**params, limit=per_page)

    response = encode(list(result))
    return Response(response, mimetype="application/json")


@posts_blueprint.route('/posts/<post_id>', methods=['GET'])
def route_get_post(post_id):
    post = Post.get_post(id=post_id)
    response = encode(post)
    return Response(response, mimetype="application/json")


@posts_blueprint.route('/posts/<post_id>', methods=['DELETE'])
def delete_post(post_id):
    post = Post.objects.get_or_404(id=post_id)
    post.delete()
    response = json.dumps(dict(_id=str(post.id)))
    return Response(response, mimetype="application/json")


@posts_blueprint.route('/posts/<post_id>/favorite', methods=['POST'])
def route_create_favorite(post_id: str):
    uid = request.headers.get("uid", None)
    if not uid:
        abort(401)

    user = User.objects.get_or_404(uid=uid)
    post = Post.objects.get_or_404(id=post_id)
    post.update(add_to_set__favorite_user_ids=user.id)

    user_from = user
    user_to = post.author

    alarm = Alarm.create_alarm(
        user_from=user_from,
        user_to=user_to,
        event=Alarm.Event.FAVORITE,
        post=post,
        message="{nickname} 님이 당신의 게시물을 좋아합니다.".format(nickname=user_from.nickname))

    alarm_record: AlarmRecord = alarm.records[-1]
    data: dict = alarm_record.as_dict()
    message_service.push(data, user_to.device_token)

    return Response("", mimetype="application/json")


@posts_blueprint.route('/posts/<post_id>/favorite', methods=['DELETE'])
def route_delete_favorite(post_id):
    uid = request.headers.get("uid", None)
    if not uid:
        abort(401)

    user = User.objects.get_or_404(uid=uid)
    post = Post.objects.get_or_404(id=post_id)
    post.update(pull__favorite_user_ids=user.id)

    return Response("", mimetype="application/json")


@posts_blueprint.route('/posts/<post_id>/comments', methods=['POST'])
def route_create_comment(post_id: str):
    uid = request.headers.get("uid", None)
    if not uid:
        abort(401)

    # if exists, create a comment as a sub comment
    comment_id = request.form.get("comment_id", None)  # parent_comment_id
    comment = request.form.get("comment", "")

    post = Post.objects.get_or_404(id=post_id)
    user = User.objects.get_or_404(uid=uid)

    comment_to_create = Comment(
        post_id=post_id,
        user_id=user.id,
        comment=comment,
        comments=[],  # child comments
        created_at=pendulum.now().int_timestamp
    ).save()

    post.add_comment(comment_to_create, parent_id=comment_id)

    alarm = Alarm.create_alarm(
        user_from=user,
        user_to=post.author,
        event=Alarm.Event.COMMENT,
        post=post,
        comment=comment_to_create,
        message="{nickname} 님이 당신의 게시물에 댓글을 남겼습니다.".format(nickname=user.nickname))

    alarm_record = alarm.records[-1]
    data = alarm_record.as_dict()
    message_service.push(data, post.author.device_token)

    comment = comment_to_create.to_mongo()
    comment["commenter"] = User.get(id=user.id).to_mongo()

    response = encode(comment)
    return Response(response, mimetype="application/json")


@posts_blueprint.route('/posts/<post_id>/comments/<comment_id>/thumb_up', methods=['POST'])
def route_create_thumb_up(post_id, comment_id):
    uid = request.headers.get("uid", None)
    if not uid:
        abort(401)

    user = User.objects.get_or_404(uid=uid)
    post = Post.objects.get_or_404(id=post_id)
    comment = next(
        (comment for comment in post.comments
         if str(comment.id) == comment_id), None)

    if not comment:
        abort(404)

    comment.update(add_to_set__thumb_up_user_ids=user.id, pull__thumb_down_user_ids=user.id)
    comment = Comment.objects.get_or_404(id=comment_id)

    if user.id == post.author.id:
        user_from = user
        user_to = User.get(id=comment.user_id)

        alarm = Alarm.create_alarm(
            user_from=user_from,
            user_to=user_to,
            event=Alarm.Event.THUMB_UP,
            post=post,
            comment=comment,
            message="{nickname} 님이 당신의 댓글을 좋아합니다.".format(nickname=user_from.nickname))
        alarm_record = alarm.records[-1]
        data = alarm_record.as_dict()
        message_service.push(data, user_to.device_token)

    return Response("", mimetype="application/json")


@posts_blueprint.route('/posts/<post_id>/comments/<comment_id>/thumb_up', methods=['DELETE'])
def route_delete_thumb_up(post_id, comment_id):
    uid = request.headers.get("uid", None)

    if not uid:
        abort(401)

    user = User.objects.get_or_404(uid=uid)
    post = Post.objects.get_or_404(id=post_id)
    comment = next((comment for comment in post.comments if str(comment.id) == comment_id), None)

    comment.update(pull__thumb_up_user_ids=user.id)

    return Response("", mimetype="application/json")


@posts_blueprint.route('/posts/<post_id>/comments/<comment_id>/thumb_down', methods=['POST'])
def route_create_thumb_down(post_id, comment_id):
    uid = request.headers.get("uid", None)
    if not uid:
        abort(401)

    user = User.objects.get_or_404(uid=uid)
    post = Post.objects.get_or_404(id=post_id)
    comment = next(
        (comment for comment in post.comments
         if str(comment.id) == comment_id), None)

    comment.update(add_to_set__thumb_down_user_ids=user.id, pull__thumb_up_user_ids=user.id)

    return Response("", mimetype="application/json")


@posts_blueprint.route('/posts/<post_id>/comments/<comment_id>/thumb_down', methods=['DELETE'])
def route_delete_thumb_down(post_id, comment_id):
    uid = request.headers.get("uid", None)
    if not uid:
        abort(401)

    user = User.objects.get_or_404(uid=uid)
    post = Post.objects.get_or_404(id=post_id)
    comment = next(
        (comment for comment in post.comments
         if str(comment.id) == comment_id), None)

    comment.update(pull__thumb_down_user_ids=user.id)

    return Response("", mimetype="application/json")


@posts_blueprint.route('/posts/<post_id>/favorite', methods=['GET'])
def route_list_all_favorite_users(post_id):
    uid = request.headers.get("uid", None)
    post = Post.objects.get_or_404(id=post_id)

    if post.author.uid != uid:
        abort(401)

    favorite_user_ids = post.favorite_user_ids
    users = User.objects(id__in=favorite_user_ids) \
        .exclude(*User.excludes()).as_pymongo()

    response = encode(list(users))
    return Response(response, mimetype="application/json")

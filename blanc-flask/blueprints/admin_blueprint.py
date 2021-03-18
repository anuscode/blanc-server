"""Admin blue print definitions."""

import json
from flask import abort
from flask import Blueprint
from flask import Response
from flask import request
from model.models import Admin, User, Alarm, Post
from shared import message_service
from shared.json_encoder import encode

admin_blueprint = Blueprint("admin_blueprint", __name__)


@admin_blueprint.route("/admin/session", methods=["GET"])
def route_admin_session():
    """Checks session.."""
    uid = request.headers.get("uid", None)
    admin = Admin.objects(uid=uid).first()

    if not admin:
        admin = Admin(uid=uid, available=False)
        admin.save()
        admin.reload()

    uid = admin.user.uid if admin.user else None
    available = admin.available

    response = encode(dict(uid=uid, available=available))
    return Response(response, mimetype="application/json")


@admin_blueprint.route("/admin/users/status/<status>", methods=["GET"])
def route_list_pending_users(status: str):
    """Retrieves all pending users."""

    uid = request.headers.get("uid", None)
    admin = Admin.objects.get_or_404(uid=uid)

    if not admin.available:
        abort(401)

    status = status or ""
    status = status.upper()
    users = User.objects(status=status).as_pymongo()

    response = encode(list(users))
    return Response(response, mimetype="application/json")


@admin_blueprint.route("/admin/posts", methods=["GET"])
def route_list_posts():
    """Lists all posts not filtering opposite sex things."""
    uid = request.headers.get("uid", None)
    admin = Admin.objects.get_or_404(uid=uid)

    if not admin.available:
        abort(401)

    last_id: str = request.args.get("last_id", None)
    per_page: int = int(request.args.get("per_page", 30))

    params = dict(is_deleted=False, limit=per_page)
    if last_id:
        params["id__lt"] = last_id

    result = Post.list_posts(**params)

    response = encode(list(result))
    return Response(response, mimetype="application/json")


@admin_blueprint.route("/admin/posts/<post_id>", methods=["DELETE"])
def route_delete_post(post_id: str):
    """Deletes a post by admin."""
    uid = request.headers.get("uid", None)
    admin = Admin.objects.get_or_404(uid=uid)

    if not admin.available:
        abort(401)

    post = Post.objects.get_or_404(id=post_id)
    post.is_deleted = True
    post.save()

    return Response("", mimetype="application/json")


@admin_blueprint.route("/admin/posts/<post_id>/comments/<comment_id>", methods=["DELETE"])
def route_delete_comment(post_id: str, comment_id: str):
    """Deletes a post by admin."""
    uid = request.headers.get("uid", None)
    admin = Admin.objects.get_or_404(uid=uid)

    if not admin.available:
        abort(401)

    post = Post.objects.get_or_404(id=post_id)

    def search_comment(comments: list, cid: str):
        found = None
        for c in comments:
            if str(c.id) == cid:
                found = c
                break
            if c.comments:
                found = search_comment(c.comments, cid)
            if found:
                break
        return found

    comment = search_comment(post.comments, comment_id)
    if comment:
        comment.is_deleted = True
        comment.save()
    else:
        abort(404)

    return Response("", mimetype="application/json")


@admin_blueprint.route("/admin/users/<user_id>/status/approved", methods=["PUT"])
def route_approve_users(user_id: str):
    """Updates user status APPROVED."""

    uid = request.headers.get("uid", None)
    admin = Admin.objects.get_or_404(uid=uid)
    if not admin.available:
        abort(401)

    user = User.objects.get_or_404(id=user_id)

    user.user_images = user.user_images_temp
    user.status = User.Status.APPROVED
    user.available = True
    user.save()

    message_service.push(dict(event=Alarm.Event.APPROVED), user.device_token)

    return Response("", mimetype="application/json")


@admin_blueprint.route("/admin/users/<user_id>/status/rejected", methods=["PUT"])
def route_reject_users(user_id: str):
    """Updates user status REJECTED."""

    uid = request.headers.get("uid", None)
    admin = Admin.objects.get_or_404(uid=uid)
    if not admin.available:
        abort(401)

    user = User.objects.get_or_404(id=user_id)

    user.status = User.Status.REJECTED
    user.available = False
    user.save()

    message_service.push(dict(event=Alarm.Event.REJECTED), user.device_token)

    return Response("", mimetype="application/json")


@admin_blueprint.route("/admin/users/<user_id>/status/blocked", methods=["PUT"])
def route_block_users(user_id: str):
    """Updates user status BLOCKED."""

    uid = request.headers.get("uid", None)
    admin = Admin.objects.get_or_404(uid=uid)
    if not admin.available:
        abort(401)

    user = User.objects.get_or_404(id=user_id)

    user.status = User.Status.BLOCKED
    user.available = False
    user.save()

    message_service.push(dict(event=Alarm.Event.BLOCKED), user.device_token)

    return Response("", mimetype="application/json")

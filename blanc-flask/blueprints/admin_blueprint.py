"""User blue print definitions."""

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
    """Retrieves all pending users."""
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

    status = status or ""
    status = status.upper()
    users = User.objects(status=status).as_pymongo()

    response = encode(list(users))
    return Response(response, mimetype="application/json")


@admin_blueprint.route("/admin/posts", methods=["GET"])
def route_list_posts():
    """List all posts"""
    last_id: str = request.args.get("last_id", None)
    per_page: int = int(request.args.get("per_page", 30))

    params = dict(id__lt=last_id) if last_id else dict()
    result = Post.list_posts(**params, limit=per_page)

    response = encode(list(result))
    return Response(response, mimetype="application/json")


@admin_blueprint.route("/admin/users/<user_id>/status/approved", methods=["PUT"])
def route_approve_users(user_id: str):
    """Updates user status to APPROVED."""

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
    """Updates user status to REJECTED."""

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
    """Updates user status to BLOCKED."""

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

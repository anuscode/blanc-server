"""User blue print definitions."""

from flask import abort
from flask import Blueprint
from flask import Response
from flask import request
from model.models import User
from shared import message_service
from shared.json_encoder import encode

admin_blueprint = Blueprint("admin_blueprint", __name__)


@admin_blueprint.route("/admin/users/status/<status>", methods=["GET"])
def route_list_pending_users(status: str):
    """Retrieves all pending users."""

    uid = request.headers.get("uid", None)
    admin = User.objects.get_or_404(uid=uid)
    if not admin.is_admin():
        abort(401)

    status = status or ""
    status = status.upper()
    users = User.objects(status=status).as_pymongo()

    response = encode(list(users))
    return Response(response, mimetype="application/json")


@admin_blueprint.route("/admin/users/<user_id>/approval", methods=["PUT"])
def route_accept_users(user_id: str):
    """Updates user status to APPROVED."""

    uid = request.headers.get("uid", None)
    admin = User.objects.get_or_404(uid=uid)
    if not admin.is_admin():
        abort(401)

    user = User.objects.get_or_404(id=user_id)

    user.user_images = user.user_images_temp
    user.status = User.Status.APPROVED
    user.available = True
    user.save()

    message_service.push(dict(event="APPROVAL"), user.device_token)

    return Response("", mimetype="application/json")


@admin_blueprint.route("/admin/users/<user_id>/rejection", methods=["PUT"])
def route_reject_users(user_id: str):
    """Updates user status to REJECTED."""

    uid = request.headers.get("uid", None)
    admin = User.objects.get_or_404(uid=uid)
    if not admin.is_admin():
        abort(401)

    user = User.objects.get_or_404(id=user_id)

    user.status = User.Status.REJECTED
    user.save()

    message_service.push(dict(event="REJECTION"), user.device_token)

    return Response("", mimetype="application/json")


@admin_blueprint.route("/admin/users/<user_id>/block", methods=["GET"])
def route_block_users(user_id: str):
    """Updates user status to BLOCKED."""

    uid = request.headers.get("uid", None)
    admin = User.objects.get_or_404(uid=uid)
    if not admin.is_admin():
        abort(401)

    user = User.objects.get_or_404(id=user_id)

    user.status = User.Status.BLOCKED
    user.available = False
    user.save()

    message_service.push(dict(event="BLOCK"), user.device_token)

    return Response("", mimetype="application/json")

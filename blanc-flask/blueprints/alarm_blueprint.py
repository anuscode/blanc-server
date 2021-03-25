"""User blue print definitions."""

import json
import mongoengine

from flask import current_app as app
from flask import Blueprint
from flask import request
from flask import Response

from model.models import Alarm, User

alarms_blueprint = Blueprint('alarms_blueprint', __name__)


@alarms_blueprint.route('/alarms', methods=['GET'])
def list_alarms():
    uid = request.headers.get("uid", None)

    user = User.objects.get_or_404(uid=uid)

    alarm = Alarm.objects(owner=user).first()
    if not alarm:
        alarm = Alarm(owner=user, records=[]).save()

    records = alarm.records

    result = []
    for push in records:
        try:
            push_dict: dict = push.as_dict()
            result.append(push_dict)
        except mongoengine.DoesNotExist:
            nickname = user.nickname
            user_id = str(user.id)
            not_found_user_id = push.user_id
            message = "Not found a user({not_found_user_id}) in alarm of {nickname}({user_id}) ".format(
                not_found_user_id=not_found_user_id, nickname=nickname, user_id=user_id)
            app.logger.error(message)

    return Response(json.dumps(result), mimetype='application/json')


@alarms_blueprint.route('/alarms', methods=['PUT'])
def update_all_alarms_as_read():
    uid = request.headers.get("uid", None)

    user = User.objects.get_or_404(uid=uid)

    alarm = Alarm.objects.get_or_404(owner=user)
    records = alarm.records

    for push in records:
        push.is_read = True

    alarm.save()
    return Response("", mimetype='application/json')

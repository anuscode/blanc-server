"""Request blue print definitions."""

import pendulum

from flask import abort
from flask import Blueprint
from flask import Response
from flask import request
from model.models import Alarm, Request, User, Conversation
from shared import message_service
from shared.annotation import id_token_required, time_lapse
from shared.json_encoder import encode

requests_blueprint = Blueprint("requests_blueprint", __name__)


@requests_blueprint.route("/requests", methods=["GET"])
@time_lapse
def route_list_requests():
    """Endpoint for like request list."""
    uid = request.headers.get("uid", None)
    user = User.objects.get_or_404(uid=uid)
    result = user.list_requests_to_me()
    response = encode(result)
    return Response(response, mimetype="application/json")


@requests_blueprint.route("/requests/<request_id>", methods=["GET"])
@time_lapse
def route_get_request(request_id: str):
    """Endpoint for like request list."""
    _request = Request.get(id=request_id)
    response = encode(_request)
    return Response(response, mimetype="application/json")


@requests_blueprint.route("/requests/user_to/<user_id>/type/<int:r_type>", methods=["POST"])
@id_token_required
@time_lapse
def route_create_request(user_id: str, r_type: int):
    """Endpoint to request like."""

    uid = request.headers.get("uid", None)  # already verified uid.
    user = User.objects.get_or_404(uid=uid)

    user_from = user  # me
    user_to = User.objects.get_or_404(id=user_id)  # target

    # checks if there is a one I have already sent
    request_i_sent = Request.objects(user_to=user_to, user_from=user_from).first()

    if request_i_sent:
        raise ValueError("a duplicate request already exists.")

    # checks if there is a one I have already received.
    request_i_received = Request.objects(user_to=user_from, user_from=user_to).first()

    if request_i_received:
        if request_i_received.response is None:
            return route_update_response_of_request(request_i_received.id, 1)
        else:
            raise ValueError("a duplicate request already exists.")

    is_available_for_free = user_from.is_available_for_free_pass_token()
    amount_remaining = user_from.get_current_amount_of_point()

    if not is_available_for_free and amount_remaining <= 0:
        raise Exception("Unavailable for the request.")

    _request = Request(
        user_from=user_from,
        user_to=user_to,
        request_type_id=r_type,
        requested_at=pendulum.now().int_timestamp,
        response=None,
        responded_at=None
    )
    _request.save()
    _request.reload()

    # if the target exists in recommendation, remove them.
    user_from.remove_user_from_recommendation(user_to)

    if is_available_for_free:
        user_from.consume_free_pass_token()
    else:
        user_from.consume(5)

    alarm = Alarm.create_alarm(
        user_from=user_from,
        user_to=user_to,
        push_for="REQUEST",
        request=_request,
        message="{nickname} 님이 당신에게 친구 신청을 보냈습니다.".format(nickname=user_from.nickname))
    alarm_record = alarm.records[-1]
    data = alarm_record.as_dict()
    message_service.push(data, user_to.device_token)

    response = encode(Request.get(id=_request.id))
    return Response(response, mimetype="application/json")


@requests_blueprint.route("/requests/<request_id>/response/<int:result>", methods=["PUT"])
@time_lapse
def route_update_response_of_request(request_id: str, result: int):
    """Updates a received like request. ACCEPT: 1 DECLINE: 0 """

    uid = request.headers.get("uid", None)
    me = User.objects.get_or_404(uid=uid)

    _request = Request.objects.get_or_404(id=request_id)

    if _request.user_to.id != me.id:
        abort(400)

    # update request table.
    _request.response = result
    _request.responded_at = pendulum.now().int_timestamp
    _request.save()
    _request.reload()

    if int(result) == 1:
        _request.user_to.remove_user_from_recommendation(_request.user_from)

        # create chat room
        conversation = Conversation(
            title=None,
            participants=[_request.user_from, _request.user_to],
            references=[_request.user_from, _request.user_to],
            created_at=pendulum.now().int_timestamp)
        conversation.save()
        conversation.reload()

        # alarm by push below
        user_alarm_from = _request.user_to
        user_alarm_to = _request.user_from

        alarm = Alarm.create_alarm(
            user_from=user_alarm_from,
            user_to=user_alarm_to,
            push_for="MATCHED",
            request=_request,
            conversation=conversation,
            message="{nickname} 님과 연결 되었습니다.".format(nickname=_request.user_to.nickname))
        alarm_record = alarm.records[-1]
        data = alarm_record.as_dict()
        message_service.push(data, user_alarm_to.device_token)

    response = encode(Request.get(id=_request.id))
    return Response(response, mimetype="application/json")

import pendulum

from flask import abort
from flask import Blueprint
from flask import Response
from flask import request
from model.models import AlarmRecord, User, Conversation, EmbeddedMessage
from shared import message_service
from shared.annotation import id_token_required
from shared.annotation import time_lapse
from shared.json_encoder import encode

conversations_blueprint = Blueprint('conversations_blueprint', __name__)

BEGIN_CONVERSATION_MESSAGE = "대화가 시작 되었습니다. 즐거운 대화 나누세요."


@conversations_blueprint.route('/conversations', methods=['POST'])
def route_create_conversation():
    params = request.get_json()
    title = params.get("title", None)
    conversation = Conversation(title=title, created_at=pendulum.now().int_timestamp).save()
    conversation.reload()
    return Response(encode(conversation.to_mongo()), mimetype="application/json")


@conversations_blueprint.route('/conversations/<conversation_id>', methods=['DELETE'])
def route_delete_conversation(conversation_id):
    conversation = Conversation.objects(id=conversation_id).first()
    conversation.delete()
    return Response("", mimetype="application/json")


@conversations_blueprint.route('/conversations', methods=['GET'])
@time_lapse
def route_list_user_conversations():
    uid = request.headers.get("uid", None)
    user = User.objects.get_or_404(uid=uid)
    conversations = Conversation.objects(participants=user).as_pymongo()

    user_ids = get_conversation_reference_ids(conversations)
    users_dict = User.get_users_dict(user_ids)

    converted = []
    for conversation in conversations:
        participants = [users_dict.get(str(user_id), None) for user_id in conversation.get("participants")]
        references = [users_dict.get(str(user_id), None) for user_id in conversation.get("references")]
        if None not in participants and None not in references:
            conversation["participants"] = participants
            conversation["references"] = references
            converted.append(conversation)

    response = encode(converted)
    return Response(response, mimetype="application/json")


@conversations_blueprint.route('/conversations/<conversation_id>', methods=['GET'])
def route_get_conversation(conversation_id):
    uid = request.headers.get("uid", None)
    user = User.objects.get_or_404(uid=uid)
    conversation = Conversation.objects.get_or_404(id=conversation_id, participants=user).to_mongo()

    user_ids = get_conversation_reference_ids([conversation])
    user_index = User.get_users_dict(user_ids)
    conversation["participants"] = [user_index.get(str(user_id), None) for user_id in conversation["participants"]]
    conversation["references"] = [user_index.get(str(user_id), None) for user_id in conversation["references"]]

    response = encode(conversation)
    return Response(response, mimetype="application/json")


@conversations_blueprint.route('/conversations/<conversation_id>/messages/<message>', methods=['POST'])
def route_create_message(conversation_id: str, message: str):
    uid = request.headers.get("uid", None)

    user = User.objects.get_or_404(uid=uid)
    conversation = Conversation.objects.get_or_404(id=conversation_id, participants=user)
    embedded_message = EmbeddedMessage(
        conversation_id=conversation_id,
        category="MESSAGE",
        user_id=str(user.id),
        message=message,
        created_at=pendulum.now().int_timestamp
    )
    conversation.messages.append(embedded_message)
    conversation.save()

    user_from = user
    user_image = next(iter(user.user_images or []), None)
    image_url = user_image.url if user_image else ""

    user_to_list = [p for p in conversation.participants if p.id != user.id]

    for user_to in user_to_list:
        message_service.push(dict(
            event="CONVERSATION",
            nickname=user_from.nickname,
            user_id=str(user_from.id),
            image_url=image_url,
            created_at=str(pendulum.now().int_timestamp),
            conversation_id=str(conversation.id),
            message_id=str(embedded_message.id),
            message=str(embedded_message.message),
            category="MESSAGE",
        ), user_to.device_token, priority="high")

    response = encode(embedded_message.to_mongo())
    return Response(response, mimetype="application/json")


@conversations_blueprint.route('/conversations/<conversation_id>/available/<available>', methods=['PUT'])
@id_token_required
def route_update_conversation_available(conversation_id: str, available: bool):
    uid = request.headers.get("uid", None)

    conversation = Conversation.objects.get_or_404(id=conversation_id)
    user_to_open_room: User = next((member for member in conversation.participants if member.uid == uid), None)

    if not user_to_open_room:
        raise Exception("The user who has tried to open conversation, is not belong to the room.")

    if user_to_open_room.is_available_for_free_open_token():
        user_to_open_room.consume_free_open_token()
    else:
        # it will raise exception when remaining point is not enough
        user_to_open_room.consume(5)

    conversation.available = bool(available)
    conversation.available_at = pendulum.now().int_timestamp
    conversation.save()

    embedded_message = EmbeddedMessage(
        conversation_id=conversation_id,
        message=BEGIN_CONVERSATION_MESSAGE,
        category="SYSTEM",
        created_at=pendulum.now().int_timestamp
    )

    conversation.messages.append(embedded_message)
    conversation.save()

    # push opened message
    for user_to in conversation.participants:
        if user_to.uid == user_to_open_room.uid:
            continue
        push = AlarmRecord(
            event="OPENED",
            user_id=user_to_open_room.id,
            created_at=pendulum.now().int_timestamp,
            conversation_id=conversation.id,
            message="{nickname} 님이 대화방을 열었습니다.".format(nickname=user_to_open_room.nickname)
        )
        data = push.as_dict()
        message_service.push(data, user_to.device_token, priority="high")

    # push system message as conversation message
    for participant in conversation.participants:
        message_service.push(dict(
            event="CONVERSATION",
            created_at=str(pendulum.now().int_timestamp),
            conversation_id=str(conversation.id),
            message_id=str(embedded_message.id),
            category="SYSTEM",
            message=BEGIN_CONVERSATION_MESSAGE
        ), participant.device_token, priority="high")

    return Response("", mimetype="application/json")


@conversations_blueprint.route('/conversations/<conversation_id>/user_id/<user_id>', methods=['DELETE'])
def route_leave_conversation(conversation_id: str, user_id: str):
    uid = request.headers.get("uid", None)
    user = User.objects.get_or_404(uid=uid)

    if str(user.id) != user_id:
        abort(401)

    conversation = Conversation.objects.get_or_404(id=conversation_id)
    leave_message = "{nickname} 님이 대화를 종료 하셨습니다.".format(nickname=user.nickname)

    embedded_message = EmbeddedMessage(
        conversation_id=conversation_id,
        message=leave_message,
        category="SYSTEM",
        created_at=pendulum.now().int_timestamp
    )

    conversation.update(pull__participants=user, push__messages=embedded_message)
    conversation.reload()

    if len(conversation.participants) == 0:
        conversation.delete()

    for participant in conversation.participants:
        message_service.push(dict(
            event="CONVERSATION",
            created_at=str(pendulum.now().int_timestamp),
            conversation_id=str(conversation.id),
            message_id=str(embedded_message.id),
            category="SYSTEM",
            message=leave_message
        ), participant.device_token, priority="high")

    return Response("", mimetype="application/json")


def get_conversation_reference_ids(conversations):
    user_ids = set()
    for conversation in conversations:
        references = conversation.get("references")
        for user_id in references:
            user_ids.add(user_id)
    return user_ids

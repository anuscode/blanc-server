"""User blue print definitions."""

import json
import logging
import pendulum
import urllib3
import uuid
import random
import re
import requests

from flask import abort
from flask import Blueprint
from flask import current_app as app
from flask import request
from flask import Response
from firebase_admin import messaging
from firebase_admin import storage
from firebase_admin import auth
from firebase_admin._auth_utils import UserNotFoundError
from model.models import Alarm, User, UserImage, Request, StarRating, Setting, Post, Contact
from model.models import Status
from shared import regex
from shared import message_service
from shared.annotation import id_token_required
from shared.annotation import time_lapse
from shared.hash_service import verify_sms_token
from shared.json_encoder import encode

users_blueprint = Blueprint("users_blueprint", __name__)

IMAGE_MIMETYPE_REGEX = r"image/.*"

USER_IMAGE_FOLDER = "user_images"

KAKAO_AUTH_URL = "https://kapi.kakao.com/v2/user/me"

http = urllib3.PoolManager()

UPDATE_ABLE_FIELDS = {
    'available', 'birthed_at', 'blood_id', 'body_id', 'charm_ids', 'drink_id', 'education', 'height', 'ideal_type_ids',
    'interest_ids', 'introduction', 'last_login_at', 'nickname', 'occupation', 'religion_id', 'sex', 'smoking_id',
    'star_rating_avg', 'status', 'user_images_temp'
}

STRIP_REQUIRED_FIELDS = ["nickname", "occupation", "education"]

MAXIMUM_RECOMMENDATION_SHOW_COUNT = 12


def get_coordinates_by_ip(req):
    ip_stack_config = app.config.get("IP_STACK")
    access_key = ip_stack_config.get("ACCESS_KEY")

    try:
        ip_address = req.remote_addr
        url = "http://api.ipstack.com/{ip_address}?access_key={access_key}".format(
            ip_address=ip_address, access_key=access_key)
        response = http.request("GET", url)
        value = json.loads(response.data.decode('utf8'))
        longitude, latitude = value.get("longitude"), value.get("latitude")
        return float(longitude), float(latitude)

    except Exception:
        latitude = random.randrange(33125798, 38550609) / 1000000
        longitude = random.randrange(126018599, 129576299) / 1000000
        return longitude, latitude


@users_blueprint.route("/users", methods=["POST"])
@id_token_required
def route_create_user():
    uid = request.headers.get("uid", None)
    phone = request.form.get("phone", None)
    sms_code = request.form.get("sms_code", None)
    sms_token = request.form.get("sms_token", None)

    proof = verify_sms_token(sms_token, phone, sms_code)
    if not proof:
        abort(401)

    if not phone:
        raise ValueError("phone is required value to create an user.")

    user = User.objects(uid=uid).first()

    if not user:
        user = User(uid=uid, phone=phone, status=Status.OPENED, available=False,
                    last_login_at=pendulum.now().int_timestamp)
        user.save()
        alarm = Alarm(owner=user, records=[])
        alarm.save()

    response = encode(user.to_mongo())
    return Response(response, mimetype="application/json")


@users_blueprint.route("/users/kakao", methods=["POST"])
def route_authentication_with_kakao():
    kakao_token = request.headers.get("id_token", None)

    authorization = "Bearer {kakao_token}".format(kakao_token=kakao_token)
    kakao_auth_response = requests.get(KAKAO_AUTH_URL, headers=dict(Authorization=authorization))
    json_response: dict = kakao_auth_response.json()
    kakao_id = json_response.get("id", None)

    if not kakao_id:
        raise abort(401)

    firebase_kakao_id = "KAKAO:{kakao_id}".format(kakao_id=kakao_id)

    try:
        firebase_user = auth.get_user(firebase_kakao_id)
    except UserNotFoundError:
        firebase_user = auth.create_user(uid=firebase_kakao_id)

    uid = firebase_user.uid

    custom_token_bytes = auth.create_custom_token(uid)
    custom_token = custom_token_bytes.decode("utf-8")

    response = json.dumps(dict(custom_token=custom_token))
    return Response(response, mimetype="application/json")


@users_blueprint.route("/users/<user_id>/location", methods=["PUT"])
def route_update_user_location(user_id: str):
    user = User.objects.get_or_404(id=user_id)
    user.identify(request)

    longitude = request.args.get("longitude", None)
    latitude = request.args.get("latitude", None)

    area = request.args.get("area", None)

    if not longitude or not latitude:
        longitude, latitude = get_coordinates_by_ip(request)

    if not longitude or not latitude:
        return Response(json.dumps(dict(coordinates=[], type="Point")), mimetype="application/json")

    coordinates = [float(longitude), float(latitude)]
    user.update(**dict(location=coordinates, area=area))

    response = json.dumps(dict(coordinates=coordinates, type="Point"))
    return Response(response, mimetype="application/json")


@users_blueprint.route("/users/<user_id>/profile", methods=["PUT"])
@id_token_required
def route_update_user_profile(user_id: str):
    user = User.objects.get_or_404(id=user_id)
    user.identify(request)

    params = request.get_json()

    for key in list(params.keys()):
        if key not in UPDATE_ABLE_FIELDS:
            params.pop(key, None)

    for key in STRIP_REQUIRED_FIELDS:
        value = params.get(key, None)
        if not value:
            raise ValueError("{0} is required value.".format(value))
        value = value.strip()
        params[key] = value
    user.update(**params)

    return Response("", mimetype="application/json")


@users_blueprint.route("/users/<user_id>/rated_me_high", methods=["GET"])
def route_list_users_rated_me_high(user_id: str):
    user = User.objects.get_or_404(id=user_id)
    user.identify(request)

    users = user.list_users_rated_me_high()
    response = encode(list(users))
    return Response(response, mimetype="application/json")


@users_blueprint.route("/users/<user_id>/i_rated_high", methods=["GET"])
def route_list_users_i_rated_high(user_id: str):
    user = User.objects.get_or_404(id=user_id)
    user.identify(request)

    users = user.list_users_i_rated_high()
    response = encode(list(users))
    return Response(response, mimetype="application/json")


@users_blueprint.route("/users/<user_id>", methods=["GET"])
def route_get_user(user_id):
    """Endpoint for getting user."""
    user = User.get(id=user_id)
    response = encode(user.to_mongo())
    return Response(response, mimetype="application/json")


@users_blueprint.route("/users/session", methods=["GET"])
@time_lapse
@id_token_required
def route_get_session():
    """Endpoint for getting user session."""
    uid = request.headers.get("uid", None)
    user = User.objects.get_or_404(uid=uid)
    user_id = user.id

    point = user.get_current_amount_of_point()
    user = user.to_mongo()

    star_rating = StarRating.objects(user_from=user_id).as_pymongo()
    received = Request.objects(user_to=user_id).as_pymongo()
    sent = Request.objects(user_from=user_id).as_pymongo()

    # 이미 성사 된 상대
    matched_request_sent = [str(req["user_to"]) for req in sent if req.get("response") == 1]
    matched_request_received = [str(req["user_from"]) for req in received if req.get("response") == 1]
    user_ids_matched = matched_request_received + matched_request_sent
    # 성사 되지 않은 상대
    unmatched_request_sent = [str(req["user_to"]) for req in sent if req.get("response") == 0]
    unmatched_request_received = [str(req["user_from"]) for req in received if req.get("response") == 0]
    user_ids_unmatched = unmatched_request_sent + unmatched_request_received
    # 이미 좋아요를 보냄
    user_ids_i_sent_request = [str(req["user_to"]) for req in sent if req.get("response") != 1]
    # 내게 좋아요를 보냄 and 미수락
    user_ids_sent_me_request = [str(req["user_from"]) for req in received if req.get("response") != 1]
    # 내가 평가 한 사람들
    star_ratings_i_rated = [dict(user_id=str(x["user_to"]), score=x["score"]) for x in star_rating]

    user["user_ids_matched"] = user_ids_matched
    user["user_ids_unmatched"] = user_ids_unmatched
    user["user_ids_i_sent_request"] = user_ids_i_sent_request
    user["user_ids_sent_me_request"] = user_ids_sent_me_request
    user["star_ratings_i_rated"] = star_ratings_i_rated
    user["point"] = point

    response = encode(user)
    return Response(response, mimetype="application/json")


@users_blueprint.route("/users/device_token/<device_token>", methods=["PUT"])
def route_update_registration_token(device_token: str):
    """Endpoint for updating user registration token."""
    uid = request.headers.get("uid", None)
    user = User.objects.get_or_404(uid=uid)

    existing_device_token = user.device_token
    new_device_token = device_token

    is_update_required = existing_device_token != new_device_token

    if is_update_required:
        user.device_token = new_device_token
        user.save()

    if is_update_required and existing_device_token is not None:
        try:
            message = messaging.Message(
                data=dict(push_for="LOG_OUT"),
                token=existing_device_token,
                apns=messaging.APNSConfig(),
                android=messaging.AndroidConfig(priority="high"),
                notification=messaging.Notification())
            messaging.send(message)
        except Exception as e:
            logging.exception(e)

    response = encode(user.to_mongo())
    return Response(response, mimetype="application/json")


@users_blueprint.route("/users/<user_id>/user_images/<int:index>", methods=["POST", "PUT"])
def route_upload_user_image(user_id: str, index: int):
    """Endpoint for uploading profile images."""
    user = User.objects.get_or_404(id=user_id)
    user.identify(request)

    image_file = request.files["user_image"]

    if not re.match(IMAGE_MIMETYPE_REGEX, image_file.mimetype):
        raise ValueError("The file is not an image type.")

    bucket = storage.bucket()
    file_name_to_save = "{0}_{1}_{2}".format(user.uid, index, uuid.uuid1())
    blob = bucket.blob("{0}/{1}/{2}".format(USER_IMAGE_FOLDER, user.uid, file_name_to_save))
    blob.upload_from_file(image_file)

    user_images_temp = user.user_images_temp
    current_image_at_index = next((x for x in user_images_temp if x.index == index), None)

    if not current_image_at_index:  # create new one
        user.user_images_temp.append(UserImage(index=index, url=blob.public_url))
    else:  # update existing one
        current_image_at_index.url = blob.public_url
        user.user_images_temp = sorted(user_images_temp, key=lambda x: x.index)
    user.status = Status.OPENED
    user.save()

    updated_image = next((x for x in user_images_temp if x.index == index), None)

    response = encode(updated_image.to_mongo())
    return Response(response, mimetype="application/json")


@users_blueprint.route("/users/<user_id>/status/approval", methods=["PUT"])
def route_update_user_status_to_approved(user_id: str):
    """Endpoint for updating user status approved."""
    user = User.objects.get_or_404(id=user_id)

    user.user_images = user.user_images_temp
    user.status = Status.APPROVED
    user.available = True
    user.save()

    data = dict(push_for="APPROVAL")
    message_service.push(data, user.device_token)

    return Response("", mimetype="application/json")


@users_blueprint.route("/users/<user_id>/status/rejection", methods=["PUT"])
def route_update_user_status_to_rejected(user_id: str):
    """Endpoint for updating user status rejected."""
    user = User.objects.get_or_404(id=user_id)

    user.user_images = user.user_images_temp
    user.status = Status.REJECTED
    user.save()

    response = encode(user.to_mongo())
    return Response(response, mimetype="application/json")


@users_blueprint.route("/users/<user_id>/status/pending", methods=["PUT"])
def route_update_user_status_pending(user_id: str):
    user = User.objects.get_or_404(id=user_id)
    user.identify(request)

    user.status = Status.PENDING
    user.save()

    response = encode(user.to_mongo())
    return Response(response, mimetype="application/json")


@users_blueprint.route("/users/<user_id>/user_images/<int:index>", methods=["DELETE"])
def route_delete_user_image(user_id: str, index: int):
    user = User.objects.get_or_404(id=user_id)
    user.identify(request)

    if user.available and user.status == Status.APPROVED:
        is_same = compare_user_images_and_temps(
            user.user_images, user.user_images_temp
        )
        if is_same and len(user.user_images_temp) > 2:
            images = user.user_images
            images_to_update = [image for image in images if image.index != index]
            user.update(user_images=images_to_update)
            user.update(user_images_temp=images_to_update)
            user.reload()
            response = encode(user.to_mongo())
            return Response(response, mimetype="application/json")

    user_image_to_remove = next(
        (user_image_temp for user_image_temp in user.user_images_temp
         if user_image_temp.index == index), None)

    user.update(pull__user_images_temp=user_image_to_remove)
    user.status = Status.OPENED
    user.save()
    user.reload()

    response = encode(user.to_mongo())
    return Response(response, mimetype="application/json")


@users_blueprint.route("/users/<user_id>/posts", methods=["GET"])
def route_list_user_posts(user_id):
    user = User.get(id=user_id)
    result = user.list_posts()
    response = encode(list(result))
    return Response(response, mimetype="application/json")


@users_blueprint.route("/users/<user_id>/recommendation", methods=["GET"])
@time_lapse
def route_list_users_recommendation(user_id: str):
    """Endpoint for getting recommended users."""
    user = User.objects.get_or_404(id=user_id)
    user.identify(request)

    recommendation = user.get_recommendation()

    last_recommended_at = pendulum.from_timestamp(
        recommendation.last_recommended_at, tz="Asia/Seoul")
    is_today_recommended = last_recommended_at.date() == pendulum.today().date()

    if is_today_recommended and len(recommendation.user_ids) >= 2:
        user_ids = recommendation.user_ids
    else:
        user_ids = user.list_recommended_user_ids()
        user_ids.extend(recommendation.user_ids)
        recommendation.user_ids = user_ids
        recommendation.last_recommended_at = pendulum.now().int_timestamp
        recommendation.save()

    users = User.list(id__in=user_ids[:MAXIMUM_RECOMMENDATION_SHOW_COUNT]).as_pymongo()
    users = sort_order_by_ids(user_ids, users)
    response = encode(list(users))
    return Response(response, mimetype="application/json")


@users_blueprint.route("/users/<user_id>/real_time", methods=["GET"])
@time_lapse
def route_list_users_real_time(user_id: str):
    """Endpoint for getting users."""
    user = User.objects.get_or_404(id=user_id)
    user.identify(request)

    user_ids = user.list_realtime_user_ids()
    users = User.list(id__in=user_ids).as_pymongo()
    response = encode(list(users))
    return Response(response, mimetype="application/json")


@users_blueprint.route("/users/<user_id>/distance/<int:distance>", methods=["GET"])
@time_lapse
def route_list_users_close(user_id: str, distance: int):
    """Endpoint for getting users."""
    user = User.objects.get_or_404(id=user_id)
    user.identify(request)

    distance = distance or 5

    if not user.location or not user.location["coordinates"]:
        return Response(json.dumps([]), mimetype="application/json")

    close_user_ids = user.list_user_ids_within_distance(distance=distance)
    users = User.list(id__in=close_user_ids).as_pymongo()
    response = encode(list(users))
    return Response(response, mimetype="application/json")


@users_blueprint.route("/users/<user_id>/score/<int:score>", methods=["PUT"])
def route_update_star_rating(user_id: str, score: int):
    """Endpoint for getting users."""
    uid = request.headers.get("uid", None)

    user_from = User.get(uid=uid)
    user_to = User.get(id=user_id)

    is_already_rated = StarRating.objects(user_from=user_from, user_to=user_to).first()

    if not is_already_rated:
        StarRating(
            user_from=user_from,
            user_to=user_to,
            rated_at=pendulum.now().int_timestamp,
            score=score
        ).save()

        if score > 3:
            alarm = Alarm.create_alarm(
                user_from=user_from,
                user_to=user_to,
                push_for="STAR_RATING",
                message="{nickname} 님이 당신을 높게 평가 하였습니다.".format(nickname=user_from.nickname))
            alarm_record = alarm.records[-1]
            data = alarm_record.as_dict()
            message_service.push(data, user_to.device_token)

        star_ratings = StarRating.objects(user_to=user_to).all()

        star_rating_sum = 0
        for rating in star_ratings:
            star_rating_sum += rating.score
        star_rating_avg = star_rating_sum / len(star_ratings)

        user_to.update(star_rating_avg=star_rating_avg)

    return Response("", mimetype="application/json")


@users_blueprint.route("/users/<user_id>/score", methods=["GET"])
def route_list_users_rated_me(user_id: str):
    """Endpoint for getting users rated me."""
    user = User.objects.get_or_404(id=user_id)
    user.identify(request)

    users = user.list_users_rated_me()
    response = encode(list(users))
    return Response(response, mimetype="application/json")


@users_blueprint.route("/users/<user_id>/last_login_at", methods=["PUT"])
def route_update_last_login_at(user_id: str):
    user = User.objects.get_or_404(id=user_id)
    user.identify(request)

    user.update(last_login_at=pendulum.now().int_timestamp)
    return Response("", mimetype="application/json")


@users_blueprint.route("/users/uid/<uid>", methods=["GET"])
def route_user_exists(uid: str):
    user = User.objects(uid=uid).first()
    result = True if user else False
    return Response(
        json.dumps(dict(exists=result)), mimetype="application/json")


@users_blueprint.route("/users/<user_id>/contacts", methods=["PUT"])
@id_token_required
def route_user_block(user_id: str):
    user = User.objects.get_or_404(id=user_id)
    user.identify(request)

    phones = request.json
    if not phones and phones is not list:
        raise ValueError("phones must be list type.")

    phones = [phone for phone in phones if re.match(regex.GLOBAL_PHONE_REGEX, phone)]
    user.set_contact(phones)

    return Response("", mimetype="application/json")


@users_blueprint.route("/users/phone/<phone>/sms_code/<sms_code>/sms_token/<sms_token>", methods=["GET"])
def route_find_account_by_phone(phone: str, sms_code: str, sms_token: str):
    proof = verify_sms_token(sms_token, phone, sms_code)
    if not proof:
        abort(401)

    user = User.objects(phone=phone).first()
    if user:
        firebase_user = auth.get_user(user.uid)
        if firebase_user.email:
            return Response(json.dumps(dict(email=firebase_user.email, is_exists=True)), mimetype="application/json")
        if "KAKAO" in firebase_user.uid:
            return Response(json.dumps(dict(email="카카오 계정", is_exists=True)), mimetype="application/json")
        else:
            abort(404)
    else:
        return Response(json.dumps(dict(email="", is_exists=False)), mimetype="application/json")


@users_blueprint.route("/users/<user_id>/push/lookup", methods=["POST"])
def route_push_look_up(user_id: str):
    """uid is for a current user and user_id is for an user to watch."""
    uid = request.headers.get("uid", None)
    user_from = User.get(uid=uid)
    user_to = User.get(id=user_id)

    message_service.push(dict(
        push_for="LOOK_UP",
        user_id=str(user_from.id),
        nickname=user_from.nickname,
        image_url=user_from.get_first_image(),
        message="{nickname} 님이 당신을 조회 중입니다.".format(nickname=user_from.nickname),
        created_at=str(pendulum.now().int_timestamp)
    ), user_to.device_token)

    return Response("", mimetype="application/json")


@users_blueprint.route("/users/<user_id>/push/poke", methods=["POST"])
def route_push_poke(user_id):
    uid = request.headers.get("uid", None)
    user_from = User.get(uid=uid)
    user_to = User.get(id=user_id)

    alarm = Alarm.create_alarm(
        push_for="POKE",
        user_from=user_from,
        user_to=user_to,
        message="{nickname} 님이 당신을 찔렀습니다.".format(nickname=user_from.nickname)
    )
    alarm_record = alarm.records[-1]
    data: dict = alarm_record.as_dict()
    message_service.push(data, user_to.device_token)

    return Response("", mimetype="application/json")


@users_blueprint.route("/users/<user_id>/setting/push", methods=["GET"])
def route_get_push_setting(user_id: str):
    user = User.objects.get_or_404(id=user_id)
    user.identify(request)

    setting = Setting.objects(owner=user).first()
    if not setting:
        setting = Setting(owner=user)
        setting.save()

    push_setting = setting.push
    push_setting = push_setting.to_mongo()
    response = encode(push_setting)
    return Response(response, mimetype="application/json")


@users_blueprint.route("/users/<user_id>/setting/push", methods=["PUT"])
def route_update_push_setting(user_id: str):
    user = User.objects.get_or_404(id=user_id)
    user.identify(request)

    params: dict = request.get_json()

    setting: Setting = Setting.objects(owner=user).first() or Setting(owner=user)
    setting.push.set(params)
    setting.save()

    return Response("", mimetype="application/json")


@users_blueprint.route("/users/<user_id>/cancel", methods=["DELETE"])
@id_token_required
def route_cancel_register_user(user_id: str):
    user = User.objects.get_or_404(id=user_id)
    user.identify(request)

    if user.available:
        abort(500)
    if user.status != Status.PENDING:
        abort(500)
    if user.user_images:
        abort(500)

    Alarm.objects(owner=user).delete()
    user.delete()

    return Response("", mimetype="application/json")


@users_blueprint.route("/users/<user_id>/unregister", methods=["PUT"])
@id_token_required
def route_unregister_user(user_id: str):
    user = User.objects.get_or_404(id=user_id)
    user.identify(request)
    user.unregister()
    return Response("", mimetype="application/json")


def compare_user_images_and_temps(images, images_temp):
    images_set = set([image.url for image in images])
    images_temp_set = set([image.url for image in images_temp])
    image_set_merged = set()
    image_set_merged.update(images_set)
    image_set_merged.update(images_temp_set)
    diff_len_1 = len(image_set_merged - images_set)
    diff_len_2 = len(image_set_merged - images_temp_set)

    if diff_len_1 > 0 or diff_len_2 > 0:
        return False

    result = True
    for index in range(0, len(images)):
        image = images[index]
        image_temp = images_temp[index]
        if image.url != image_temp.url:
            result = False
            break

    return result


def sort_order_by_ids(ids, objects):
    dict_map = {str(o["_id"]): o for o in objects}
    result = []
    for _id in ids:
        obj = dict_map.get(str(_id), None)
        if obj is not None:
            result.append(obj)
    return result

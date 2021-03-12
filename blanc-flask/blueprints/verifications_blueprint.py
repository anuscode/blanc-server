import json
import pendulum
import re

from flask import Blueprint
from flask import request
from flask import Response
from shared import hash_service
from shared import regex
from shared import sms_service

verifications_blueprint = Blueprint('verifications_blueprint', __name__)

GLOBAL_PHONE_REGEX = regex.GLOBAL_PHONE_REGEX

PHONE_PREFIX_REGEX = regex.PHONE_PREFIX_REGEX


class STATUS(object):
    SUCCEED_ISSUE = "SUCCEED_ISSUE"
    FAILED_ISSUE = "FAILED_ISSUE"
    INVALID_PHONE_NUMBER = "INVALID_PHONE_NUMBER"
    DUPLICATE_PHONE_NUMBER = "DUPLICATE_PHONE_NUMBER"
    INVALID_SMS_CODE = "INVALID_SMS_CODE"
    EXPIRED_SMS_CODE = "EXPIRED_SMS_CODE"
    VERIFIED_SMS_CODE = "VERIFIED_SMS_CODE"


@verifications_blueprint.route('/verifications/sms', methods=['POST'])
def route_issue_sms_code():
    phone = request.form.get('phone', None)

    phone = normalize_phone_number(phone)
    phone, match = validate_phone_regex(phone)
    if not match:
        response = json.dumps(dict(status=STATUS.INVALID_PHONE_NUMBER))
        return Response(response, mimetype="application/json")

    issue_result = issue(phone)
    response = json.dumps(issue_result)
    return Response(response, mimetype="application/json")


@verifications_blueprint.route('/verifications/sms', methods=['PUT'])
def route_verify_sms_code():
    phone = request.form.get('phone', None)
    sms_code = request.form.get('sms_code', None)
    expired_at = request.form.get('expired_at', None)

    sms_code_to_verify = hash_service.get_sms_code(phone, expired_at)

    if sms_code != sms_code_to_verify:
        response = json.dumps(dict(status=STATUS.INVALID_SMS_CODE))
        return Response(response, mimetype="application/json")

    if int(expired_at) < pendulum.now().int_timestamp:
        response = json.dumps(dict(status=STATUS.EXPIRED_SMS_CODE))
        return Response(response, mimetype="application/json")

    sms_token = hash_service.generate_sms_token(phone, sms_code)
    response = json.dumps(dict(
        phone=phone,
        status=STATUS.VERIFIED_SMS_CODE,
        sms_code=sms_code,
        expired_at=int(expired_at),
        sms_token=sms_token)
    )
    return Response(response, mimetype="application/json")


def normalize_phone_number(phone):
    phone = phone.strip()
    phone = re.sub(PHONE_PREFIX_REGEX, "+8210", phone)
    return phone


def validate_phone_regex(phone):
    match = re.match(GLOBAL_PHONE_REGEX, phone)
    return phone, match


def issue(phone):
    expired_at = pendulum.now().int_timestamp + (60 * 10)
    sms_code = hash_service.get_sms_code(phone, expired_at)
    message = "[인증번호:{sms_code}] 핑미 회원가입 인증번호 입니다.".format(sms_code=sms_code)
    response = sms_service.send(phone=phone, msg=message)
    success = response.get("success_cnt")
    error = response.get("error_cnt")
    status = STATUS.SUCCEED_ISSUE if success == 1 and error == 0 else STATUS.FAILED_ISSUE
    return dict(
        status=status,
        sms_code=sms_code,
        expired_at=expired_at,
        phone=phone
    )

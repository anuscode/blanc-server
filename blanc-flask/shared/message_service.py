import logging
from firebase_admin import messaging
from model.models import Alarm, Setting


def push(data: dict = None, token: str = None, priority="normal"):
    if not token:
        return
    try:
        apns = build_apns()
        message = messaging.Message(
            data=data,
            token=token,
            apns=apns,
            android=messaging.AndroidConfig(priority=priority)
        )
        progress(message=message, data=data)
        messaging.send(message)
    except Exception as e:
        logging.exception(e)


def progress(message: messaging.Message, data: dict = None):
    if is_event(of=Alarm.Event.LOG_OUT, data=data):
        log_out(message=message, data=data)
        return

    if is_event(of=Alarm.Event.APPROVED, data=data):
        approved(message=message, data=data)
        return

    if is_event(of=Alarm.Event.REJECTED, data=data):
        rejected(message=message, data=data)
        return

    if is_event(of=Alarm.Event.BLOCKED, data=data):
        blocked(message=message, data=data)
        return

    if is_event(of=Alarm.Event.CONVERSATION, data=data):
        conversation(message=message, data=data)
        return

    if is_event(of=Alarm.Event.POKE, data=data):
        poke(message=message, data=data)
        return

    if is_event(of=Alarm.Event.REQUEST, data=data):
        request(message=message, data=data)
        return

    if is_event(of=Alarm.Event.COMMENT, data=data):
        comment(message=message, data=data)
        return

    if is_event(of=Alarm.Event.POST_FAVORITE, data=data):
        favorite(message=message, data=data)
        return

    if is_event(of=Alarm.Event.MATCHED, data=data):
        matched(message=message, data=data)
        return

    if is_event(of=Alarm.Event.COMMENT_THUMB_UP, data=data):
        thumb_up(message=message, data=data)
        return

    if is_event(of=Alarm.Event.CONVERSATION_OPEN, data=data):
        conversation_open(message=message, data=data)
        return

    if is_event(of=Alarm.Event.CONVERSATION_LEAVE, data=data):
        conversation_leave(message=message, data=data)
        return

    if is_event(of=Alarm.Event.LOOK_UP, data=data):
        look_up(message=message, data=data)
        return

    if is_event(of=Alarm.Event.STAR_RATING, data=data):
        star_rating(message=message, data=data)
        return


def build_apns():
    aps = messaging.Aps(content_available=True, mutable_content=True)
    payload = messaging.APNSPayload(aps=aps)
    apns = messaging.APNSConfig(headers={"apns-priority": "5"}, payload=payload)
    return apns


def is_event(of=None, data: dict = None) -> bool:
    event = of
    return data.get("event", None) == event


def log_out(message: messaging.Message, data: dict = None):
    if not is_event(of=Alarm.Event.LOG_OUT, data=data):
        return
    set_alert(into=message, subtitle="블랑", body="다른 디바이스에서 로그인이 감지 되었습니다.")


def approved(message: messaging.Message, data: dict = None):
    if not is_event(of=Alarm.Event.APPROVED, data=data):
        return
    set_alert(into=message, subtitle="블랑", body="가입 승인이 완료 되었습니다.")


def rejected(message: messaging.Message, data: dict = None):
    if not is_event(of=Alarm.Event.REJECTED, data=data):
        return
    set_alert(into=message, subtitle="블랑", body="가입이 거절 되었습니다.")


def blocked(message: messaging.Message, data: dict = None):
    if not is_event(of=Alarm.Event.BLOCKED, data=data):
        return
    set_alert(into=message, subtitle="블랑", body="계정이 정지 되었습니다.")


def conversation(message: messaging.Message, data: dict = None):
    if not is_event(of=Alarm.Event.CONVERSATION, data=data):
        return

    user_id = data.get("user_id", None)
    setting = Setting.objects(owner=user_id).first()
    is_pushable = setting.push.conversation
    if not is_pushable:
        return

    nickname = data.get("nickname", "알 수 없음")
    image_url = data.get("image_url", "")
    body = "{nickname}: 새로운 메세지가 도착 했습니다.".format(nickname=nickname)
    set_alert(into=message, subtitle="블랑", body=body)
    set_image(into=message, image=image_url)


def poke(message: messaging.Message, data: dict = None):
    if not is_event(of=Alarm.Event.POKE, data=data):
        return

    user_id = data.get("user_id", None)
    setting = Setting.objects(owner=user_id).first()
    is_pushable = setting.push.poke
    if not is_pushable:
        return

    nickname = data.get("nickname", "알 수 없음")
    image_url = data.get("image_url", "")
    body = "{nickname} 님이 당신을 찔렀습니다.".format(nickname=nickname)
    set_alert(into=message, subtitle="블랑", body=body)
    set_image(into=message, image=image_url)


def request(message: messaging.Message, data: dict = None):
    if not is_event(of=Alarm.Event.REQUEST, data=data):
        return

    user_id = data.get("user_id", None)
    setting = Setting.objects(owner=user_id).first()
    is_pushable = setting.push.request
    if not is_pushable:
        return

    nickname = data.get("nickname", "알 수 없음")
    image_url = data.get("image_url", "")
    body = "{nickname} 님이 친구신청을 하였습니다.".format(nickname=nickname)
    set_alert(into=message, subtitle="블랑", body=body)
    set_image(into=message, image=image_url)


def comment(message: messaging.Message, data: dict = None):
    if not is_event(of=Alarm.Event.COMMENT, data=data):
        return

    user_id = data.get("user_id", None)
    setting = Setting.objects(owner=user_id).first()
    is_pushable = setting.push.comment
    if not is_pushable:
        return

    nickname = data.get("nickname", "알 수 없음")
    image_url = data.get("image_url", "")
    body = "{nickname} 님이 댓글을 남겼습니다.".format(nickname=nickname)
    set_alert(into=message, subtitle="블랑", body=body)
    set_image(into=message, image=image_url)


def favorite(message: messaging.Message, data: dict = None):
    if not is_event(of=Alarm.Event.POST_FAVORITE, data=data):
        return

    user_id = data.get("user_id", None)
    setting = Setting.objects(owner=user_id).first()
    is_pushable = setting.push.post_favorite
    if not is_pushable:
        return

    nickname = data.get("nickname", "알 수 없음")
    image_url = data.get("image_url", "")
    body = "{nickname} 님이 당신의 게시물을 좋아합니다.".format(nickname=nickname)
    set_alert(into=message, subtitle="블랑", body=body)
    set_image(into=message, image=image_url)


def matched(message: messaging.Message, data: dict = None):
    if not is_event(of=Alarm.Event.MATCHED, data=data):
        return

    user_id = data.get("user_id", None)
    setting = Setting.objects(owner=user_id).first()
    is_pushable = setting.push.match
    if not is_pushable:
        return

    nickname = data.get("nickname", "알 수 없음")
    image_url = data.get("image_url", "")
    body = "{nickname} 님과 연결 되었습니다.".format(nickname=nickname)
    set_alert(into=message, subtitle="블랑", body=body)
    set_image(into=message, image=image_url)


def thumb_up(message: messaging.Message, data: dict = None):
    if not is_event(of=Alarm.Event.COMMENT_THUMB_UP, data=data):
        return

    user_id = data.get("user_id", None)
    setting = Setting.objects(owner=user_id).first()
    is_pushable = setting.push.comment_thumb_up
    if not is_pushable:
        return

    nickname = data.get("nickname", "알 수 없음")
    image_url = data.get("image_url", "")
    body = "{nickname} 님이 당신의 댓글을 좋아합니다.".format(nickname=nickname)
    set_alert(into=message, subtitle="블랑", body=body)
    set_image(into=message, image=image_url)


def conversation_open(message: messaging.Message, data: dict = None):
    if not is_event(of=Alarm.Event.CONVERSATION_OPEN, data=data):
        return

    user_id = data.get("user_id", None)
    setting = Setting.objects(owner=user_id).first()
    is_pushable = setting.push.conversation_open
    if not is_pushable:
        return

    nickname = data.get("nickname", "알 수 없음")
    image_url = data.get("image_url", "")
    body = "{nickname} 님이 대화방을 열었습니다.".format(nickname=nickname)
    set_alert(into=message, subtitle="블랑", body=body)
    set_image(into=message, image=image_url)


def conversation_leave(message: messaging.Message, data: dict = None):
    if not is_event(of=Alarm.Event.CONVERSATION_LEAVE, data=data):
        pass


def look_up(message: messaging.Message, data: dict = None):
    if not is_event(of=Alarm.Event.LOOK_UP, data=data):
        return

    user_id = data.get("user_id", None)
    setting = Setting.objects(owner=user_id).first()
    is_pushable = setting.push.lookup
    if not is_pushable:
        return

    nickname = data.get("nickname", "알 수 없음")
    image_url = data.get("image_url", "")
    body = "{nickname} 님이 당신의 프로필을 열람 중입니다.".format(nickname=nickname)
    set_alert(into=message, subtitle="블랑", body=body)
    set_image(into=message, image=image_url)


def star_rating(message: messaging.Message, data: dict = None):
    if not is_event(of=Alarm.Event.STAR_RATING, data=data):
        return

    nickname = data.get("nickname", "알 수 없음")
    image_url = data.get("image_url", "")
    body = "{nickname} 님이 당신에게 관심이 있습니다.".format(nickname=nickname)
    set_alert(into=message, body=body)
    set_image(into=message, image=image_url)


def set_alert(into: messaging.Message, title=None, subtitle=None, body=None, badge=0, sound="default"):
    message = into
    message.apns.payload.aps.alert = messaging.ApsAlert(
        title=title,
        subtitle=subtitle,
        body=body
    )
    message.apns.payload.aps.badge = badge
    message.apns.payload.aps.sound = sound


def set_image(into: messaging.Message, image=""):
    message = into
    message.apns.fcm_options = messaging.APNSFCMOptions(image=image)

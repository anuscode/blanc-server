import logging
from firebase_admin import messaging

aps = messaging.Aps(content_available=True)
payload = messaging.APNSPayload(aps=aps)
apns = messaging.APNSConfig(headers={"apns-priority": "5", "apns_priority": "5"}, payload=payload)


def push(data: dict = None, token: str = None, priority="normal"):
    try:
        message = messaging.Message(
            data=data,
            token=token,
            apns=apns,
            android=messaging.AndroidConfig(priority=priority)
        )
        messaging.send(message)
    except Exception as e:
        logging.exception(e)

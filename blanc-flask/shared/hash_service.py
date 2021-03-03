import hashlib

SMS_HASH_KEY = "000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f"


def get_sms_code(phone, expired_at, recur_cnt=1):
    hash_key = sms_sha256(phone + str(expired_at) + str(recur_cnt))
    numerics = []
    for char in hash_key:
        if char.isnumeric():
            numerics.append(char)
    
    sms_code = "".join(numerics[0:6])
    return sms_code if len(sms_code) == 6 else get_sms_code(
        phone, expired_at, recur_cnt=recur_cnt + 1)


def sms_sha256(uid: str):
    sms_hash_key: str = SMS_HASH_KEY
    return sha256(uid + sms_hash_key)


def verify_sms_token(key: str, phone: str, sms_code: str):
    key_to_verify = generate_sms_token(phone, sms_code)
    return key == key_to_verify


def generate_sms_token(phone, sms_code):
    return sha256(str(phone) + str(sms_code))


def sha256(value):
    return hashlib.sha256(bytes(value, 'utf-8')).hexdigest()

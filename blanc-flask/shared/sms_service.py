import re
import requests

from shared import regex

URL = "https://apis.aligo.in/send/"

NORMAL_PHONE_REGEX = regex.NORMAL_PHONE_REGEX

_config = dict(testmode_yn="Y")


def initialize(config):
    _config["testmode_yn"] = config.TESTMODE_YN


def send(phone=None, msg=None):
    phone = phone.replace("+8210", "010").replace("+82010", "010")
    
    if not re.match(NORMAL_PHONE_REGEX, phone):
        raise ValueError("Invalid phone number regex found..")
    
    params = {
        "key": "egzjhd8k5y5extdl7msd7sdcs5900rh4",
        "user_id": "dldyddn0624",
        "sender": "01022889311",
        "receiver": phone,
        "destination": phone,
        "msg": msg,
        "title": "회원가입",
        # "testmode_yn": "Y"
        "testmode_yn": _config["testmode_yn"]
    }
    
    return requests.post(URL, params=params).json()
    # return dict()

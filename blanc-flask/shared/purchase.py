import os

from googleapiclient import discovery
from google.oauth2 import service_account
from googleapiclient.errors import HttpError
from inapppy import GooglePlayValidator, InAppPyValidationError
from inapppy import AppStoreValidator, InAppPyValidationError
from pathlib import Path

play_console_path = '../service_keys/play_console_service_account.json'

current_file_path = Path(os.path.dirname(os.path.abspath(__file__)))

credential_path = os.path.join(current_file_path, play_console_path)

credentials = service_account.Credentials.from_service_account_file(credential_path)

service = discovery.build("androidpublisher", "v3", credentials=credentials)

ios_bundle_id = "com.ground.Blanc-ios"

shared_secret = "0062c0812a164740bed2e43f606cf80c"

android_bundle_id = "com.ground.blanc"


class Struct(object):
    def __init__(self, data):
        for name, value in data.items():
            setattr(self, name, self._wrap(value))

    def _wrap(self, value):
        if isinstance(value, (tuple, list, set, frozenset)):
            return type(value)([self._wrap(v) for v in value])
        else:
            return Struct(value) if isinstance(value, dict) else value


class Product(object):

    def __init__(self, product_id, name, amount):
        self.product_id = product_id
        self.name = name
        self.amount = amount


class Receipt(object):

    def __init__(self, is_verified=False, order_id=None, purchase_time=None):
        self.is_verified = is_verified
        self.order_id = order_id
        self.purchase_time = purchase_time


def verify_android_purchase_token(product_id, token):
    try:
        result = service.purchases().products().get(
            packageName=android_bundle_id, productId=product_id, token=token
        ).execute()

        if not result:
            return Receipt(is_verified=False)

        purchase_state = result.get("purchaseState", 1)
        consumption_state = result.get("consumptionState", 1)
        order_id = result.get("orderId", "")
        purchase_time = int(int(result.get("purchaseTimeMillis", 0)) / 1000)

        if purchase_state == 0 and consumption_state == 0:
            return Receipt(is_verified=True, order_id=order_id, purchase_time=purchase_time)
        else:
            return Receipt(is_verified=False)

    except HttpError:
        return Receipt(is_verified=False)


def decode_receipt(receipt):
    validator = AppStoreValidator(ios_bundle_id, sandbox=True, auto_retry_wrong_env_request=False)

    try:
        validation = validator.validate(receipt, shared_secret=shared_secret)
        result = Struct(validation)
        return result
    except InAppPyValidationError as ex:
        # handle validation error
        response = ex.raw_response  # contains actual response from AppStore service.
        return Struct(response)


def products():
    return [
        # ios
        Product(product_id="ios.com.ground.blanc.point.2500.won", name="Point 10", amount=10),
        Product(product_id="ios.com.ground.blanc.point.4900.won", name="Point 20", amount=20),
        Product(product_id="ios.com.ground.blanc.point.11000.won", name="Point 50", amount=50),
        Product(product_id="ios.com.ground.blanc.point.20000.won", name="Point 100", amount=100),
        Product(product_id="ios.com.ground.blanc.point.36000.won", name="Point 200", amount=200),
        Product(product_id="ios.com.ground.blanc.point.79000.won", name="Point 500", amount=500),
        # android
        Product(product_id="android.com.ground.blanc.point.2500.won", name="Point 10", amount=10),
        Product(product_id="android.com.ground.blanc.point.4500.won", name="Point 20", amount=20),
        Product(product_id="android.com.ground.blanc.point.13500.won", name="Point 50", amount=50),
        Product(product_id="android.com.ground.blanc.point.25500.won", name="Point 100", amount=100),
        Product(product_id="android.com.ground.blanc.point.44900.won", name="Point 200", amount=200),
        Product(product_id="android.com.ground.blanc.point.99900.won", name="Point 500", amount=500)
    ]


def get_amount(of=None):
    product_id = of
    amount = next((product.amount for product in products() if product.product_id == product_id), None)
    if not amount:
        raise ValueError("Invalid product id..")
    return amount

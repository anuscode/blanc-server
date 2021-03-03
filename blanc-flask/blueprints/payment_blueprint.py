import json

from flask import Blueprint
from flask import Response
from flask import request
from model.models import User, Payment
from shared.annotation import id_token_required
from shared.purchase import verify_android_purchase_token, decode_receipt, get_amount

payment_blueprint = Blueprint("payment_blueprint", __name__)


@payment_blueprint.route("/payments/users/<user_id>/amount", methods=["GET"])
def route_get_amount(user_id: str):
    user = User.objects.get_or_404(id=user_id)
    payments = Payment.objects(owner=user).as_pymongo()

    amount_sum = 0

    for payment in payments:
        amount_sum += payment.get("amount")

    response = json.dumps(dict(amount=amount_sum))
    return Response(response, mimetype="application/json")


@payment_blueprint.route(
    "/payments/users/<user_id>/product_id/<product_id>/purchase_token/<purchase_token>/platform/android",
    methods=["POST"])
@id_token_required
def route_payment_purchase_android(user_id: str, product_id: str, purchase_token: str):
    user = User.get_verified_user(user_id, request)

    purchase_result = verify_android_purchase_token(product_id, purchase_token)

    if not purchase_result.is_verified:
        response = json.dumps(dict(result=False))
        return Response(response, mimetype="application/json")

    amount = get_amount(of=product_id)

    user.purchase(
        platform="ANDROID",
        order_id=purchase_result.order_id,
        amount=amount,
        purchase_time=purchase_result.purchase_time
    )

    response = json.dumps(dict(result=True))
    return Response(response, mimetype="application/json")


@payment_blueprint.route("/payments/users/<user_id>/platform/ios", methods=["POST"])
@id_token_required
def route_payment_purchase_ios(user_id: str):
    user = User.get_verified_user(user_id, request)

    token = request.form.get("token", None)
    if not token:
        raise ValueError("Token not found ..")

    result = decode_receipt(token)

    if int(result.status) != 0:
        response = json.dumps(dict(result=False))
        return Response(response, mimetype="application/json")

    purchase = result.receipt.in_app[0]
    product_id = purchase.product_id
    transaction_id = purchase.transaction_id
    purchase_time = int(purchase.purchase_date_ms) / 1000
    amount = get_amount(of=product_id)

    user.purchase(
        platform="IOS",
        order_id=transaction_id,
        product_id=product_id,
        amount=amount,
        purchase_time=purchase_time
    )

    response = json.dumps(dict(result=True))
    return Response(response, mimetype="application/json")
import logging

from flask import Blueprint, jsonify

errors_blue_print = Blueprint('errors', __name__)


@errors_blue_print.app_errorhandler(401)
def handle_unexpected_error(error):
    logging.exception(error)
    response = dict(error_code="0000")
    return jsonify(response), 401


@errors_blue_print.app_errorhandler(404)
def handle_unexpected_error(error):
    logging.exception(error)
    response = dict(error_code="0000")
    return jsonify(response), 404


@errors_blue_print.app_errorhandler(500)
def handle_unexpected_error(error):
    logging.exception(error)
    response = dict(error_code="0000")
    return jsonify(response), 500

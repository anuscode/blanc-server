import logging

from flask import Blueprint, jsonify

errors_blue_print = Blueprint('errors', __name__)


@errors_blue_print.app_errorhandler(404)
def handle_unexpected_error(error):
    logging.exception(error)
    
    status_code = 404
    response = {
        'status_code': status_code,
        'type': 'UnexpectedException',
        'message': str(error)
    }
    return jsonify(response), status_code

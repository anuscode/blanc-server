import logging

from flask import Blueprint, jsonify

errors_blue_print = Blueprint('errors', __name__)


@errors_blue_print.app_errorhandler(Exception)
def handle_unexpected_error(error):
    logging.exception(error)
    
    status_code = 500
    success = False
    response = {
        'success': success,
        'status_code': status_code,
        'type': 'UnexpectedException',
        'message': str(error)
    }
    return jsonify(response), status_code

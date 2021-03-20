import firebase_admin
import logging
import logging.handlers
import os

from blueprints.users_blueprint import users_blueprint
from blueprints.posts_blueprint import posts_blueprint
from blueprints.requests_blueprint import requests_blueprint
from blueprints.conversation_blueprint import conversations_blueprint
from blueprints.alarm_blueprint import alarms_blueprint
from blueprints.error_blueprint import errors_blue_print
from blueprints.payment_blueprint import payment_blueprint
from blueprints.verifications_blueprint import verifications_blueprint
from blueprints.admin_blueprint import admin_blueprint
from blueprints.report_blueprint import report_blueprint

from config import DevConfig

from firebase_admin import credentials
from flask import Flask
from flask_mongoengine import MongoEngine
from shared import sms_service
from pathlib import Path
from pymongo import monitoring

LOG_PATH = os.path.join(
    Path(os.path.dirname(os.path.abspath(__file__))), 'flask_instance.log')

CREDENTIAL_PATH = os.path.join(
    Path(os.path.dirname(
        os.path.abspath(__file__))), 'service_keys/service_account.json')


def init_sms_service(config):
    sms_service.initialize(config)


def init_firebase(config):
    cred = credentials.Certificate(CREDENTIAL_PATH)
    return firebase_admin.initialize_app(cred, config.FIREBASE_APP)


def init_mongo(app):
    init_mongo_logger(app)
    MongoEngine().init_app(app)


def init_mongo_logger(app):
    class CommandLogger(monitoring.CommandListener):
        
        def started(self, event):
            pass
            # app.logger.info("Command {0.command_name} with request id "
            #                 "{0.request_id} started on server "
            #                 "{0.connection_id}".format(event))
        
        def succeeded(self, event):
            app.logger.info("Command {0.command_name} with request id "
                            "{0.request_id} on server {0.connection_id} "
                            "succeeded in {0.duration_micros} "
                            "microseconds".format(event))
        
        def failed(self, event):
            app.logger.info("Command {0.command_name} with request id "
                            "{0.request_id} on server {0.connection_id} "
                            "failed in {0.duration_micros} "
                            "microseconds".format(event))
    
    if app.config["DEBUG"]:
        monitoring.register(CommandLogger())


def create_app(config=None, mongo=True, firebase=True) -> Flask:
    if not config:
        raise ValueError("Config is required value.")
    
    app = Flask(__name__)
    
    app.logger.addHandler(
        logging.handlers.RotatingFileHandler(
            filename=LOG_PATH, mode='a',
            maxBytes=10485760, backupCount=10,
            encoding='utf-8', delay=False))
    
    # config
    app.config.from_object(config)
    # logger
    app.logger.setLevel(logging.DEBUG)
    # blue prints
    app.register_blueprint(users_blueprint)
    app.register_blueprint(posts_blueprint)
    app.register_blueprint(requests_blueprint)
    app.register_blueprint(conversations_blueprint)
    app.register_blueprint(alarms_blueprint)
    app.register_blueprint(errors_blue_print)
    app.register_blueprint(payment_blueprint)
    app.register_blueprint(verifications_blueprint)
    app.register_blueprint(admin_blueprint)
    app.register_blueprint(report_blueprint)

    if mongo:
        init_mongo(app)
    if firebase:
        init_firebase(config)
    
    init_sms_service(config)
    
    return app


if __name__ == "__main__":
    app = create_app(config=DevConfig)
    app.run(host='0.0.0.0', port=5000, debug=DevConfig.DEBUG, threaded=True)

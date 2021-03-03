import os

from dotenv import load_dotenv, find_dotenv
from pathlib import Path

ENV_DIR = os.path.join(Path(os.path.dirname(os.path.abspath(__file__))), 'env/qa.env')
load_dotenv(ENV_DIR)


class Config(object):
    """Base config, uses staging database server."""
    DEBUG = False
    TESTING = False
    JSON_AS_ASCII = False  # for jsonify encoding issue
    FIREBASE_APP = {
        'storageBucket': "blanc-850624.appspot.com",
    }
    MONGODB_SETTINGS = {
        'host': 'mongodb://34.64.134.230:7361/pingme-test'  # external
    }
    IP_STACK = {
        'ACCESS_KEY': "e8ab27ee174997778b7826a94b7db233"
    }
    DEBUG_TB_PANELS = [
        'flask_debugtoolbar.panels.versions.VersionDebugPanel',
        'flask_debugtoolbar.panels.timer.TimerDebugPanel',
        'flask_debugtoolbar.panels.headers.HeaderDebugPanel',
        'flask_debugtoolbar.panels.request_vars.RequestVarsDebugPanel',
        'flask_debugtoolbar.panels.template.TemplateDebugPanel',
        'flask_debugtoolbar.panels.sqlalchemy.SQLAlchemyDebugPanel',
        'flask_debugtoolbar.panels.logger.LoggingPanel',
        'flask_debugtoolbar.panels.profiler.ProfilerDebugPanel',
        'flask_debugtoolbar_mongo.panel.MongoDebugPanel',
    ]
    DEBUG_TB_MONGO = {
        'SHOW_STACKTRACES': True,
        'HIDE_FLASK_FROM_STACKTRACES': True
    }
    DEBUG_TB_INTERCEPT_REDIRECTS = False
    TESTMODE_YN = "Y"
    SECRET_KEY = "SECRET_KEY"


class ProdConfig(Config):
    MONGODB_SETTINGS = {
        'host': 'mongodb://10.178.0.13:7361/blanc-prod'  # internal
    }
    TESTMODE_YN = "N"


class QaConfig(Config):
    DEBUG = True
    TESTING = True
    MONGODB_SETTINGS = {
        'host': 'mongodb://10.178.0.12:7361/pingme-test'  # internal
    }
    TESTMODE_YN = "N"


class DevConfig(Config):
    DEBUG = True
    TESTING = True
    TESTMODE_YN = "N"


class RemoteProdConfig(Config):
    DEBUG = True
    TESTING = True
    MONGODB_SETTINGS = {
        'host': 'mongodb://34.64.134.230:7361/pingme-test'  # internal
    }
    TESTMODE_YN = "N"


class UnitTestConfig(Config):
    DEBUG = True
    TESTING = True

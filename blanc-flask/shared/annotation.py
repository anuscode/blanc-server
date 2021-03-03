import pendulum

from flask import abort
from flask import request
from firebase_admin import auth
from functools import wraps


def id_token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        uid = request.headers.get("uid", None)
        token = request.headers.get("id_token", None)
        decoded_token = auth.verify_id_token(token)
        uid_to_verify = decoded_token["uid"]
        
        if uid != uid_to_verify:
            abort(401)
        
        return f(*args, **kwargs)
    
    return decorated_function


def time_lapse(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start = pendulum.now().timestamp()
        result = f(*args, **kwargs)
        
        end = pendulum.now().timestamp()
        elapsed = end - start
        print(f.__name__ + " : " + str(elapsed))
        return result
    
    return decorated_function

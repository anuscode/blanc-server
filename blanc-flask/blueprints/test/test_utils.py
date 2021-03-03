from blueprints.test.mock_data import mock_user_1, mock_user_2, mock_user_3
from model.models import User

user_1_sms_token = '76d692123c22a83aa38f1237d6b2ed1db565c29e7e71e6942d28fdb1447fac18'
user_2_sms_token = 'cef8e3adb31073b28bc4c6ff73309e304254368f836d3d0f402065636e68fde0'
user_3_sms_token = '737245306a1d56a00563361aed4ae64e15dd589e0cc33dd8d52778d1eb49f5e4'


def create_user(app, mock_user, sms_token):
    mock_user["sms_token"] = sms_token
    mock_user["sms_code"] = "000000"
    
    response = app.post("/users", headers=dict(uid=mock_user["uid"]), data=mock_user)
    
    user_id = response.get_json().get("_id")
    
    user = User.get(id=user_id)
    mock_user.pop("sms_token")
    mock_user.pop("sms_code")
    mock_user.pop("user_images")
    user.update(**mock_user)
    
    user.save()
    
    return response


def create_user_1(app):
    mock_user = mock_user_1.copy()
    return create_user(app, mock_user, user_1_sms_token)


def create_user_2(app):
    mock_user = mock_user_2.copy()
    return create_user(app, mock_user, user_2_sms_token)


def create_user_3(app):
    mock_user = mock_user_3.copy()
    return create_user(app, mock_user, user_3_sms_token)

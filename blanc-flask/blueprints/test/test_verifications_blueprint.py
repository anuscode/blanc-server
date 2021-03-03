import firebase_admin
import mock
import unittest
import pendulum

from mongoengine import connect, disconnect
from app import create_app
from app import init_firebase
from blueprints.test.test_utils import create_user_1, create_user_2, create_user_3
from blueprints.test.mock_data import mock_user_1, mock_user_2, mock_user_3
from blueprints.verifications_blueprint import issue

from config import UnitTestConfig

from firebase_admin import auth
from firebase_admin import messaging

from shared import hash_service


class VerificationBlueprintTestCase(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls) -> None:
        cls.firebase_app = init_firebase(UnitTestConfig)
    
    def setUp(self) -> None:
        connect('mongoenginetest', host='mongomock://localhost')
        app = create_app(UnitTestConfig, mongo=False, firebase=False)
        app.app_context().push()
        self.app = app.test_client()
        messaging.send = lambda x: x
    
    def tearDown(self):
        disconnect()
    
    @classmethod
    def tearDownClass(cls) -> None:
        firebase_admin.delete_app(cls.firebase_app)
    
    @mock.patch.object(auth, 'verify_id_token')
    def test_issue(self, verify_id_token):
        verify_id_token.return_value = dict(uid=mock_user_1["uid"])
        create_user_1(self.app)
        
        # Create testing datetime
        known = pendulum.datetime(2001, 5, 21, 12)
        pendulum.set_test_now(known)
        
        response = self.app.post("/verifications/sms", data=dict(phone="+821022889311"))
        json_data = response.get_json()
        expired_at = json_data.get("expired_at")
        expired_at_to_verify = pendulum.now().int_timestamp + (60 * 10)
        
        self.assertEqual(expired_at, expired_at_to_verify)
    
    def test_issue2(self):
        # Create testing datetime
        known = pendulum.datetime(2001, 5, 21, 12)
        pendulum.set_test_now(known)
        phone, expired_at = "+821022889311", pendulum.now().int_timestamp
        
        sms_code = hash_service.get_sms_code(phone, expired_at)
        self.assertEqual(sms_code, "291455")
        
        result = issue("+821022889311")
        expired_at = result.get("expired_at")
        self.assertEqual(expired_at, 990447000)
    
    @mock.patch.object(auth, 'verify_id_token')
    @mock.patch.object(auth, 'get_user')
    def test_verify_fail_due_to_duplicate_phone(self, get_user, verify_id_token):
        class MockUser:
            email = "NotEmpty@gmail.com"
        
        verify_id_token.return_value = dict(uid=mock_user_1["uid"])
        get_user.return_value = MockUser()
        create_user_1(self.app)
        
        # Create testing datetime
        known = pendulum.datetime(2001, 5, 21, 12)
        pendulum.set_test_now(known)
        
        response = self.app.put("/verifications/sms", data=dict(
            phone="+821022889311", expired_at="990446400", sms_code="291455"
        ))
        json_data = response.get_json()
        self.assertEqual(json_data.get("verified"), True)
        
        phone = json_data["phone"]
        sms_code = json_data["sms_code"]
        sms_token = json_data["sms_token"]
        
        response = self.app.get("/users/phone/{phone}/sms_code/{sms_code}/sms_token/{sms_token}".format(
            phone=phone, sms_code=sms_code, sms_token=sms_token
        ))
        json_data = response.get_json()
        email, is_exists = json_data["email"], json_data["is_exists"]
        
        self.assertEqual(email, "NotEmpty@gmail.com")
        self.assertEqual(is_exists, True)
    
    @mock.patch.object(auth, 'verify_id_token')
    def test_verify_success(self, verify_id_token):
        verify_id_token.return_value = dict(uid=mock_user_1["uid"])
        create_user_1(self.app)
        
        # Create testing datetime
        known = pendulum.datetime(2001, 5, 21, 12)
        pendulum.set_test_now(known)
        
        response = self.app.put("/verifications/sms", data=dict(
            phone="+821022881234", expired_at="990446400", sms_code="174522"
        ), headers=dict(uid=mock_user_1["uid"]))
        json_data = response.get_json()
        self.assertEqual(json_data.get("verified"), True)
    
    @mock.patch.object(auth, 'verify_id_token')
    def test_verify_failed(self, verify_id_token):
        verify_id_token.return_value = dict(uid=mock_user_1["uid"])
        create_user_1(self.app)
        
        # Create testing datetime
        known = pendulum.datetime(2001, 5, 21, 12)
        pendulum.set_test_now(known)
        
        response = self.app.put("/verifications/sms", data=dict(
            phone="+821022889311", expired_at="990446400", sms_code="STRANGE_CODE"
        ), headers=dict(uid=mock_user_1["uid"]))
        
        json_data = response.get_json()
        verified, reason = json_data["verified"], json_data["reason"]
        self.assertEqual(verified, False)
        self.assertEqual(reason, "유효하지 않은 SMS_CODE 입니다.")
    
    @mock.patch.object(auth, 'verify_id_token')
    def test_verify_failed2(self, verify_id_token):
        verify_id_token.return_value = dict(uid=mock_user_1["uid"])
        create_user_1(self.app)
        
        # Create testing datetime
        known = pendulum.datetime(2001, 5, 21, 12)
        pendulum.set_test_now(known)
        
        response = self.app.put("/verifications/sms", data=dict(
            phone="INVALID_PHONE_NUMBER", expired_at="990446400", sms_code="957822"
        ), headers=dict(uid=mock_user_1["uid"]))
        
        json_data = response.get_json()
        verified, reason = json_data["verified"], json_data["reason"]
        self.assertEqual(verified, False)
        self.assertEqual(reason, "유효하지 않은 SMS_CODE 입니다.")
    
    @mock.patch.object(auth, 'verify_id_token')
    def test_verify_failed3(self, verify_id_token):
        verify_id_token.return_value = dict(uid=mock_user_1["uid"])
        create_user_1(self.app)
        
        # Create testing datetime
        known = pendulum.datetime(2001, 5, 23, 12)
        pendulum.set_test_now(known)
        
        response = self.app.put("/verifications/sms", data=dict(
            phone="+821022889311", expired_at="990446400", sms_code="291455"
        ), headers=dict(uid=mock_user_1["uid"]))
        json_data = response.get_json()
        verified, reason = json_data["verified"], json_data["reason"]
        self.assertEqual(verified, False)
        self.assertEqual(reason, "SMS_CODE가 만료 되었습니다.")


if __name__ == "__main__":
    unittest.main()

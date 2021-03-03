import firebase_admin
import json
import unittest
import pendulum

from blueprints.test.mock_data import *
from config import UnitTestConfig
from firebase_admin import auth
from firebase_admin import messaging
from app import create_app
from app import init_firebase

from blueprints.test.test_utils import create_user_1, create_user_2, create_user_3
from model.models import User, Request, Conversation, Payment
from mongoengine import connect, disconnect
from unittest import mock
from werkzeug import exceptions

REQUEST_TYPE_LIKE = 1
REQUEST_TYPE_FRIEND = 2

LONG_MAX = 9223372036854775800

class RequestsBlueprintTestCase(unittest.TestCase):
    
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
    
    def insert_request(self, uid_from, uid_to, request_type_id, mock_token="mock_token"):
        url = "/requests/from/{uid_from}/to/{uid_to}/request_type_id/{request_type_id}".format(
            uid_from=uid_from, uid_to=uid_to, request_type_id=request_type_id)
        content_type = "application/json"
        data = json.dumps(dict(token=mock_token))
        
        with mock.patch("firebase_admin.auth.verify_id_token") as mock_up:
            mock_up.return_value = dict(uid=uid_from)
            self.app.post(url, data=data, content_type=content_type)
        return uid_from, uid_to
    
    @mock.patch.object(auth, 'verify_id_token')
    @mock.patch.object(messaging, 'send', return_value=None)
    def test_create_request(self, mock_send, mock_verify_id_token):
        """Should have a new request has been created."""
        
        mock_verify_id_token.return_value = dict(uid=mock_user_1["uid"])
        response_1 = create_user_1(self.app)
        
        mock_verify_id_token.return_value = dict(uid=mock_user_2["uid"])
        response_2 = create_user_2(self.app)
        
        # 1: user_from, 2: user_to
        user_1, user_2 = response_1.get_json(), response_2.get_json()
        user_1, user_2 = User.objects.get_or_404(id=user_1["_id"]), \
                         User.objects.get_or_404(id=user_2["_id"])
        
        mock_verify_id_token.return_value = dict(uid=user_1.uid)
        response = self.app.post("/requests/user_to/{user_id}/type/{type}".format(
            user_id=str(user_2.id), type=1),
            headers=dict(uid=user_1.uid))
        
        self.assertEqual(response.status_code, 200)
        
        request = Request.objects.first()
        self.assertEqual(request.user_from.uid, mock_user_1["uid"])
        self.assertEqual(request.user_to.uid, mock_user_2["uid"])
        
        self.assertEqual(mock_send.call_count, 1)
    
    @mock.patch.object(auth, 'verify_id_token')
    @mock.patch.object(messaging, 'send', return_value=None)
    def test_create_request_with_free_pass_unavailable_and_no_point(
            self, mock_send, mock_verify_id_token):
        """Should have a new request has been canceled."""
        mock_verify_id_token.return_value = dict(uid=mock_user_1["uid"])
        response_1 = create_user_1(self.app)
        
        mock_verify_id_token.return_value = dict(uid=mock_user_2["uid"])
        response_2 = create_user_2(self.app)
        
        # 1: user_from, 2: user_to
        user_1, user_2 = response_1.get_json(), response_2.get_json()
        user_1, user_2 = User.objects.get_or_404(id=user_1["_id"]), \
                         User.objects.get_or_404(id=user_2["_id"])
        
        mock_verify_id_token.return_value = dict(uid=user_1["uid"])
        
        user = User.objects(uid=user_1["uid"]).first()
        # unavailable tokens
        user.update(free_pass_tokens=[LONG_MAX, LONG_MAX])
        
        response = self.app.post("/requests/user_to/{user_id}/type/{type}".format(
            user_id=str(user_2.id), type=1),
            headers=dict(uid=user_1["uid"]))
        
        self.assertEqual(response.status_code, 500)
        self.assertEqual(mock_send.call_count, 0)
    
    @mock.patch.object(auth, 'verify_id_token')
    @mock.patch.object(messaging, 'send', return_value=None)
    def test_create_request_with_free_pass_unavailable_but_point_available(
            self, mock_send, mock_verify_id_token):
        """Should have a new request has been created."""
        mock_verify_id_token.return_value = dict(uid=mock_user_1["uid"])
        response_1 = create_user_1(self.app)
        
        mock_verify_id_token.return_value = dict(uid=mock_user_2["uid"])
        response_2 = create_user_2(self.app)
        
        # 1: user_from, 2: user_to
        user_1, user_2 = response_1.get_json(), response_2.get_json()
        user_1, user_2 = User.objects.get_or_404(id=user_1["_id"]), \
                         User.objects.get_or_404(id=user_2["_id"])
        
        mock_verify_id_token.return_value = dict(uid=user_1["uid"])
        
        user = User.objects(uid=user_1["uid"]).first()
        user.update(free_pass_tokens=[LONG_MAX, LONG_MAX])
        # payment point is charged.
        Payment(owner=user, type="PURCHASE", amount=10,
                created_at=pendulum.now().int_timestamp).save()
        point_amount = user.get_current_amount_of_point()
        self.assertEqual(point_amount, 10)
        
        response = self.app.post("/requests/user_to/{user_id}/type/{type}".format(
            user_id=str(user_2.id), type=1),
            headers=dict(uid=user_1["uid"]))
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_send.call_count, 1)
        point_amount = user.get_current_amount_of_point()
        self.assertEqual(point_amount, 5)
    
    @mock.patch.object(auth, 'verify_id_token')
    @mock.patch.object(messaging, 'send', return_value=None)
    def test_create_request_with_free_pass_available_and_point_available(
            self, mock_send, mock_verify_id_token):
        """Should have a new request has been created."""
        mock_verify_id_token.return_value = dict(uid=mock_user_1["uid"])
        response_1 = create_user_1(self.app)
        
        mock_verify_id_token.return_value = dict(uid=mock_user_2["uid"])
        response_2 = create_user_2(self.app)
        
        # 1: user_from, 2: user_to
        user_1, user_2 = response_1.get_json(), response_2.get_json()
        user_1, user_2 = User.objects.get_or_404(id=user_1["_id"]), \
                         User.objects.get_or_404(id=user_2["_id"])
        
        mock_verify_id_token.return_value = dict(uid=user_1["uid"])
        
        user = User.objects(uid=user_1["uid"]).first()
        # free pass has been never used that it's available now
        user.update(free_pass_tokens=[0, 0])
        # payment point is charged.
        Payment(owner=user, type="PURCHASE", amount=2,
                created_at=pendulum.now().int_timestamp).save()
        point_amount = user.get_current_amount_of_point()
        self.assertEqual(point_amount, 2)
        
        response = self.app.post(
            "/requests/user_to/{user_id}/type/{type}".format(
                user_id=str(user_2["id"]), type=1),
            headers=dict(uid=user_1["uid"]))
        
        self.assertEqual(response.status_code, 200)
        
        self.assertEqual(mock_send.call_count, 1)
        self.assertEqual(user.get_current_amount_of_point(), 2)  # should be never been used.
        
        user = User.objects(uid=user_1["uid"]).first()
        self.assertNotEqual(user.free_pass_tokens, [LONG_MAX, LONG_MAX])
    
    @mock.patch.object(auth, 'verify_id_token')
    @mock.patch.object(messaging, 'send', return_value=None)
    def test_create_duplicated_request(
            self, mock_send, mock_verify_id_token):
        """Should have a bad request exception raise."""
        
        mock_verify_id_token.return_value = dict(uid=mock_user_1["uid"])
        response_1 = create_user_1(self.app)
        
        mock_verify_id_token.return_value = dict(uid=mock_user_2["uid"])
        response_2 = create_user_2(self.app)
        
        # 1: user_from, 2: user_to
        user_1, user_2 = response_1.get_json(), response_2.get_json()
        user_1, user_2 = User.objects.get_or_404(id=user_1["_id"]), \
                         User.objects.get_or_404(id=user_2["_id"])
        
        mock_verify_id_token.return_value = dict(uid=user_1["uid"])
        response = self.app.post(
            "/requests/user_to/{user_id}/type/{type}".format(
                user_id=str(user_2["id"]), type=1),
            headers=dict(uid=user_1["uid"]))
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_send.call_count, 1)
        
        with self.app as client:
            # send duplicate one again to raise ValueError intended.
            client.post(
                "/requests/user_to/{user_id}/type/{type}".format(
                    user_id=str(user_2["id"]), type=1),
                headers=dict(uid=user_1["uid"]))
            self.assertRaises(exceptions.BadRequest)
            self.assertEqual(mock_send.call_count, 1)
    
    @mock.patch.object(auth, 'verify_id_token')
    @mock.patch.object(messaging, 'send', return_value=None)
    def test_create_request_when_he_already_sent_me(
            self, mock_send, mock_verify_id_token):
        """Should have the response of the request become 1."""
        
        mock_verify_id_token.return_value = dict(uid=mock_user_1["uid"])
        response_1 = create_user_1(self.app)
        
        mock_verify_id_token.return_value = dict(uid=mock_user_2["uid"])
        response_2 = create_user_2(self.app)
        
        # 1: user_from, 2: user_to
        user_1, user_2 = response_1.get_json(), response_2.get_json()
        user_1, user_2 = User.objects.get_or_404(id=user_1["_id"]), \
                         User.objects.get_or_404(id=user_2["_id"])
        
        mock_verify_id_token.return_value = dict(uid=user_1["uid"])
        response = self.app.post(
            "/requests/user_to/{user_id}/type/{type}".format(
                user_id=str(user_2["id"]), type=1),
            headers=dict(uid=user_1["uid"]))
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_send.call_count, 1)
        
        mock_verify_id_token.return_value = dict(uid=user_2["uid"])
        response = self.app.post(
            "/requests/user_to/{user_id}/type/{type}".format(
                user_id=str(user_1["id"]), type=1),
            headers=dict(uid=user_2["uid"]))
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_send.call_count, 2)
        
        request_id = response.get_json()["_id"]
        request = Request.objects.get_or_404(id=request_id)
        self.assertEqual(request.response, 1)
    
    @mock.patch.object(auth, 'verify_id_token')
    @mock.patch.object(messaging, 'send', return_value=None)
    def test_list_requests_to_me(self, mock_send, mock_verify_id_token):
        """Should have requests list which does like me."""
        
        mock_verify_id_token.return_value = dict(uid=mock_user_1["uid"])
        response_1 = create_user_1(self.app)
        
        mock_verify_id_token.return_value = dict(uid=mock_user_2["uid"])
        response_2 = create_user_2(self.app)
        
        mock_verify_id_token.return_value = dict(uid=mock_user_3["uid"])
        response_3 = create_user_3(self.app)
        
        user_1, user_2, user_3 = \
            response_1.get_json(), response_2.get_json(), response_3.get_json()
        
        user_1, user_2, user_3 = \
            User.objects.get_or_404(id=str(user_1["_id"])), \
            User.objects.get_or_404(id=str(user_2["_id"])), \
            User.objects.get_or_404(id=str(user_3["_id"]))
        
        # set mock id token
        mock_verify_id_token.return_value = dict(uid=user_2["uid"])
        response_1 = self.app.post("/requests/user_to/{user_id}/type/{type}".format(
            user_id=str(user_1["id"]), type=1),
            headers=dict(uid=user_2["uid"]))
        
        self.assertEqual(mock_send.call_count, 1)
        self.assertEqual(response_1.status_code, 200)
        
        # set mock id token
        mock_verify_id_token.return_value = dict(uid=user_3["uid"])
        response_2 = self.app.post("/requests/user_to/{user_id}/type/{type}".format(
            user_id=str(user_1["id"]), type=1),
            headers=dict(uid=user_3["uid"]))
        
        self.assertEqual(mock_send.call_count, 2)
        self.assertEqual(response_2.status_code, 200)
        
        user = User.objects(id=str(user_1["id"])).first()
        requests = user.list_requests_to_me()
        request_1, request_2 = requests[0], requests[1]
        
        self.assertEqual(len(requests), 2)
        # from mock_user_2 to mock_user_1
        self.assertEqual(
            request_1["user_from"]["nickname"], user_2["nickname"])  # user_from
        self.assertEqual(
            request_1["user_to"]["nickname"], user_1["nickname"])  # user_to
        # from mock_user_3 to mock_user_1
        self.assertEqual(
            request_2["user_from"]["nickname"], user_3["nickname"])  # user_from
        self.assertEqual(
            request_2["user_to"]["nickname"], user_1["nickname"])  # user_to
    
    @mock.patch.object(auth, 'verify_id_token')
    @mock.patch.object(messaging, 'send', return_value=None)
    def test_update_request_accepted(self, mock_send, mock_verify_id_token):
        """Should have response become 1 after the update."""
        # set mock time
        mock_time = pendulum.datetime(2020, 5, 21, 12)
        pendulum.set_test_now(mock_time)
        # create 2 users
        mock_verify_id_token.return_value = dict(uid=mock_user_1["uid"])
        response_1 = create_user_1(self.app)
        
        mock_verify_id_token.return_value = dict(uid=mock_user_2["uid"])
        response_2 = create_user_2(self.app)
        
        # 1: user_from, 2: user_to
        user_1, user_2 = response_1.get_json(), response_2.get_json()
        
        user_1 = User.objects.get_or_404(id=user_1["_id"])
        user_2 = User.objects.get_or_404(id=user_2["_id"])
        
        # set mock id token
        mock_verify_id_token.return_value = dict(uid=user_1["uid"])
        # create a request
        response = self.app.post("/requests/user_to/{user_id}/type/{type}".format(
            user_id=str(user_2["id"]), type=1),
            headers=dict(uid=user_1["uid"]))
        
        self.assertEqual(mock_send.call_count, 1)
        self.assertEqual(response.status_code, 200)
        
        req = Request.objects.first()
        
        # update a request with response 1 (yes)
        response = self.app.put(
            "/requests/{rid}/response/{response}".format(
                rid=req["id"], response=1),
            headers=dict(uid=user_2["uid"]))
        
        # assert request
        updated_request = Request.objects.first()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(updated_request.response, 1)
        self.assertEqual(updated_request.responded_at, pendulum.now().int_timestamp)
        self.assertEqual(mock_send.call_count, 2)
        
        # chat room must be created when accepted.
        conversation = Conversation.objects.first()
        member_1, member_2 = conversation.participants[0], conversation.participants[1]
        self.assertEqual(user_1["uid"], member_1["uid"])
        self.assertEqual(user_2["uid"], member_2["uid"])
        self.assertEqual(conversation.created_at, pendulum.now().int_timestamp)
    
    @mock.patch.object(auth, 'verify_id_token')
    @mock.patch.object(messaging, 'send', return_value=None)
    def test_update_request_declined(self, mock_send, mock_verify_id_token):
        """Should have response become 0 after the update."""
        # set mock time
        mock_time = pendulum.datetime(2020, 5, 21, 12)
        pendulum.set_test_now(mock_time)
        # create 2 users
        
        mock_verify_id_token.return_value = dict(uid=mock_user_1["uid"])
        response_1 = create_user_1(self.app)
        
        mock_verify_id_token.return_value = dict(uid=mock_user_2["uid"])
        response_2 = create_user_2(self.app)
        
        # 1: user_from, 2: user_to
        user_from, user_to = \
            response_1.get_json(), response_2.get_json()
        
        # set mock id token
        user_from = User.objects.get_or_404(id=user_from["_id"])
        mock_verify_id_token.return_value = dict(uid=user_from["uid"])
        # create a request
        response = self.app.post("/requests/user_to/{user_id}/type/{type}".format(
            user_id=user_to["_id"], type=1),
            headers=dict(uid=user_from["uid"]))
        req = Request.objects.first()
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mock_send.call_count, 1)  # should be called when created
        
        # update a request with response 0 (No!)
        user_from = User.objects.get_or_404(id=user_to["_id"])
        response = self.app.put("/requests/{rid}/response/{response}".format(
            rid=req.id, response=0),
            headers=dict(uid=user_from["uid"]))
        
        # assert
        updated_request = Request.objects.first()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(updated_request.response, 0)
        self.assertEqual(mock_send.call_count, 1)  # should be not called when declined
        self.assertEqual(updated_request.responded_at, pendulum.now().int_timestamp)


if __name__ == "__main__":
    unittest.main()

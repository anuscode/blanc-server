import firebase_admin
import json
import unittest
import pendulum
import mock

from mongoengine import connect, disconnect
from app import create_app
from app import init_firebase
from blueprints.test.mock_data import *
from config import UnitTestConfig
from model.models import User, Conversation

from firebase_admin import auth
from firebase_admin import messaging
from blueprints.test.test_utils import create_user_1, create_user_2, create_user_3

REQUEST_TYPE_LIKE = 10
REQUEST_TYPE_FRIEND = 20


class ConversationsBlueprintTestCase(unittest.TestCase):
    
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
    
    def test_create_conversation(self):
        response = self.app.post(
            "/conversations", data=json.dumps(dict(title="mock_title")),
            content_type="application/json")
        
        conversation = Conversation.objects.first()
        self.assertEqual(conversation.title, "mock_title")
    
    def test_delete_conversation(self):
        response = self.app.post("/conversations", data=json.dumps(dict(title="mock_title")),
                                 content_type="application/json")
        conversation_id = response.get_json()["_id"]
        response = self.app.delete("/conversations/{conversation_id}".format(
            conversation_id=conversation_id))
        self.assertEqual(response.status_code, 200)
        conversation = Conversation.objects.first()
        self.assertEqual(conversation, None)
    
    @mock.patch.object(auth, 'verify_id_token')
    @mock.patch.object(messaging, 'send', return_value=None)
    def test_create_message(self, send, verify_id_token):
        from firebase_admin import messaging
        messaging.send = lambda x: x  # set mock function to messaging.send
        
        mock_time = pendulum.datetime(2020, 5, 21, 12)
        pendulum.set_test_now(mock_time)
        
        # insert user1
        verify_id_token.return_value = dict(uid=mock_user_1["uid"])
        create_user_1(self.app)
        
        # insert user2
        verify_id_token.return_value = dict(uid=mock_user_2["uid"])
        create_user_2(self.app)
        
        # open chat room with user1 and user2
        users = User.objects.all()
        user_1, user_2 = users[0], users[1]
        conversation = Conversation(
            title=None,
            participants=[user_1, user_2],
            references=[user_1, user_2],
            created_at=pendulum.now().int_timestamp).save()
        
        first_message = "first_message 1"
        second_message = "second_message 2"
        
        # insert message_1
        response = self.app.post("/conversations/{conversation_id}/messages/{message}".format(
            conversation_id=conversation.id, message=first_message),
            headers=dict(uid=user_1.uid),
            content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        
        # insert message_2
        response = self.app.post("/conversations/{conversation_id}/messages/{message}".format(
            conversation_id=conversation.id, message=second_message),
            headers=dict(uid=user_1.uid),
            content_type='application/json')
        
        self.assertEqual(response.status_code, 200)
        
        conversation = Conversation.objects.first()
        
        # assert embedded_messages
        messages = conversation.messages
        self.assertEqual(len(messages), 2)
        self.assertEqual(str(messages[0].user_id), str(user_1.id))
        self.assertEqual(messages[0].message, first_message)
        self.assertEqual(str(messages[1].user_id), str(user_1.id))
        self.assertEqual(messages[1].message, second_message)
        

    @mock.patch.object(auth, 'verify_id_token')
    @mock.patch.object(messaging, 'send', return_value=None)
    def test_get_conversation(self, send, verify_id_token):
        # insert user1
        verify_id_token.return_value = dict(uid=mock_user_1["uid"])
        create_user_1(self.app)
        
        # insert user2
        verify_id_token.return_value = dict(uid=mock_user_2["uid"])
        create_user_2(self.app)
        
        # open chat room with user1 and user2
        users = User.objects.all()
        user_1, user_2 = users[0], users[1]
        conversation = Conversation(
            title=None,
            participants=[user_1, user_2],
            references=[user_1, user_2],
            created_at=pendulum.now().int_timestamp).save()
        
        self.app.post("/conversations/{conversation_id}/messages/test_message_1".format(
            conversation_id=conversation.id), headers=dict(uid=user_1.uid))
        
        self.app.post("/conversations/{conversation_id}/messages/test_message_2".format(
            conversation_id=conversation.id), headers=dict(uid=user_2.uid))
        
        self.app.post("/conversations/{conversation_id}/messages/test_message_3".format(
            conversation_id=conversation.id), headers=dict(uid=user_1.uid))
        
        response = self.app.get("/conversations/{conversation_id}".format(
            conversation_id=conversation.id), headers=dict(uid=user_1.uid))
        conversation: dict = response.get_json()
        
        embedded_messages = conversation.get("messages")
        
        # checks embedded messages
        self.assertEqual(len(embedded_messages), 3)
        self.assertEqual(embedded_messages[0]["message"], "test_message_1")
        self.assertEqual(embedded_messages[0]["user_id"], str(user_1.id))
        self.assertEqual(embedded_messages[1]["message"], "test_message_2")
        self.assertEqual(embedded_messages[1]["user_id"], str(user_2.id))
        self.assertEqual(embedded_messages[2]["message"], "test_message_3")
        self.assertEqual(embedded_messages[2]["user_id"], str(user_1.id))
        
        participants = conversation.get("participants")
        
        # checks room members
        self.assertEqual(participants[0]["nickname"], user_1.nickname)
        self.assertEqual(participants[1]["nickname"], user_2.nickname)


if __name__ == "__main__":
    unittest.main()

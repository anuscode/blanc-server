import firebase_admin
import io
import os
import mock
import unittest

from mongoengine import connect, disconnect
from app import create_app
from app import init_firebase
from blueprints.test.mock_data import *
from blueprints.test.test_utils import create_user_1, create_user_2, create_user_3

from config import UnitTestConfig
from model.models import Post, Comment, User

from firebase_admin import auth
from firebase_admin import messaging


class PostsBlueprintTestCase(unittest.TestCase):
    
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
    
    def ping_to_create_post(self, user=mock_user_1,
                            title="mock_title", description="hello world"):
        # read file and send to server.
        file_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "testdata/nyan.png")
        
        # insert post1
        with open(file_dir, "rb") as image:
            b = bytearray(image.read())
            response = self.app.post(
                "/posts",
                data=dict(title=title, description=description,
                          post_image=(io.BytesIO(b), "test.jpg")),
                headers=dict(uid=user["uid"]),
                follow_redirects=False,
                content_type="multipart/form-data")
        return response
    
    @mock.patch.object(auth, 'verify_id_token', return_value=dict(uid=mock_user_1["uid"]))
    def test_create_post(self, verify_id_token):
        """Checks to create a post properly."""
        # insert user then create post
        create_user_1(self.app)
        response = self.ping_to_create_post(user=mock_user_1)
        post = Post.objects().first()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(post["title"], "mock_title")
        self.assertEqual(post["description"], "hello world")
        resources = post["resources"]
        self.assertRegex(resources[0]["url"], "https://storage.googleapis.com/.*")
        self.assertRegex(resources[0]["type"], "IMAGE")
    
    @mock.patch.object(auth, 'verify_id_token', return_value=dict(uid=mock_user_1["uid"]))
    def test_get_post(self, verify_id_token):
        """Checks to retrieve a post properly."""
        # insert user then create post
        create_user_1(self.app)
        response = self.ping_to_create_post(
            user=mock_user_1, title="mock_title",
            description="test_description")
        
        self.assertEqual(response.status_code, 200)
        
        created_post_id = response.get_json()["_id"]
        
        # ping to get post
        response = self.app.get("/posts/{pid}".format(pid=str(created_post_id)))
        post: dict = response.get_json()
        author: dict = post["author"]
        
        self.assertEqual(post["title"], "mock_title")
        self.assertEqual(post["description"], "test_description")
        resources = post["resources"]
        self.assertRegex(resources[0]["url"], "https://storage.googleapis.com.*")
        self.assertRegex(resources[0]["type"], "IMAGE")
        
        self.assertEqual(author.get("uid", None), None)
        self.assertEqual(author["nickname"], mock_user_1["nickname"])
        self.assertEqual(author["sex"], mock_user_1["sex"])
        self.assertEqual(author["birthed_at"], mock_user_1["birthed_at"])
        self.assertEqual(author["height"], mock_user_1["height"])
        self.assertEqual(author["body_id"], mock_user_1["body_id"])
        self.assertEqual(author["occupation"], mock_user_1["occupation"])
        self.assertEqual(author["education"], mock_user_1["education"])
        self.assertEqual(author["religion_id"], mock_user_1["religion_id"])
        self.assertEqual(author["drink_id"], mock_user_1["drink_id"])
        self.assertEqual(author["smoking_id"], mock_user_1["smoking_id"])
        self.assertEqual(author["blood_id"], mock_user_1["blood_id"])
        self.assertEqual(author["device_token"], mock_user_1["device_token"])
        self.assertEqual(author["introduction"], mock_user_1["introduction"])
        self.assertEqual(author["last_login_at"], mock_user_1["last_login_at"])
        self.assertEqual(author["user_images"], [])
    
    @mock.patch.object(auth, 'verify_id_token')
    def test_route_list_posts(self, verify_id_token):
        """Checks to retrieve all posts properly."""
        
        # insert user then create post
        verify_id_token.return_value = dict(uid=mock_user_1["uid"])
        create_user_1(self.app)
        self.ping_to_create_post(
            user=mock_user_1, title="mock_title_1",
            description="test_description")
        
        # insert user then create post
        verify_id_token.return_value = dict(uid=mock_user_2["uid"])
        create_user_2(self.app)
        self.ping_to_create_post(
            user=mock_user_2, title="mock_title_2",
            description="test_description")
        
        # insert user then create post
        verify_id_token.return_value = dict(uid=mock_user_3["uid"])
        create_user_3(self.app)
        self.ping_to_create_post(
            user=mock_user_3, title="mock_title_3",
            description="test_description")
        
        response = self.app.get("/posts?page=0")
        posts = response.get_json()
        self.assertEqual(len(posts), 3)
    
    @mock.patch.object(auth, 'verify_id_token', return_value=dict(uid=mock_user_1["uid"]))
    @mock.patch.object(messaging, 'send', return_value=None)
    def test_route_list_posts_with_favorite(self, send, verify_id_token):
        """Checks if the response includes favorite_user_ids but not favorite_users."""
        # insert user then create post
        create_user_1(self.app)
        self.ping_to_create_post(
            user=mock_user_1, title="mock_title_1",
            description="test_description")
        
        post = Post.objects.first()
        
        # create favorite
        self.app.post("/posts/{pid}/favorite".format(
            pid=post.id), headers=dict(uid=mock_user_1["uid"]))
        
        response = self.app.get("/posts?page=0")
        posts = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(posts[0]["favorite_user_ids"]), 1)
    
    @mock.patch.object(auth, 'verify_id_token')
    @mock.patch.object(messaging, 'send', return_value=None)
    def test_create_favorite(self, send, verify_id_token):
        # create mock_user_1 and post_1
        
        verify_id_token.return_value = dict(uid=mock_user_1["uid"])
        create_user_1(self.app)
        response = self.ping_to_create_post(
            user=mock_user_1, title="mock_title_1",
            description="test_description")
        
        post = response.get_json()
        pid, uid = post["_id"], mock_user_1["uid"]
        
        # create favorite
        self.app.post("/posts/{pid}/favorite".format(pid=pid),
                      headers=dict(uid=mock_user_1["uid"]))
        
        # favorite must be created
        post_to_verify = Post.objects.first()
        favorite_user_ids = post_to_verify.favorite_user_ids
        self.assertEqual(len(favorite_user_ids), 1)
        
        # same user creates favorite again.
        self.app.post("/posts/{pid}/favorite".format(
            pid=pid), headers=dict(uid=mock_user_1["uid"]))
        
        # the number should be stayed because it"s a same user.
        post_to_verify = Post.objects.first()
        favorite_user_ids = post_to_verify.favorite_user_ids
        self.assertEqual(len(favorite_user_ids), 1)
        
        # create mock_user_2 for reference user.
        verify_id_token.return_value = dict(uid=mock_user_2["uid"])
        create_user_2(self.app)
        
        # another user creates favorite.
        self.app.post("/posts/{pid}/favorite".format(
            pid=pid), headers=dict(uid=mock_user_2["uid"]))
        
        # the number should be increased because it"s an another user.
        post_to_verify = Post.objects.first()
        self.assertEqual(len(post_to_verify.favorite_user_ids), 2)
    
    @mock.patch.object(auth, 'verify_id_token', return_value=dict(uid=mock_user_1["uid"]))
    @mock.patch.object(messaging, 'send', return_value=None)
    def test_delete_favorite(self, send, verify_id_token):
        # create mock_user_1 and post_1
        create_user_1(self.app)
        response = self.ping_to_create_post(
            user=mock_user_1, title="mock_title_1",
            description="test_description")
        
        post = response.get_json()
        pid, uid = post["_id"], mock_user_1["uid"]
        
        # create favorite
        self.app.post("/posts/{pid}/favorite".format(
            pid=pid), headers=dict(uid=mock_user_1["uid"]))
        
        # favorite must be created
        post_to_verify = Post.objects.first()
        favorite_user_ids = post_to_verify.favorite_user_ids
        self.assertEqual(len(favorite_user_ids), 1)
        
        # delete favorite back
        self.app.delete("/posts/{pid}/favorite".format(
            pid=pid), headers=dict(uid=mock_user_1["uid"]))
        
        # favorite must be created
        post_to_verify = Post.objects.first()
        favorite_user_ids = post_to_verify.favorite_user_ids
        self.assertEqual(len(favorite_user_ids), 0)
    
    @mock.patch.object(auth, 'verify_id_token')
    def test_create_comment(self, verify_id_token):
        verify_id_token.return_value = dict(uid=mock_user_1["uid"])
        create_user_1(self.app)
        response = self.ping_to_create_post(
            user=mock_user_1, title="mock_title_1", description="test_description")
        
        post = response.get_json()
        post_id, uid = post["_id"], mock_user_1["uid"]
        response = self.app.post("/posts/{post_id}/comments".format(
            post_id=post_id), headers=dict(uid=uid),
            data=dict(comment="create_comment_test"))
        
        self.assertEqual(response.status_code, 200)
        
        post = Post.objects.first()
        comment = post.comments[0]
        self.assertTrue(comment is not None)
        self.assertEqual(comment.comment, "create_comment_test")
    
    @mock.patch.object(auth, 'verify_id_token')
    def test_create_sub_comment(self, verify_id_token):
        verify_id_token.return_value = dict(uid=mock_user_1["uid"])
        create_user_1(self.app)
        verify_id_token.return_value = dict(uid=mock_user_2["uid"])
        create_user_2(self.app)
        
        response = self.ping_to_create_post(
            user=mock_user_1, title="mock_title_1", description="test_description")
        self.assertEqual(response.status_code, 200)
        
        post = response.get_json()
        post_id = post["_id"]
        
        # create comment
        response = self.app.post("/posts/{post_id}/comments?comment=create_comment_test".format(
            post_id=post_id), headers=dict(uid=mock_user_1["uid"]))
        self.assertEqual(response.status_code, 200)
        
        # create sub comment
        comment = Comment.objects.first()
        response = self.app.post("/posts/{post_id}/comments".format(
            post_id=post_id),
            headers=dict(uid=mock_user_1["uid"]),
            data=dict(comment="create_sub_comment_test",
                      comment_id=comment.id))
        self.assertEqual(response.status_code, 200)
        
        comment_to_verify = Comment.objects.first()
        sub_comment = comment_to_verify.comments[0]
        self.assertTrue(comment_to_verify is not None)
        self.assertEqual(len(comment_to_verify.comments), 1)
        self.assertEqual(sub_comment.comment, "create_sub_comment_test")
        
        # create sub comment2
        comment = Comment.objects.first()
        response = self.app.post("/posts/{post_id}/comments".format(
            post_id=post_id),
            headers=dict(uid=mock_user_2["uid"]),
            data=dict(comment="create_sub_comment_test2",
                      comment_id=comment.id))
        self.assertEqual(response.status_code, 200)
        
        comment_to_verify = Comment.objects.first()
        self.assertTrue(comment_to_verify is not None)
        self.assertEqual(len(comment_to_verify.comments), 2)
        self.assertEqual(comment_to_verify.comments[0].comment, "create_sub_comment_test")
        self.assertEqual(comment_to_verify.comments[1].comment, "create_sub_comment_test2")
    
    @mock.patch.object(auth, 'verify_id_token', return_value=dict(uid=mock_user_1["uid"]))
    @mock.patch.object(messaging, 'send', return_value=None)
    def test_create_thumb_up(self, send, verify_id_token):
        create_user_1(self.app)
        response = self.ping_to_create_post(
            user=mock_user_1, title="mock_title_1",
            description="test_description")
        
        post = response.get_json()
        post_id, uid = post["_id"], mock_user_1["uid"]
        
        # create comment
        response = self.app.post(
            "/posts/{post_id}/comments".format(
                post_id=post_id), headers=dict(uid=uid),
            data=dict(comment="create_comment_test"))
        
        comment = response.get_json()
        comment_id = comment["_id"]
        
        # thumb up.
        response = self.app.post("/posts/{post_id}/comments/{comment_id}/thumb_up".format(
            post_id=post_id, comment_id=comment_id), headers=dict(uid=uid))
        
        self.assertEqual(response.status_code, 200)
        
        comment_from_db = Comment.objects.first()
        user = User.objects.first()
        
        self.assertIn(user.id, comment_from_db.thumb_up_user_ids)
    
    @mock.patch.object(auth, 'verify_id_token', return_value=dict(uid=mock_user_1["uid"]))
    @mock.patch.object(messaging, 'send', return_value=None)
    def test_duplicate_create_thumb_up(self, send, verify_id_token):
        create_user_1(self.app)
        response = self.ping_to_create_post(
            user=mock_user_1, title="mock_title_1",
            description="test_description")
        
        post = response.get_json()
        post_id, uid = post["_id"], mock_user_1["uid"]
        
        # create comment
        response = self.app.post("/posts/{post_id}/comments".format(
            post_id=post_id), headers=dict(uid=uid),
            data=dict(comment="create_comment_test"))
        
        comment = response.get_json()
        comment_id = comment["_id"]
        
        # thumb up.
        response = self.app.post("/posts/{post_id}/comments/{comment_id}/thumb_up".format(
            post_id=post_id, comment_id=comment_id),
            headers=dict(uid=uid))
        
        self.assertEqual(response.status_code, 200)
        
        # thumb up again.
        response = self.app.post("/posts/{post_id}/comments/{comment_id}/thumb_up".format(
            post_id=post_id, comment_id=comment_id),
            headers=dict(uid=uid))
        
        self.assertEqual(response.status_code, 200)
        
        comment_from_db = Comment.objects.first()
        user = User.objects.first()
        
        self.assertEqual(len(comment_from_db.thumb_up_user_ids), 1)
        self.assertIn(user.id, comment_from_db.thumb_up_user_ids)
    
    @mock.patch.object(auth, 'verify_id_token')
    def test_create_thumb_down(self, verify_id_token):
        verify_id_token.return_value = dict(uid=mock_user_1["uid"])
        create_user_1(self.app)
        response = self.ping_to_create_post(
            user=mock_user_1, title="mock_title_1",
            description="test_description")
        
        post = response.get_json()
        post_id, uid = post["_id"], mock_user_1["uid"]
        
        # create comment
        response = self.app.post("/posts/{post_id}/comments".format(
            post_id=post_id), headers=dict(uid=uid),
            data=dict(comment="create_comment_test"))
        
        comment = response.get_json()
        comment_id = comment["_id"]
        
        # thumb down.
        response = self.app.post("/posts/{post_id}/comments/{comment_id}/thumb_down".format(
            post_id=post_id, comment_id=comment_id),
            headers=dict(uid=uid))
        
        self.assertEqual(response.status_code, 200)
        
        comment_from_db = Comment.objects.first()
        user = User.objects.first()
        
        self.assertIn(user.id, comment_from_db.thumb_down_user_ids)
    
    @mock.patch.object(auth, 'verify_id_token')
    def test_duplicate_create_thumb_down(self, verify_id_token):
        verify_id_token.return_value = dict(uid=mock_user_1["uid"])
        create_user_1(self.app)
        response = self.ping_to_create_post(
            user=mock_user_1, title="mock_title_1",
            description="test_description")
        
        post = response.get_json()
        post_id, uid = post["_id"], mock_user_1["uid"]
        
        # create comment
        response = self.app.post("/posts/{post_id}/comments".format(
            post_id=post_id), headers=dict(uid=uid),
            data=dict(comment="create_comment_test"))
        
        comment = response.get_json()
        comment_id = comment["_id"]
        
        # thumb down.
        response = self.app.post("/posts/{post_id}/comments/{comment_id}/thumb_down".format(
            post_id=post_id, comment_id=comment_id),
            headers=dict(uid=uid))
        
        self.assertEqual(response.status_code, 200)
        
        # create thumb down.
        response = self.app.post("/posts/{post_id}/comments/{comment_id}/thumb_down".format(
            post_id=post_id, comment_id=comment_id),
            headers=dict(uid=uid))
        
        self.assertEqual(response.status_code, 200)
        
        comment_from_db = Comment.objects.first()
        user = User.objects.first()
        
        self.assertEqual(len(comment_from_db.thumb_down_user_ids), 1)
        self.assertIn(user.id, comment_from_db.thumb_down_user_ids)
    
    @mock.patch.object(auth, 'verify_id_token')
    @mock.patch.object(messaging, 'send', return_value=None)
    def test_delete_thumb_up(self, send, verify_id_token):
        verify_id_token.return_value = dict(uid=mock_user_1["uid"])
        create_user_1(self.app)
        response = self.ping_to_create_post(
            user=mock_user_1, title="mock_title_1",
            description="test_description")
        
        post = response.get_json()
        post_id, uid = post["_id"], mock_user_1["uid"]
        
        # create comment
        response = self.app.post("/posts/{post_id}/comments".format(
            post_id=post_id), headers=dict(uid=uid),
            data=dict(comment="create_comment_test"))
        
        comment = response.get_json()
        comment_id = comment["_id"]
        
        # create thumb up.
        response = self.app.post("/posts/{post_id}/comments/{comment_id}/thumb_up".format(
            post_id=post_id, comment_id=comment_id),
            headers=dict(uid=uid))
        
        self.assertEqual(response.status_code, 200)
        
        # delete thumb up.
        response = self.app.delete("/posts/{post_id}/comments/{comment_id}/thumb_up".format(
            post_id=post_id, comment_id=comment_id),
            headers=dict(uid=uid))
        
        # asserts response
        self.assertEqual(response.status_code, 200)
        
        # asserts db
        comment_from_db = Comment.objects.first()
        self.assertEqual(
            len(comment_from_db.thumb_up_user_ids), 0)
    
    @mock.patch.object(auth, 'verify_id_token')
    def test_delete_thumb_down(self, verify_id_token):
        verify_id_token.return_value = dict(uid=mock_user_1["uid"])
        create_user_1(self.app)
        response = self.ping_to_create_post(
            user=mock_user_1, title="mock_title_1",
            description="test_description")
        
        post = response.get_json()
        post_id, uid = post["_id"], mock_user_1["uid"]
        
        # create comment
        response = self.app.post("/posts/{post_id}/comments".format(
            post_id=post_id), headers=dict(uid=uid),
            data=dict(comment="create_comment_test"))
        
        comment = response.get_json()
        comment_id = comment["_id"]
        
        # create thumb down.
        response = self.app.post("/posts/{post_id}/comments/{comment_id}/thumb_down".format(
            post_id=post_id, comment_id=comment_id),
            headers=dict(uid=uid))
        
        self.assertEqual(response.status_code, 200)
        
        # delete thumb down.
        response = self.app.delete("/posts/{post_id}/comments/{comment_id}/thumb_down".format(
            post_id=post_id, comment_id=comment_id),
            headers=dict(uid=uid))
        
        # asserts response
        self.assertEqual(response.status_code, 200)
        
        # asserts db
        comment_from_db = Comment.objects.first()
        self.assertEqual(len(comment_from_db.thumb_down_user_ids), 0)


if __name__ == "__main__":
    unittest.main()

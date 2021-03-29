import firebase_admin
import json
import os
import pendulum
import unittest
import io
import mock

from mongoengine import connect, disconnect
from app import create_app
from app import init_firebase

from blueprints.test.mock_data import *
from blueprints import users_blueprint
from blueprints.test.test_utils import create_user_1, create_user_2, create_user_3

from config import UnitTestConfig
from model.models import User, StarRating, Recommendation, Contact, Setting

from firebase_admin import auth
from firebase_admin import messaging


class UsersBlueprintTestCase(unittest.TestCase):

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
    def test_create_user(self, verify_id_token):
        verify_id_token.return_value = dict(uid=mock_user_1.get("uid"))
        response = create_user_1(self.app)
        user = User.objects().first()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(user.uid, mock_user_1.get("uid"))

    @mock.patch.object(auth, 'verify_id_token')
    def test_update_user(self, verify_id_token):
        verify_id_token.return_value = dict(uid=mock_user_1["uid"])
        # insert user only with uid.
        create_user_1(self.app)

        updated_user = User.objects().first()

        self.assertEqual(updated_user["uid"], mock_user_1["uid"])
        self.assertEqual(updated_user["nickname"], mock_user_1["nickname"])
        self.assertEqual(updated_user["sex"], mock_user_1["sex"])
        self.assertEqual(updated_user["birthed_at"], mock_user_1["birthed_at"])
        self.assertEqual(updated_user["height"], mock_user_1["height"])
        self.assertEqual(updated_user["body_id"], mock_user_1["body_id"])
        self.assertEqual(updated_user["occupation"], mock_user_1["occupation"])
        self.assertEqual(updated_user["education"], mock_user_1["education"])
        self.assertEqual(updated_user["religion_id"], mock_user_1["religion_id"])
        self.assertEqual(updated_user["drink_id"], mock_user_1["drink_id"])
        self.assertEqual(updated_user["smoking_id"], mock_user_1["smoking_id"])
        self.assertEqual(updated_user["blood_id"], mock_user_1["blood_id"])
        self.assertEqual(updated_user["device_token"], 'cPFFTaZTQ2ivAN-bAmxNI5:APA91bFsgmm')
        self.assertEqual(updated_user["introduction"], mock_user_1["introduction"])
        self.assertEqual(updated_user["last_login_at"], mock_user_1["last_login_at"])
        self.assertEqual(len(updated_user["charm_ids"]), len(mock_user_1["charm_ids"]))
        self.assertEqual(len(updated_user["ideal_type_ids"]), len(mock_user_1["ideal_type_ids"]))
        self.assertEqual(len(updated_user["interest_ids"]), len(mock_user_1["interest_ids"]))

    @mock.patch.object(auth, 'verify_id_token')
    def test_override_user_list_type_values(self, verify_id_token):

        # insert user only with uid.
        verify_id_token.return_value = dict(uid=mock_user_1["uid"])
        response = create_user_1(self.app)

        self.assertEqual(response.status_code, 200)

        # assert first update results.
        updated_user = User.objects().first()
        self.assertEqual(len(updated_user["charm_ids"]), len(mock_user_1["charm_ids"]))
        self.assertEqual(len(updated_user["ideal_type_ids"]), len(mock_user_1["ideal_type_ids"]))
        self.assertEqual(len(updated_user["interest_ids"]), len(mock_user_1["interest_ids"]))

        # test for overriding list type values
        mock_user_1["charm_ids"] = mock_user_2["charm_ids"]
        mock_user_1["ideal_type_ids"] = mock_user_2["ideal_type_ids"]
        mock_user_1["interest_ids"] = mock_user_2["interest_ids"]

        response = self.app.put("/users/{user_id}/profile".format(user_id=str(updated_user.id)),
                                data=json.dumps(mock_user_1),
                                headers=dict(uid=mock_user_1["uid"]),
                                content_type="application/json")
        updated_user = User.objects().first()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(updated_user["charm_ids"]), len(mock_user_1["charm_ids"]))
        self.assertEqual(len(updated_user["ideal_type_ids"]), len(mock_user_1["ideal_type_ids"]))
        self.assertEqual(len(updated_user["interest_ids"]), len(mock_user_1["interest_ids"]))

    @mock.patch.object(auth, 'verify_id_token')
    def test_get_user(self, verify_id_token):
        # insert user1
        verify_id_token.return_value = dict(uid=mock_user_1["uid"])
        response_1 = create_user_1(self.app)

        id_1 = response_1.get_json()["_id"]

        # insert user2
        verify_id_token.return_value = dict(uid=mock_user_2["uid"])
        response_2 = create_user_2(self.app)

        id_2 = response_2.get_json()["_id"]

        response_user_1 = self.app.get("/users/{uid}".format(uid=id_1))
        response_user_2 = self.app.get("/users/{uid}".format(uid=id_2))

        user_1 = response_user_1.get_json()
        user_2 = response_user_2.get_json()

        for key, value in mock_user_1.items():
            if key not in ["uid", "device_token", "user_images", "location", "joined_at", "phone"]:
                self.assertEqual(user_1[key], value)

        for key, value in mock_user_2.items():
            if key not in ["uid", "device_token", "user_images", "location", "joined_at", "phone"]:
                self.assertEqual(user_2[key], value)

    @mock.patch.object(auth, 'verify_id_token', return_value=dict(uid=mock_user_1["uid"]))
    def test_update_image(self, verify_id_token):
        """Checks for an update of an image that already exists.."""
        # mock_user_1 has images.
        uid = mock_user_1.get("uid")
        image_index_to_update = 2

        # insert user
        create_user_1(self.app)

        user = User.objects.first()
        user.update(user_images=[], user_images_temp=[])

        # read file and send to server.
        file_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "testdata/nyan.png")

        with open(file_dir, "rb") as image:
            file = image.read()
            b = bytearray(file)
            response = self.app.post(
                "/users/{user_id}/user_images/{index}".format(user_id=str(user.id), index=0),
                headers=dict(uid=uid),
                data=dict(user_image=(io.BytesIO(b), "test.jpg")),
                follow_redirects=False,
                content_type="multipart/form-data"
            )
            response = self.app.post(
                "/users/{user_id}/user_images/{index}".format(user_id=str(user.id), index=1),
                headers=dict(uid=uid),
                data=dict(user_image=(io.BytesIO(b), "test.jpg")),
                follow_redirects=False,
                content_type="multipart/form-data"
            )
            response = self.app.post(
                "/users/{user_id}/user_images/{index}".format(user_id=str(user.id), index=2),
                headers=dict(uid=uid),
                data=dict(user_image=(io.BytesIO(b), "test.jpg")),
                follow_redirects=False,
                content_type="multipart/form-data"
            )

        # retrieve it again and check
        user = User.objects(uid=uid).first()
        user_images_temp = user.user_images_temp

        updated_image_temp = user_images_temp[image_index_to_update]
        original_image = mock_user_1["user_images"][image_index_to_update]

        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(original_image["url"], updated_image_temp["url"])
        self.assertEqual(user.available, False)
        self.assertEqual(user.status, "OPENED")

    @mock.patch.object(auth, 'verify_id_token', return_value=dict(uid=mock_user_1["uid"]))
    def test_delete_image(self, verify_id_token):
        """Checks for deletion of an image that already exists.."""

        # mock_user_1 has images.
        uid = mock_user_1.get("uid")

        # insert user
        response = create_user_1(self.app)
        user = response.get_json()

        # read file and send to server.
        file_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "testdata/nyan.png")

        with open(file_dir, "rb") as image:
            file = image.read()
            b = bytearray(file)
            response = self.app.post("/users/{user_id}/user_images/{index}".format(
                user_id=user["_id"], index=0),
                headers=dict(uid=uid),
                data=dict(user_image=(io.BytesIO(b), "test.jpg")),
                follow_redirects=False,
                content_type="multipart/form-data")
            self.assertEqual(response.status_code, 200)

            response = self.app.post("/users/{user_id}/user_images/{index}".format(
                user_id=user["_id"], index=1),
                headers=dict(uid=uid),
                data=dict(user_image=(io.BytesIO(b), "test.jpg")),
                follow_redirects=False,
                content_type="multipart/form-data")
            self.assertEqual(response.status_code, 200)

            response = self.app.post("/users/{user_id}/user_images/{index}".format(
                user_id=user["_id"], index=2),
                headers=dict(uid=uid),
                data=dict(user_image=(io.BytesIO(b), "test.jpg")),
                follow_redirects=False,
                content_type="multipart/form-data")
            self.assertEqual(response.status_code, 200)

        # delete user image using index.
        response = self.app.delete(
            "/users/{user_id}/user_images/{index}".format(user_id=user["_id"], index=2),
            headers=dict(uid=uid),
            content_type="application/json")
        self.assertEqual(response.status_code, 200)

        user = User.objects.first()
        self.assertEqual(len(user.user_images_temp), 2)
        self.assertEqual(user.available, False)
        self.assertEqual(user.status, "OPENED")

    @mock.patch.object(auth, 'verify_id_token')
    def test_updated_image_images_pending_order(self, verify_id_token):
        """Checks for an update of an image that already exists.."""

        # mock_user_1 has images.
        uid = mock_user_1.get("uid")
        verify_id_token.return_value = dict(uid=uid)
        # insert user
        response = create_user_1(self.app)

        user = response.get_json()

        # read file and send to server.
        file_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "testdata/nyan.png")

        with open(file_dir, "rb") as image:
            file = image.read()
            b = bytearray(file)
            response_1 = self.app.post("/users/{user_id}/user_images/{index}".format(
                user_id=user["_id"], index=5),
                headers=dict(uid=uid),
                data=dict(user_image=(io.BytesIO(b), "test.jpg")),
                follow_redirects=False,
                content_type="multipart/form-data")
            response_2 = self.app.post("/users/{user_id}/user_images/{index}".format(
                user_id=user["_id"], index=4),
                headers=dict(uid=uid),
                data=dict(user_image=(io.BytesIO(b), "test.jpg")),
                follow_redirects=False,
                content_type="multipart/form-data")
            response_3 = self.app.post("/users/{user_id}/user_images/{index}".format(
                user_id=user["_id"], index=3),
                headers=dict(uid=uid),
                data=dict(user_image=(io.BytesIO(b), "test.jpg")),
                follow_redirects=False,
                content_type="multipart/form-data")

        # retrieve it again and check
        user = User.objects(uid=uid).first()

        self.assertEqual(response_1.status_code, 200)
        self.assertEqual(response_2.status_code, 200)
        self.assertEqual(response_3.status_code, 200)

        self.assertEqual(len(user.user_images_temp), 3)
        self.assertEqual(user.user_images_temp[0].index, 3)
        self.assertEqual(user.user_images_temp[1].index, 4)
        self.assertEqual(user.user_images_temp[2].index, 5)

    @mock.patch.object(auth, 'verify_id_token')
    def test_insert_image_pending(self, verify_id_token):
        """Checks for an insert of an new image.."""
        # mock_user_2 has no images.
        uid = mock_user_2.get("uid")
        index_to_test = 2

        # insert user
        verify_id_token.return_value = dict(uid=uid)
        response = create_user_2(self.app)
        self.assertEqual(response.status_code, 200)

        user = response.get_json()

        # read file and send to server.
        file_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "testdata/nyan.png")

        with open(file_dir, "rb") as image:
            file = image.read()
            b = bytearray(file)
            response = self.app.post("/users/{user_id}/user_images/{index}".format(
                user_id=user["_id"], index=index_to_test),
                data=dict(user_image=(io.BytesIO(b), "test.jpg")),
                headers=dict(uid=uid),
                follow_redirects=False,
                content_type="multipart/form-data"
            )

        user = User.objects(uid=uid).get_or_404()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(user.user_images_temp), 1)
        self.assertEqual(user.user_images_temp[0].index, index_to_test)
        self.assertRegex(user.user_images_temp[0].url, "https://storage.googleapis.com.*")

    @mock.patch.object(auth, 'verify_id_token', return_value=dict(uid=mock_user_1["uid"]))
    def test_update_registration_token(self, verify_id_token):
        # insert an user
        response = create_user_1(self.app)
        # update the user
        self.app.put("/users/device_token/{device_token}".format(
            device_token="updated_registration_token_value"),
            headers=dict(uid=mock_user_1["uid"]))

        user_1 = User.objects(uid=mock_user_1["uid"]).first()
        # registration_token must be updated.
        self.assertEqual(user_1.device_token, "updated_registration_token_value")

    @mock.patch.object(auth, 'verify_id_token', return_value=dict(uid=mock_user_1["uid"]))
    def test_list_user_posts(self, verify_id_token):
        # insert user_1
        response = create_user_1(self.app)

        user_1 = User.objects.first()

        # when nothing post found
        response = self.app.get("/users/{user_id}/posts".format(user_id=user_1.id))
        self.assertEqual(response.status_code, 200)

        # insert post1
        file_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "testdata/nyan.png")
        with open(file_dir, "rb") as image:
            b = bytearray(image.read())
            self.app.post("/posts",
                          data=dict(title="mock_title",
                                    description="mock_description",
                                    post_image=(io.BytesIO(b), "test.jpg")),
                          headers=dict(uid=mock_user_1["uid"]),
                          follow_redirects=False,
                          content_type="multipart/form-data")

        # when 1 post found
        response = self.app.get("/users/{user_id}/posts".format(
            user_id=user_1.id))
        posts = response.get_json()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(posts[0]["title"], "mock_title")
        self.assertEqual(posts[0]["description"], "mock_description")
        resources = posts[0]["resources"]
        self.assertRegex(resources[0]["url"], "https://storage.googleapis.com/.*")
        self.assertRegex(resources[0]["type"], "IMAGE")

    @mock.patch.object(auth, 'verify_id_token')
    @mock.patch.object(messaging, 'send', return_value=None)
    def test_poke(self, mock_send, verify_id_token):
        # insert user_1
        verify_id_token.return_value = dict(uid=mock_user_1["uid"])
        response_1 = create_user_1(self.app)

        # insert user_2
        verify_id_token.return_value = dict(uid=mock_user_2["uid"])
        response_2 = create_user_2(self.app)

        user_from = response_1.get_json()
        user_from = User.objects.get_or_404(id=user_from["_id"])
        user_to = response_2.get_json()
        user_to = User.objects.get_or_404(id=user_to["_id"])

        # user_1 pokes user_2
        poke_response = self.app.post("/users/{uid_to}/push/poke".format(
            uid_to=str(user_to.id)),
            headers=dict(uid=user_from["uid"]))
        self.assertEqual(poke_response.status_code, 200)
        self.assertEqual(mock_send.call_count, 1)

    @mock.patch.object(auth, 'verify_id_token')
    def test_user_images_approval(self, verify_id_token):

        uid = mock_user_1.get("uid")

        verify_id_token.return_value = dict(uid=uid)
        response_1 = create_user_1(self.app)

        user = response_1.get_json()

        # read file and send to server.
        file_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "testdata/nyan.png")

        with open(file_dir, "rb") as image:
            file = image.read()
            b = bytearray(file)

            response = self.app.post(
                "/users/{user_id}/user_images/{index}".format(user_id=user["_id"], index=0),
                headers=dict(uid=uid),
                data=dict(user_image=(io.BytesIO(b), "test.jpg")),
                follow_redirects=False,
                content_type="multipart/form-data")
            self.assertEqual(response.status_code, 200)

            response = self.app.post(
                "/users/{user_id}/user_images/{index}".format(user_id=user["_id"], index=1),
                headers=dict(uid=uid),
                data=dict(user_image=(io.BytesIO(b), "test.jpg")),
                follow_redirects=False,
                content_type="multipart/form-data")
            self.assertEqual(response.status_code, 200)

            response = self.app.post(
                "/users/{user_id}/user_images/{index}".format(user_id=user["_id"], index=2),
                headers=dict(uid=uid),
                data=dict(user_image=(io.BytesIO(b), "test.jpg")),
                follow_redirects=False,
                content_type="multipart/form-data")
            self.assertEqual(response.status_code, 200)

        # retrieve it again and check
        user = User.objects(uid=uid).first()
        self.assertEqual(len(user.user_images), 0)
        self.assertEqual(len(user.user_images_temp), 3)

        response = self.app.put("/users/{user_id}/status/approval".format(
            user_id=str(user.id)))

        user = User.objects(uid=uid).first()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(user.user_images), 3)
        self.assertEqual(len(user.user_images_temp), 3)

        for index, _ in enumerate(user.user_images):
            self.assertEqual(user.user_images[index], user.user_images_temp[index])

    @mock.patch.object(auth, 'verify_id_token')
    def test_update_location(self, mock_verify_id_token):
        # insert user_1
        mock_verify_id_token.return_value = dict(uid=mock_user_1["uid"])
        response_1 = create_user_1(self.app)
        self.assertEqual(response_1.status_code, 200)

        user = response_1.get_json()

        location_response = self.app.put(
            "/users/{user_id}/location?longitude=127.07256&latitude=35.78125".format(user_id=user["_id"]),
            headers=dict(uid=mock_user_1["uid"]))
        self.assertEqual(location_response.status_code, 200)

        user = User.objects.first()
        coordinates = user.location.get("coordinates")
        self.assertEqual(coordinates, [127.07256, 35.78125])

        if __name__ == "__main__":
            unittest.main()

    @mock.patch.object(users_blueprint, 'get_coordinates_by_ip', return_value=[127.07256, 35.78125])
    @mock.patch.object(auth, 'verify_id_token')
    def test_update_location_by_ip(
            self, mock_verify_id_token, mock_get_coordinates_by_ip):
        # insert user_1
        mock_verify_id_token.return_value = dict(uid=mock_user_1["uid"])
        response_1 = create_user_1(self.app)
        self.assertEqual(response_1.status_code, 200)

        user = response_1.get_json()

        location_response = self.app.put("/users/{user_id}/location".format(
            user_id=user["_id"]),
            headers=dict(uid=mock_user_1["uid"]),
            content_type="application/json")

        self.assertEqual(location_response.status_code, 200)

        user = User.objects.first()
        coordinates = user.location.get("coordinates")
        self.assertEqual(coordinates, [127.07256, 35.78125])

    @mock.patch.object(auth, 'verify_id_token')
    @mock.patch.object(messaging, 'send', return_value=None)
    def test_update_star_rating_score(self, mock_send, mock_verify_id_token):
        # insert user_1
        mock_verify_id_token.return_value = dict(uid=mock_user_1["uid"])
        response = create_user_1(self.app)

        self.assertEqual(response.status_code, 200)

        # insert user_2
        mock_verify_id_token.return_value = dict(uid=mock_user_2["uid"])
        response = create_user_2(self.app)

        self.assertEqual(response.status_code, 200)

        # user 1 rates score to user 2
        user_id = str(User.objects(uid=mock_user_2["uid"]).first().id)
        response = self.app.put(
            "/users/{user_id}/score/{score}".format(
                user_id=user_id, score=5),
            headers=dict(uid=mock_user_1["uid"]),
            content_type="application/json")
        self.assertEqual(response.status_code, 200)

        rate = StarRating.objects.first()

        self.assertEqual(rate.user_from.uid, mock_user_1["uid"])
        self.assertEqual(rate.user_to.uid, mock_user_2["uid"])
        self.assertEqual(rate.score, 5)

    @mock.patch.object(auth, 'verify_id_token')
    def test_list_user_recommendation(self, mock_verify_id_token):
        """There must not be recommended users because anotehr users contacts contain my number."""
        mock_time = pendulum.datetime(2020, 5, 21, 12)
        pendulum.set_test_now(mock_time)

        # insert user_1
        mock_verify_id_token.return_value = dict(uid=mock_user_1["uid"])
        response_1 = create_user_1(self.app)
        self.assertEqual(response_1.status_code, 200)
        # insert user_2
        mock_verify_id_token.return_value = dict(uid=mock_user_2["uid"])
        response_2 = create_user_2(self.app)
        self.assertEqual(response_2.status_code, 200)

        User.objects(uid=mock_user_1["uid"]).update(available=True)
        User.objects(uid=mock_user_2["uid"]).update(available=True)

        response = self.app.get("/users/{user_id}/recommendation".format(
            user_id=response_1.get_json().get("_id")),
            headers=dict(uid=mock_user_1["uid"]),
            content_type="application/json")

        self.assertEqual(response.status_code, 500)
        recommendation = Recommendation.objects.first()
        self.assertEqual(len(recommendation.user_ids), 0)

    @mock.patch.object(auth, 'verify_id_token')
    def test_list_user_recommendation_blocked_by_contacts1(self, mock_verify_id_token):
        """There must not be recommended users because my contacts number contains there number."""
        mock_time = pendulum.datetime(2020, 5, 21, 12)
        pendulum.set_test_now(mock_time)

        # insert user_1
        mock_verify_id_token.return_value = dict(uid=mock_user_1["uid"])
        response_1 = create_user_1(self.app)
        self.assertEqual(response_1.status_code, 200)
        # insert user_2
        mock_verify_id_token.return_value = dict(uid=mock_user_2["uid"])
        response_2 = create_user_2(self.app)
        self.assertEqual(response_2.status_code, 200)

        User.objects(uid=mock_user_1["uid"]).update(available=True)
        User.objects(uid=mock_user_2["uid"]).update(available=True)

        user_1 = User.objects(uid=mock_user_1["uid"]).first()
        user_2 = User.objects(uid=mock_user_2["uid"]).first()
        Contact(owner=user_1, phones=[user_2.phone],
                last_updated_at=pendulum.now().int_timestamp).save()

        response = self.app.get("/users/{user_id}/recommendation".format(
            user_id=response_1.get_json().get("_id")),
            headers=dict(uid=mock_user_1["uid"]),
            content_type="application/json")

        self.assertEqual(response.status_code, 500)
        recommendation = Recommendation.objects.first()
        self.assertEqual(len(recommendation.user_ids), 0)

    @mock.patch.object(auth, 'verify_id_token')
    def test_list_user_recommendation_block_by_contacts2(self, mock_verify_id_token):
        """There must not be recommended users because anotehr users contacts contain my number."""
        mock_time = pendulum.datetime(2020, 5, 21, 12)
        pendulum.set_test_now(mock_time)

        # insert user_1
        mock_verify_id_token.return_value = dict(uid=mock_user_1["uid"])
        response_1 = create_user_1(self.app)
        self.assertEqual(response_1.status_code, 200)
        # insert user_2
        mock_verify_id_token.return_value = dict(uid=mock_user_2["uid"])
        response_2 = create_user_2(self.app)
        self.assertEqual(response_2.status_code, 200)

        User.objects(uid=mock_user_1["uid"]).update(available=True)
        User.objects(uid=mock_user_2["uid"]).update(available=True)

        user_1 = User.objects(uid=mock_user_1["uid"]).first()
        user_2 = User.objects(uid=mock_user_2["uid"]).first()
        Contact(owner=user_2, phones=[user_1.phone],
                last_updated_at=pendulum.now().int_timestamp).save()

        response = self.app.get("/users/{user_id}/recommendation".format(
            user_id=response_1.get_json().get("_id")),
            headers=dict(uid=mock_user_1["uid"]),
            content_type="application/json")

        self.assertEqual(response.status_code, 500)
        recommendation = Recommendation.objects.first()
        self.assertEqual(len(recommendation.user_ids), 0)

    @mock.patch.object(auth, 'verify_id_token')
    def test_list_users_within_distance(self, mock_verify_id_token):
        """There must not be recommended users because anotehr users contacts contain my number."""
        mock_time = pendulum.datetime(2020, 5, 21, 12)
        pendulum.set_test_now(mock_time)

        # insert user_1
        mock_verify_id_token.return_value = dict(uid=mock_user_1["uid"])
        response_1 = create_user_1(self.app)
        self.assertEqual(response_1.status_code, 200)
        # insert user_2
        mock_verify_id_token.return_value = dict(uid=mock_user_2["uid"])
        response_2 = create_user_2(self.app)
        self.assertEqual(response_2.status_code, 200)

        User.objects(uid=mock_user_1["uid"]).update(available=True)
        User.objects(uid=mock_user_2["uid"]).update(available=True)

        user_1 = User.objects(uid=mock_user_1["uid"]).first()
        user_2 = User.objects(uid=mock_user_2["uid"]).first()
        Contact(owner=user_2, phones=[user_1.phone],
                last_updated_at=pendulum.now().int_timestamp).save()

        response = self.app.get("/users/{user_id}/distance/10".format(
            user_id=response_1.get_json().get("_id")),
            headers=dict(uid=mock_user_1["uid"]),
            content_type="application/json")

        self.assertEqual(response.status_code, 500)
        recommendation = Recommendation.objects.first()
        self.assertEqual(len(recommendation.user_ids), 0)

    @mock.patch.object(auth, 'verify_id_token')
    def test_list_real_time_users(self, mock_verify_id_token):
        """There must not be recommended users because anotehr users contacts contain my number."""
        mock_time = pendulum.datetime(2020, 5, 21, 12)
        pendulum.set_test_now(mock_time)

        # insert user_1
        mock_verify_id_token.return_value = dict(uid=mock_user_1["uid"])
        response_1 = create_user_1(self.app)
        self.assertEqual(response_1.status_code, 200)
        # insert user_2
        mock_verify_id_token.return_value = dict(uid=mock_user_2["uid"])
        response_2 = create_user_2(self.app)
        self.assertEqual(response_2.status_code, 200)

        User.objects(uid=mock_user_1["uid"]).update(available=True)
        User.objects(uid=mock_user_2["uid"]).update(available=True)

        user_1 = User.objects(uid=mock_user_1["uid"]).first()
        user_2 = User.objects(uid=mock_user_2["uid"]).first()

        response = self.app.get("/users/{user_id}/real_time".format(
            user_id=response_1.get_json().get("_id")),
            headers=dict(uid=mock_user_1["uid"]),
            content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.get_json()), 1)

        Contact.objects(owner=user_2).update(
            phones=[user_1.phone], last_updated_at=pendulum.now().int_timestamp)
        response = self.app.get("/users/{user_id}/real_time".format(
            user_id=response_1.get_json().get("_id")),
            headers=dict(uid=mock_user_1["uid"]),
            content_type="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.get_json()), 0)

    @mock.patch.object(auth, 'verify_id_token')
    def test_does_know_each_other1(self, mock_verify_id_token):
        """Should be True at least when one person has the others phone number."""
        mock_time = pendulum.datetime(2020, 5, 21, 12)
        pendulum.set_test_now(mock_time)

        # insert user_1
        mock_verify_id_token.return_value = dict(uid=mock_user_1["uid"])
        response_1 = create_user_1(self.app)
        self.assertEqual(response_1.status_code, 200)
        # insert user_2
        mock_verify_id_token.return_value = dict(uid=mock_user_2["uid"])
        response_2 = create_user_2(self.app)
        self.assertEqual(response_2.status_code, 200)

        user_1 = User.objects(uid=mock_user_1["uid"]).first()
        user_2 = User.objects(uid=mock_user_2["uid"]).first()
        Contact(owner=user_2, phones=[user_1.phone],
                last_updated_at=pendulum.now().int_timestamp).save()

        does_know_1 = user_1.does_know_each_other(user_2)
        does_know_2 = user_2.does_know_each_other(user_1)
        self.assertEqual(does_know_1, True)
        self.assertEqual(does_know_2, True)

    @mock.patch.object(auth, 'verify_id_token')
    def test_does_know_each_other2(self, mock_verify_id_token):
        """Should be True at least when one person has the others phone number."""
        mock_time = pendulum.datetime(2020, 5, 21, 12)
        pendulum.set_test_now(mock_time)

        # insert user_1
        mock_verify_id_token.return_value = dict(uid=mock_user_1["uid"])
        response_1 = create_user_1(self.app)
        self.assertEqual(response_1.status_code, 200)
        # insert user_2
        mock_verify_id_token.return_value = dict(uid=mock_user_2["uid"])
        response_2 = create_user_2(self.app)
        self.assertEqual(response_2.status_code, 200)

        user_1 = User.objects(uid=mock_user_1["uid"]).first()
        user_2 = User.objects(uid=mock_user_2["uid"]).first()
        Contact(owner=user_1, phones=[user_2.phone],
                last_updated_at=pendulum.now().int_timestamp).save()

        does_know_1 = user_1.does_know_each_other(user_2)
        does_know_2 = user_2.does_know_each_other(user_1)
        self.assertEqual(does_know_1, True)
        self.assertEqual(does_know_2, True)

    @mock.patch.object(auth, 'verify_id_token')
    def test_get_push_setting(self, mock_verify_id_token):
        """Should return push setting json response."""
        mock_time = pendulum.datetime(2020, 5, 21, 12)
        pendulum.set_test_now(mock_time)

        # insert user_1
        mock_verify_id_token.return_value = dict(uid=mock_user_1["uid"])
        response_1 = create_user_1(self.app)
        self.assertEqual(response_1.status_code, 200)

        response = self.app.get("/users/{user_id}/setting/push".format(
            user_id=response_1.get_json().get("_id")),
            headers=dict(uid=mock_user_1["uid"]),
            content_type="application/json")

        data = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(data.get("poke"), True)
        self.assertEqual(data.get("request"), True)
        self.assertEqual(data.get("comment"), True)
        self.assertEqual(data.get("high_rate"), True)
        self.assertEqual(data.get("match"), True)
        self.assertEqual(data.get("favorite_comment"), True)
        self.assertEqual(data.get("conversation"), True)
        self.assertEqual(data.get("lookup"), True)

    @mock.patch.object(auth, 'verify_id_token')
    def test_update_push_setting(self, mock_verify_id_token):
        """Should return push setting json response."""
        mock_time = pendulum.datetime(2020, 5, 21, 12)
        pendulum.set_test_now(mock_time)

        # insert user_1
        mock_verify_id_token.return_value = dict(uid=mock_user_1["uid"])
        response_1 = create_user_1(self.app)
        self.assertEqual(response_1.status_code, 200)

        response = self.app.put("/users/{user_id}/setting/push".format(
            user_id=response_1.get_json().get("_id")),
            data=json.dumps(dict(
                poke=True,
                request=False,
                comment=True,
                high_rate=False,
                match=True,
                favorite_comment=True,
                conversation=False,
                lookup=True
            )),
            headers=dict(uid=mock_user_1["uid"]),
            content_type="application/json")

        setting = Setting.objects.first()
        push_setting = setting.push

        self.assertEqual(response.status_code, 200)
        self.assertEqual(push_setting.poke, True)
        self.assertEqual(push_setting.request, False)
        self.assertEqual(push_setting.comment, True)
        self.assertEqual(push_setting.high_rate, False)
        self.assertEqual(push_setting.match, True)
        self.assertEqual(push_setting.favorite_comment, True)
        self.assertEqual(push_setting.conversation, False)
        self.assertEqual(push_setting.lookup, True)

if __name__ == "__main__":
    unittest.main()

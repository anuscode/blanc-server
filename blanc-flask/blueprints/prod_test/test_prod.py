import unittest
import pendulum

from app import create_app, init_firebase
# from blueprints.users_blueprint import _geo_query_users
from config import RemoteProdConfig
from firebase_admin import auth
from model.models import Post, Comment, User, StarRating, Conversation, Request, Alarm
from model.models import Contact
from shared.json_encoder import encode

# 126.98265075683594, 37.56100082397461
dldyddn0624_uid = "AVZlVCmIXlWHy9ibTcLFT9b6YK02"
pink_gongdu_uid = "GxM4qD1jPMUo80TrrGHx9JI4OnO2"


class ProdPerformanceTestCase(unittest.TestCase):

    def setUp(self) -> None:
        app = create_app(RemoteProdConfig)
        app.app_context().push()
        self.app = app.test_client()

    def test_phone_query_performance(self):
        user = User.objects(uid=dldyddn0624_uid).first()
        start = pendulum.now().int_timestamp
        contact = Contact.objects(owner=user).first()
        phone_users = User.objects(phone__in=contact.phones).only("id").all()
        user_ids = set([str(user.id) for user in phone_users])
        end = pendulum.now().int_timestamp
        elapsed = end - start
        print(elapsed)
        self.assertEqual(elapsed < 1, True)
        self.assertEqual(len(user_ids), 505)

    def test_within_query_performance(self):
        user = User.objects(uid="GxM4qD1jPMUo80TrrGHx9JI4OnO2").first()

        start = pendulum.now().int_timestamp
        nin_ids = user._get_nin_ids()
        result = user._geo_query_users(nin_ids, max_diameter=30)
        end = pendulum.now().int_timestamp

        elapsed = end - start

        self.assertEqual(elapsed < 1, True)
        self.assertEqual(len(result), 2)

    def test_geo_query_users_with_5000_nin_performance(self):
        user = User.objects(uid="GxM4qD1jPMUo80TrrGHx9JI4OnO2").first()
        random_result = User.objects.aggregate([{'$sample': {'size': 5000}}])
        random_ids = [str(user.get("_id")) for user in random_result]
        start = pendulum.now().int_timestamp
        queried_users = user._geo_query_users(
            random_ids, min_diameter=0, max_diameter=299)
        end = pendulum.now().int_timestamp
        elapsed = end - start
        self.assertEqual(elapsed < 1, True)
        for queried_user in queried_users:
            print(queried_user.to_json())

    def test_get_nin_ids_performance(self):
        user = User.objects(id="5f89b9b12d83e5da90ae6993").first()
        start = pendulum.now().timestamp()
        nin_ids = user._get_nin_ids()
        end = pendulum.now().timestamp()
        elapsed = end - start
        self.assertEqual(elapsed <= 1, True)
        print(nin_ids)

    def test_geo_query_users_performance(self):
        user = User.objects(id="5fa9220013459b237e6ce5d6").first()
        user._geo_query_users(nin_ids=[])

    def test_list_users_close_performance(self):
        user = User.objects(id="5f89b9b12d83e5da90ae6993").first()
        self.app.get("/users/{user_id}/close".format(user_id=str(user.id)),
                     headers=dict(uid=user.uid))

    def test_create_requests2(self):
        user = User.objects(id="5fceb2824192080326d089fb").first()
        random_users = User.objects.aggregate([{'$sample': {'size': 10}}])
        for random_user in random_users:
            Request(
                user_from=random_user.get("_id"),
                user_to=user.id,
                requested_at=1602139074).save()

    def test_user_look_up(self):
        self.app.post("/users/{user_id}/push/lookup".format(
            user_id="5f953b8afa57d31f717d31a9"),
            headers=dict(uid="GxM4qD1jPMUo80TrrGHx9JI4OnO2"),
            content_type='application/json')

    def test_recommend(self):
        random_users = User.objects.aggregate([{'$sample': {'size': 1000}}])
        user = User.objects.get_or_404(id="5f89b9b12d83e5da90ae6993")
        for random_user in random_users:
            if not Request.objects(user_from=random_user.get("_id")).first():
                Request(
                    user_from=random_user.get("_id"),
                    user_to=str(user.id),
                    requested_at=pendulum.now().int_timestamp).save()  # .save()  # .save()

    def test_star_rating(self):
        import random
        random_users = User.objects.aggregate([{'$sample': {'size': 10}}])
        user = User.objects.get_or_404(id="5fceb2824192080326d089fb")
        for random_user in random_users:
            StarRating(
                user_from=random_user.get("_id"),
                user_to=str(user.id),
                rated_at=pendulum.now().int_timestamp,
                score=random.randrange(4, 5)).save()  # .save()  # .save()

    def test_ping_star_rating(self):
        # self.app.get("/users/{user_id}/score".format(
        #     user_id="5f89b9b12d83e5da90ae6993"),
        #     headers=dict(uid="ENi4hk7ynjU7YRO6HzTc51WM4qt2"),
        #     content_type='application/json')
        import json
        user = User.objects(id="5f89b9b12d83e5da90ae6993").first()
        users = user.list_users_rated_me()

        print(len(users))

    def test_iteration(self):
        users = User.objects.limit(500).all()
        start = pendulum.now().int_timestamp
        result = []
        for user in users:
            result.append(user.to_json())
        end = pendulum.now().int_timestamp
        elapsed = end - start
        print(elapsed)
        print(len(result))

    def test_create_requests(self):
        import json
        user = User.objects(id="602ebbae11062b9a8edabb0a").first()
        requests = user.list_requests_to_me()
        start = pendulum.now().int_timestamp

        key = "user_from"

        _requests = []
        _ids = []

        for req in requests:
            req = req.to_mongo()
            subject_id = req.get(key, None)
            _ids.append(subject_id)
            _requests.append(req)

        users = User.objects(id__in=_ids).all()

        hash_index = dict()
        for user in users:
            _id = str(user.id)
            hash_index[_id] = user.to_mongo()

        for req in _requests:
            req[key] = hash_index[req.get(key)]

        end = pendulum.now().int_timestamp
        elapsed = end - start
        print(elapsed)

    def test_list_conversations_performance(self):
        user = User.objects(id="5f89b9b12d83e5da90ae6993").first()
        response = self.app.get(
            "/conversations", headers=dict(uid=user.uid))
        print(response)

    def test_google_api(self):
        from googleapiclient import discovery
        from google.oauth2 import service_account
        credentials = service_account.Credentials.from_service_account_file(
            '/home/yongwoo/IdeaProjects/blanc-python/service_keys/play_console_service_account.json'
        )

        service = discovery.build("androidpublisher", "v3", credentials=credentials)
        result = service.purchases().products().get(
            packageName="com.ground.blanc",
            productId="5000won",
            token="mhfpngfookmbkckmpdlojklm.AO-J1OxjRyFdA6l8LBrFUxW8BXKgiOSBuPgFdKJwzV2xBVi4vyaa0sm8urvA6tJW8Xchok9aXze-i6o3s4frl2xhdkdumLt5_Q"
        ).execute()
        print(result)

    def test_test(self):
        hojin_id = "5faa48e3181d410288943c88"
        hojin = User.objects(id=hojin_id).first()

        hojin.update(last_login_at=pendulum.now().int_timestamp)

        user = User.objects(id="5fa18ff392ccc8049e8766fd").first()
        print(user)
        nin_ids = user._get_nin_ids()
        users = User.objects(
            location__near=user.location["coordinates"],
            location__max_distance=5 * 1000,  # 5 km
            last_login_at__gte=pendulum.now().int_timestamp - (60 * 30),
            available=True,
            id__nin=nin_ids,
            sex="M"
        ).as_pymongo()

        ids = user._get_nin_ids()

        for _id in ids:
            if str(_id) == hojin_id:
                print(_id)

        for u in users:
            if str(u["_id"]) == hojin_id:
                print(u.to_json())

    def test_create_conversations(self):
        user = User.objects.get_or_404(id="5fa18ff392ccc8049e8766fd")
        conversations = Conversation.objects.all()
        for c in conversations:
            if user.id not in [p.id for p in c.participants]:
                c.participants.append(user.id)
                c.save()

    def test_update_user_images(self):
        import random
        user = User.objects(id="5fa18ff392ccc8049e8766fd").first()
        user_image_url = [
            'https://storage.googleapis.com/pingme-287514.appspot.com/user_images/shighJBNJxNoWmCQecqw1ESBWfv2_1_d1339d70-29f4-11eb-9fd3-42010ab2000b',
            'https://storage.googleapis.com/pingme-287514.appspot.com/user_images/shighJBNJxNoWmCQecqw1ESBWfv2_0_cc7d689c-29f4-11eb-beab-42010ab2000b',
            'https://storage.googleapis.com/pingme-287514.appspot.com/user_images/shighJBNJxNoWmCQecqw1ESBWfv2_3_db39bf7a-29f4-11eb-9dee-42010ab2000b',
            'https://storage.googleapis.com/pingme-287514.appspot.com/user_images/shighJBNJxNoWmCQecqw1ESBWfv2_5_f53af6b4-29f4-11eb-b45f-42010ab2000b',
            'https://storage.googleapis.com/pingme-287514.appspot.com/user_images/shighJBNJxNoWmCQecqw1ESBWfv2_2_d7661196-29f4-11eb-9ca2-42010ab2000b',
            'https://storage.googleapis.com/pingme-287514.appspot.com/user_images/shighJBNJxNoWmCQecqw1ESBWfv2_1_c5672c98-2a65-11eb-8e30-42010ab2000b',
            'https://storage.googleapis.com/pingme-287514.appspot.com/user_images/shighJBNJxNoWmCQecqw1ESBWfv2_2_cbe1365e-2a65-11eb-8cbe-42010ab2000b',
            'https://storage.googleapis.com/pingme-287514.appspot.com/user_images/shighJBNJxNoWmCQecqw1ESBWfv2_3_d0842ca2-2a65-11eb-9d84-42010ab2000b',
            'https://storage.googleapis.com/pingme-287514.appspot.com/user_images/shighJBNJxNoWmCQecqw1ESBWfv2_4_d6f4a2ba-2a65-11eb-944a-42010ab2000b',
            'https://storage.googleapis.com/pingme-287514.appspot.com/user_images/shighJBNJxNoWmCQecqw1ESBWfv2_5_de5d06c8-2a65-11eb-84ff-42010ab2000b',
            'https://storage.googleapis.com/pingme-287514.appspot.com/user_images/shighJBNJxNoWmCQecqw1ESBWfv2_0_ebda44be-2a65-11eb-b5a1-42010ab2000b',
            'https://storage.googleapis.com/pingme-287514.appspot.com/user_images/shighJBNJxNoWmCQecqw1ESBWfv2_1_f16bd71c-2a65-11eb-8cbe-42010ab2000b',
            'https://storage.googleapis.com/pingme-287514.appspot.com/user_images/shighJBNJxNoWmCQecqw1ESBWfv2_2_f8a22f9a-2a65-11eb-9ac8-42010ab2000b',
            'https://storage.googleapis.com/pingme-287514.appspot.com/user_images/shighJBNJxNoWmCQecqw1ESBWfv2_3_0572d012-2a66-11eb-9d84-42010ab2000b',
            'https://storage.googleapis.com/pingme-287514.appspot.com/user_images/shighJBNJxNoWmCQecqw1ESBWfv2_5_121a02cc-2a66-11eb-944a-42010ab2000b',
            'https://storage.googleapis.com/pingme-287514.appspot.com/user_images/shighJBNJxNoWmCQecqw1ESBWfv2_0_17a3b65c-2a66-11eb-9ac8-42010ab2000b'
        ]

        user_images = [image for image in user.user_images_temp]

        count = 0
        while True:
            count += 1
            print(count)
            random_users = User.objects(sex="M").only("id").aggregate([{'$sample': {'size': 5000}}])
            ids = [random_user["_id"] for random_user in random_users]
            random.shuffle(user_image_url)
            for index, image in enumerate(user_images):
                image.url = user_image_url[index]
            print(user_images[0].url)
            User.objects(id__in=ids).update(
                set__user_images=user_images, set__user_images_temp=user_images)

    def test_list_posts(self):
        posts = Post.objects.skip(2).limit(2).all()
        posts = Post.list_posts()
        response = list(posts)
        print(response)

        if __name__ == "__main__":
            unittest.main()

    def test_does_know_each_other(self):
        from model.models import Resource
        posts = Post.objects.all()
        for post in posts:
            if post.url is not None:
                post.resources.append(Resource(type="IMAGE", url=post.url))
                post.save()

        user1 = User.objects(id="6033ebb511062b6d1e495f1b").first()
        user2 = User.objects(id="6033eff011062b6d1e495f1f").first()
        result = user1.does_know_each_other(user2)
        print(result)

    def test_update_user_available(self):
        import requests

        # user = User.objects(uid="shighJBNJxNoWmCQecqw1ESBWfv2").first()
        url = 'http://127.0.0.1:5000/users/{user_id}/status/approval'.format(
            user_id=str("6033eff011062b6d1e495f1f")
        )
        headers = {
            "uid": "shighJBNJxNoWmCQecqw1ESBWfv2",
            'content-type': 'application/json'
        }
        response = requests.put(url, headers=headers)
        self.assertEqual(response.status_code, 200)

    def test_post_page(self):
        params = dict(id__lt="60218f0c11062b81bd9e28ca")
        posts = Post.objects(**params).order_by('-id').limit(20).all()

        # posts = Post.objects(id__max="").limit(10).all()
        #
        # for post in posts:
        #     print(post.created_at)

    def test_create_random_request_and_conversation(self):
        user = User.objects.get_or_404(id="603c103511062bc70dfd99f7")
        while True:
            random_result = User.objects.aggregate([{'$sample': {'size': 2}}])
            random_ids = [str(user.get("_id")) for user in random_result]
            users = User.objects(id__in=random_ids)
            Request(user_from=users[0], user_to=user,
                    requested_at=pendulum.now().int_timestamp).save()

        # start = pendulum.now().int_timestamp
        # queried_users = user._geo_query_users(
        #     random_ids, min_diameter=0, max_diameter=299)
        # end = pendulum.now().int_timestamp
        # elapsed = end - start
        # self.assertEqual(elapsed < 1, True)
        # for queried_user in queried_users:
        #     print(queried_user.to_json())

    def test_test(self):
        import requests
        user = User.objects.get_or_404(id="6033eff011062b6d1e495f1f")

        coordinates = [
            float(user.location["coordinates"][0] + 1),
            float(user.location["coordinates"][1] + 1)
        ]

        user.update(**dict(location=coordinates))
        url = 'http://127.0.0.1:5000/users/{user_id}/distance/10'.format(
            user_id=str(user.id)
        )
        headers = {
            "uid": user.uid,
            'content-type': 'application/json'
        }
        response = requests.get(url, headers=headers)
        print(response)

    def test_verification_ios(self):
        receipt = "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"
        from shared.purchase import decode_receipt

        result = decode_receipt(receipt)
        if result.status != 0:
            ValueError("Invalid purchase receipt..")

        purchases = result.receipt.in_app[0]
        print(result.receipt.in_app[0].product_id)

    def test_references(self):
        Conversation.objects.delete()
        # conversations = Conversation.objects().all()
        # for conversation in conversations:
        #     for message in conversation.messages:
        #         message.update()
        #

    def test_rename(self):
        update_qry = {"$rename": {"nick_name": "nickname"}}
        User.objects.update(__raw__=update_qry)

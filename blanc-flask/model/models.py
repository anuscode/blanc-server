# coding: utf-8

import hashlib
import flask_mongoengine as fm
import pendulum
import random
import mongoengine as db

from bson.objectid import ObjectId
from flask import abort
from flask import current_app as app
from shared.annotation import time_lapse
from shared.hash_service import sha256

ONE_YEAR_TO_SECONDS = 31556926

FREE_PASS_NEXT = 12
FREE_OPEN_NEXT = 24 * 3

# Set any default index options - see the full options list
INDEX_OPTS = {}
# Set the default value for if an index should be indexed in the background
INDEX_BACKGROUND = True
# A way to turn off a specific index for _cls.
INDEX_CLS = False
# When this is True (default), MongoEngine will ensure that the correct indexes exist in MongoDB
# each time a command is run. This can be disabled in systems where indexes are managed separately.
# Disabling this will improve performance.
AUTO_CREATE_INDEX = False


def _get_hash(user_id: str):
    today = str(pendulum.yesterday().date())
    hash_today = int(
        hashlib.sha1(
            today.encode("utf-8")).hexdigest(), 16) % 10 ** 8
    user_own_hash = int(
        hashlib.sha1(
            user_id.encode("utf-8")).hexdigest(), 16) % 10 ** 8
    return hash_today + user_own_hash


def _get_index_at(cursor, index):
    try:
        result = cursor[index]
        return result
    except IndexError as e:
        return None


class UserImage(db.EmbeddedDocument):
    index = db.IntField()
    url = db.StringField()


class User(db.Document):
    meta = {
        'strict': False,
        'queryset_class': fm.BaseQuerySet,
        'index_opts': INDEX_OPTS,
        'index_background': INDEX_BACKGROUND,
        'index_cls': INDEX_CLS,
        'auto_create_index': AUTO_CREATE_INDEX,
        'indexes': [
            # 'uid',
            # 'phone',
            # '-last_login_at',
            # (("location", "2dsphere"), '-birthed_at'),
            # (("location", "2dsphere"), '-birthed_at', '-star_rating_avg'),
        ]
    }

    class Status(object):
        OPENED = "OPENED"
        PENDING = "PENDING"
        APPROVED = "APPROVED"
        REJECTED = "REJECTED"
        BLOCKED = "BLOCKED"
        UNREGISTERED = "UNREGISTERED"

    uid = db.StringField()
    nickname = db.StringField()
    sex = db.StringField(choices=["M", "F"])
    birthed_at = db.LongField()
    height = db.IntField()
    body_id = db.IntField()
    occupation = db.StringField()
    education = db.StringField()
    religion_id = db.IntField()
    drink_id = db.IntField()
    smoking_id = db.IntField()
    blood_id = db.IntField()
    device_token = db.StringField()
    location = db.PointField()
    introduction = db.StringField()
    joined_at = db.LongField()
    last_login_at = db.LongField()
    job = db.StringField()
    area = db.StringField()
    phone = db.StringField(unique=True)

    user_images = db.SortedListField(db.EmbeddedDocumentField(UserImage), ordering="index")
    user_images_temp = db.SortedListField(db.EmbeddedDocumentField(UserImage), ordering="index")

    charm_ids = db.ListField(db.IntField())
    ideal_type_ids = db.ListField(db.IntField())
    interest_ids = db.ListField(db.IntField())

    available = db.BooleanField(default=False)
    status = db.StringField(choices=[
        Status.OPENED, Status.PENDING, Status.APPROVED, Status.REJECTED, Status.BLOCKED, Status.UNREGISTERED
    ])
    star_rating_avg = db.FloatField(default=0)

    free_pass_tokens = db.ListField(db.LongField(), default=[0, 0])
    free_open_tokens = db.ListField(db.LongField(), default=[0])

    is_phones_cached = False
    phones_cache = []

    def identify(self, request):
        uid = request.headers.get("uid", None)
        if self.uid != uid:
            raise abort(401)

    def list_posts(self) -> list:
        result = Post.list_posts(author=self.id, is_deleted=False)
        return result

    def list_requests_to_me(self, response=None):
        return Request.list_requests(user_to=self, response=response)

    def list_requests_from_me(self, response=None):
        return Request.list_requests(user_from=self, response=response)

    def list_conversations(self):
        return Conversation.objects(participants=self).all()

    def list_users_rated_me(self):
        star_ratings = StarRating.objects(user_to=self).order_by("-rated_at").as_pymongo()
        score_repository = {
            str(s.get("user_from")): dict(score=s.get("score", 0), rated_at=s.get("rated_at")) for s in star_ratings
        }
        raters = User.list(id__in=score_repository.keys()).as_pymongo()

        result = []
        for rater in raters:
            user_id = str(rater.get("_id"))
            o = score_repository.get(user_id)
            o["user"] = rater
            result.append(o)

        return result

    def list_users_rated_me_high(self):
        star_ratings = StarRating.objects(user_to=self, score__gte=4).order_by("-rated_at").as_pymongo()
        user_ids = [star_rating.get("user_from", None) for star_rating in star_ratings]
        users_dict = User.get_users_dict(set(user_ids))
        result = [users_dict.get(str(user_id)) for user_id in user_ids]
        return filter(lambda x: x, result)

    def list_users_i_rated_high(self):
        star_ratings = StarRating.objects(user_from=self, score__gte=4).order_by("-rated_at").as_pymongo()
        user_ids = [star_rating.get("user_to", None) for star_rating in star_ratings]
        users_dict = User.get_users_dict(set(user_ids))
        result = [users_dict.get(str(user_id)) for user_id in user_ids]
        return filter(lambda x: x, result)

    def get_recommendation(self):
        recommendation = Recommendation.objects(owner=self).first()
        if not recommendation:
            recommendation = Recommendation(
                owner=self, user_ids=[], last_recommended_at=pendulum.yesterday().int_timestamp
            )
            recommendation.save()
            recommendation.reload()
        return recommendation

    def get_first_image(self):
        return self.user_images[0].url if self.user_images else ""

    def remove_user_from_recommendation(self, user_to_remove):
        if not user_to_remove:
            raise ValueError("owner and target must be required value.")
        recommendation = Recommendation.objects(owner=self).first()
        if not recommendation:
            return
        for index, rec_user_id in enumerate(recommendation.user_ids):
            if rec_user_id == user_to_remove.id:
                del recommendation.user_ids[index]
                break
        recommendation.save()

    def get_current_amount_of_point(self):
        payments = Payment.objects(owner=self).all()
        amount_sum = 0
        for payment in payments:
            amount_sum += payment.amount
        return amount_sum

    def is_available_for_free_pass_token(self):
        token_min = min(self.free_pass_tokens)
        current_time = pendulum.now().int_timestamp
        delta = current_time - token_min
        return delta >= 0

    def consume_free_pass_token(self):
        tokens = list(self.free_pass_tokens)
        index = tokens.index(min(tokens))
        tokens[index] = pendulum.now().int_timestamp + FREE_PASS_NEXT * 60 * 60
        if len(tokens) != 2:
            tokens = [0, 0]
        self.update(free_pass_tokens=tokens)

    def is_available_for_free_open_token(self):
        token_min = min(self.free_open_tokens)
        current_time = pendulum.now().int_timestamp
        delta = current_time - token_min
        return delta >= 0

    def consume_free_open_token(self):
        tokens = list(self.free_open_tokens)
        index = tokens.index(min(tokens))
        tokens[index] = pendulum.now().int_timestamp + FREE_OPEN_NEXT * 60 * 60
        if len(tokens) != 1:
            tokens = [0]
        self.update(free_open_tokens=tokens)

    def consume(self, amount):
        if amount <= 0:
            raise ValueError("Illegal amount found. The amount must be bigger than 0.")

        total_amount = self.get_current_amount_of_point()
        if total_amount < amount:
            raise Exception(
                "Not enough balance..\n"
                "remaining amount: {total_amount}, amount to consume: {amount}".format(
                    total_amount=total_amount, amount=amount))

        Payment(
            owner=self,
            type="CONSUME",
            amount=(amount * -1),
            created_at=pendulum.now().int_timestamp
        ).save()

    def purchase(self,
                 platform=None,
                 order_id=None,
                 product_id=None,
                 amount=None,
                 created_at=None,
                 purchase_time_ms=None):

        if not product_id or amount <= 0 or not order_id or not created_at or not purchase_time_ms or not platform:
            raise ValueError("Illegal amount found. The amount must be bigger than 0.")

        existing = Payment.objects(order_id=order_id, purchase_time_ms=purchase_time_ms).first()
        if existing:
            return Payment.Result.DUPLICATE

        payment = Payment(
            owner=self,
            type="PURCHASE",
            platform=platform,
            order_id=order_id,
            product_id=product_id,
            amount=amount,
            created_at=int(created_at),
            purchase_time_ms=int(purchase_time_ms)
        )
        payment.save()

        return Payment.Result.PURCHASED

    def list_payments(self, to_json=False):
        if not to_json:
            return Payment.objects(owner=self).all()
        else:
            payments = Payment.objects(owner=self).as_pymongo()
            return list(payments)

    def set_contact(self, phones):
        contact = self.get_contact()
        contact.phones = phones
        contact.last_updated = pendulum.now().int_timestamp
        contact.save()
        contact.reload()
        return contact

    def add_user_knows_me(self, user):
        contact = self.get_contact()
        user_ids_know_me = contact.user_ids_know_me
        if user.id not in user_ids_know_me:
            contact.user_ids_know_me.append(user.id)
            contact.save()

    def get_contact(self):
        contact = Contact.objects(owner=self).first()
        if not contact:
            contact = Contact(
                owner=self,
                phones=[],
                last_updated_at=pendulum.now().int_timestamp)
            contact.save()
            contact.reload()
        return contact

    def get_phones(self):
        if self.is_phones_cached:
            return self.phones_cache
        contact = self.get_contact()
        self.phones_cache = contact.phones
        self.is_phones_cached = True
        return self.phones_cache

    def has_in_contacts(self, phone) -> bool:
        if not phone:
            return False
        phones = self.get_phones()
        return phone in phones

    def does_know_each_other(self, user):
        if self.has_in_contacts(user.phone):  # checks whether I know him
            return True
        if user.has_in_contacts(self.phone):  # checks whether he knows me
            return True
        return False

    def _get_nin_ids(self) -> set:

        app.logger.debug("collecting nin ids..")
        nin_ids = set()
        # nin with requests
        requests_to_me = Request.objects(user_to=self).as_pymongo()
        requests_from_me = Request.objects(user_from=self).as_pymongo()
        to_me_ids = [r["user_from"] for r in requests_to_me]
        from_me_ids = [r["user_to"] for r in requests_from_me]
        nin_ids.update(to_me_ids)
        nin_ids.update(from_me_ids)

        app.logger.debug("collected nin ids with requests..")

        # nin with recommendation
        recommendation = self.get_recommendation()
        recommendation = recommendation.to_mongo()
        rec_ids = [user_id for user_id in recommendation["user_ids"]]
        nin_ids.update(rec_ids)

        app.logger.debug("collected nin ids with recommendation..")

        # nin with contact
        contact = self.get_contact()
        know_ids = [user_id for user_id in contact.user_ids_know_me]
        nin_ids.update(know_ids)
        phones = contact.phones
        ids_in_contacts = User.list_only_user_ids(phone__in=phones)
        nin_ids.update(ids_in_contacts)

        app.logger.debug("collected nin ids with contacts phone numbers..")

        return nin_ids

    def list_recommended_user_ids(self, nin_ids: set = None, result=None,
                                  min_diameter=0, max_diameter=30,
                                  star_rating_avg=3.5):
        """Generates recommended users. If not found, recursively try it increasing diameter up to 300 km."""
        sex = next((s for s in ['M', 'F'] if s != self.sex))
        result = result or []
        nin_ids = nin_ids or self._get_nin_ids()

        location = self.location["coordinates"] if self.location else [127.0977517240413, 37.49880740259655]
        params = dict(
            location__near=location,
            location__min_distance=min_diameter * 1000,
            location__max_distance=max_diameter * 1000,
            birthed_at__gte=self.birthed_at - (12 * ONE_YEAR_TO_SECONDS),
            birthed_at__lte=self.birthed_at + (12 * ONE_YEAR_TO_SECONDS),
            star_rating_avg__gte=star_rating_avg,
            id__nin=nin_ids,
            available=True,
            sex=sex
        )

        if max_diameter > 300:
            return result

        app.logger.debug("collecting users with params: {0}..".format(str(params)))

        cursor = User.list(**params)

        index = 0
        while True:
            app.logger.debug("cursor is moving..")
            user = _get_index_at(cursor, index)

            if user is None:
                break

            if self.does_know_each_other(user):
                self.add_user_knows_me(user)
                user.add_user_knows_me(self)
                nin_ids.add(user.id)
                continue
            result.append(user.id)
            index += 1
            if len(result) >= 2:
                break

        if len(result) < 2:
            app.logger.debug("Not enough recommended user found.. collecting more")
            return self.list_recommended_user_ids(
                nin_ids, result=result, star_rating_avg=star_rating_avg * 0.9,
                min_diameter=max_diameter, max_diameter=max_diameter * 2)

        return result  # 126.98265075683594, 37.56100082397461

    def list_realtime_user_ids(self):
        nin_ids = self._get_nin_ids()
        sex = 'M' if self.sex == 'F' else 'F'
        last_login_at_gte = pendulum.now().int_timestamp - (60 * 30)
        params = dict(
            last_login_at__gte=last_login_at_gte,
            id__nin=nin_ids,
            sex=sex,
            available=True
        )

        cursor = User.objects(**params).order_by("-last_login_at")
        size = cursor.count()

        result = []
        for index in range(0, size):
            user = cursor[index]
            if self.does_know_each_other(user):
                self.add_user_knows_me(user)
                user.add_user_knows_me(self)
                continue
            result.append(user.id)
            if len(result) >= 10:
                break
        return result

    @time_lapse
    def list_user_ids_within_distance(self, distance=5):
        nin_ids = self._get_nin_ids()
        sex = 'M' if self.sex == 'F' else 'F'

        location = self.location["coordinates"] if self.location else [127.0936859, 37.505808]
        params = dict(
            location__near=location,
            location__max_distance=distance * 1000,  # 1000 = 1 km
            location__min_distance=0 * 1000,
            birthed_at__gte=self.birthed_at - (12 * ONE_YEAR_TO_SECONDS),
            birthed_at__lte=self.birthed_at + (12 * ONE_YEAR_TO_SECONDS),
            id__nin=nin_ids,
            sex=sex,
            available=True
        )

        user_ids = User.list_only_user_ids(**params)
        random.seed(_get_hash(str(self.id)) + 1)
        random.shuffle(user_ids)

        result = []
        for user_id in user_ids:
            user = User.get(id=user_id)
            if self.does_know_each_other(user):
                self.add_user_knows_me(user)
                user.add_user_knows_me(self)
                continue
            result.append(user.id)
            if len(result) >= 10:
                break

        return result

    @classmethod
    def excludes(cls):
        return [
            "uid",
            "joined_at",
            "user_images_temp",
            "free_pass_tokens",
            "free_open_tokens",
            "phone"
        ]

    @classmethod
    def get(cls, **kwargs):
        excludes = kwargs.get("excludes", User.excludes())
        return User.objects.exclude(*excludes).get_or_404(**kwargs)

    @classmethod
    def list(cls, **kwargs):
        users = User.objects(**kwargs).exclude(*User.excludes())
        return users

    @classmethod
    def get_users_dict(cls, user_ids: set):
        users = User.list(id__in=list(user_ids)).as_pymongo()
        return {str(user.get("_id")): user for user in users}

    @classmethod
    def get_verified_user(cls, user_id, request):
        uid = request.headers.get("uid", None)
        user = User.get(uid=uid)
        if user_id != str(user.id):
            abort(401)
        return user

    @classmethod
    @time_lapse
    def list_only_user_ids(cls, **kwargs):
        query = User.objects(**kwargs).only("id").as_pymongo()
        return [o["_id"] for o in query]

    def is_admin(self):
        admin = Admin.objects(user=self).first()
        return admin is not None

    def withdraw(self):
        unregister = Unregister(nickname=self.nickname, uid=self.uid, phone=self.phone, user=self)
        unregister.save()

        self.uid = None
        self.phone = None
        self.device_token = None
        self.user_images = []
        self.user_images_temp = []
        self.available = False
        self.status = User.Status.REJECTED
        self.nickname = "탈퇴 한 회원"
        self.save()

        Post.objects(author=self).delete()
        # Comment.objects(owner=user).delete()
        # Request.objects(user_from=user).delete()
        # Request.objects(user_to=user).delete()
        # StarRating.objects(user_from=user).delete()
        # StarRating.objects(user_to=user).delete()
        # Contact.objects(owner=user).delete()
        # Alarm.objects(owner=user).delete()


class Unregister(db.Document):
    meta = {
        'strict': False,
        'queryset_class': fm.BaseQuerySet,
        'index_opts': INDEX_OPTS,
        'index_background': INDEX_BACKGROUND,
        'index_cls': INDEX_CLS,
        'auto_create_index': AUTO_CREATE_INDEX,
    }
    uid = db.StringField()
    phone = db.StringField()
    nickname = db.StringField()
    user = db.ReferenceField(User)


class Comment(db.Document):
    meta = {
        'strict': False,
        'queryset_class': fm.BaseQuerySet,
        'index_opts': INDEX_OPTS,
        'index_background': INDEX_BACKGROUND,
        'index_cls': INDEX_CLS,
        'auto_create_index': AUTO_CREATE_INDEX,
        'indexes': ['post_id']
    }
    user_id = db.ObjectIdField(required=True)
    post_id = db.ObjectIdField(required=True)
    comment = db.StringField()
    comments = db.ListField(db.ReferenceField('self'), reverse_delete_rule=db.CASCADE)
    created_at = db.LongField(required=True)
    thumb_up_user_ids = db.ListField(db.ObjectIdField())
    thumb_down_user_ids = db.ListField(db.ObjectIdField())
    is_deleted = db.BooleanField(default=False)

    @classmethod
    def list_comments(cls, **kwargs):
        pipe_line = [{
            "$graphLookup": {
                "from": "comment",
                "startWith": "$comments",
                "connectFromField": "comments",
                "connectToField": "_id",
                "as": "children",
                "maxDepth": 2,
            }
        }, {
            "$project": {
                "user_id": 1,
                "comment": 1,
                "comments": "$children",
                "thumb_up_user_ids": 1,
                "thumb_down_user_ids": 1,
                "created_at": 1,
                "is_deleted": 1
            }
        }]
        aggregate = Comment.objects(**kwargs).aggregate(pipe_line)
        result = list(aggregate)
        result.sort(key=lambda x: x["created_at"], reverse=True)
        return result

    @classmethod
    def get_comments_dict(cls, comments=None, **kwargs):
        comments = comments or Comment.list_comments(**kwargs)
        comments_dict = {str(comment["_id"]): comment for comment in comments}
        return comments_dict

    @classmethod
    def collect_all_user_ids(cls, comments, collector: set = None):
        collector = collector or set()
        cls.travel_tree(comments, lambda x: collector.add(x["user_id"]))
        return collector

    @classmethod
    def swap_user_id_to_object(cls, comments, users_dict):
        def delegator(comment):
            comment["commenter"] = users_dict.get(str(comment["user_id"]), None)

        cls.travel_tree(comments, delegator)
        return comments

    @classmethod
    def travel_tree(cls, comments, delegator):
        for comment in comments:
            delegator(comment)
            if comment["comments"]:
                cls.travel_tree(comment["comments"], delegator)
        return comments


class Resource(db.EmbeddedDocument):
    type = db.StringField(choices=["IMAGE", "VIDEO"])
    url = db.StringField(required=True)


class Post(db.Document):
    meta = {
        'strict': False,
        'queryset_class': fm.BaseQuerySet,
        'index_opts': INDEX_OPTS,
        'index_background': INDEX_BACKGROUND,
        'index_cls': INDEX_CLS,
        'auto_create_index': AUTO_CREATE_INDEX,
        'indexes': ['author']
    }
    author = db.ReferenceField(User, required=True, reverse_delete_rule=db.CASCADE)
    author_sex = db.StringField(choices=["M", "F"])
    title = db.StringField()
    description = db.StringField()
    url = db.StringField()
    resources = db.EmbeddedDocumentListField(Resource)
    favorite_user_ids = db.ListField(db.ObjectIdField())
    comments = db.ListField(db.ReferenceField(Comment, reverse_delete_rule=db.CASCADE))
    created_at = db.LongField(required=True)
    enable_comment = db.BooleanField()
    is_deleted = db.BooleanField(default=False)

    @classmethod
    def create(cls,
               author=None,
               title=None,
               description=None,
               resources=None,
               created_at=None,
               enable_comment=None,
               is_deleted=False):

        post = Post(
            author=author,
            author_sex=author.sex,
            title=title,
            description=description,
            resources=resources,
            created_at=created_at,
            enable_comment=enable_comment,
            is_deleted=is_deleted
        )
        post.save()
        post.reload()
        return post

    @classmethod
    def list_posts(cls, limit=30, **kwargs):
        posts = Post.objects(**kwargs).order_by("-id") \
            .limit(limit).as_pymongo()

        user_ids = set()
        comment_ids = set()

        for post in posts:
            user_ids.add(post["author"])
            comment_ids.update(post["comments"])

        comments = Comment.list_comments(id__in=comment_ids)
        commenter_ids = Comment.collect_all_user_ids(comments)

        user_ids.update(commenter_ids)
        user_dicts = User.get_users_dict(user_ids)
        comments = Comment.swap_user_id_to_object(comments, user_dicts)
        comments_dict = Comment.get_comments_dict(comments)

        for post in posts:
            comments = post["comments"]
            hierarchy_comments = []
            for comment_id in comments:
                hierarchy_comments.append(comments_dict.get(str(comment_id), None))
            hierarchy_comments.sort(key=lambda x: x["created_at"], reverse=True)
            post["comments"] = hierarchy_comments
            post["author"] = user_dicts.get(str(post["author"]), None)

        return posts

    @classmethod
    def get_post(cls, **kwargs):
        post = Post.objects.get_or_404(**kwargs).to_mongo()

        # returns as hierarchy_comments
        comments = Comment.list_comments(id__in=post["comments"])
        # travels hierarchy structure and get all user ids.
        commenter_ids = Comment.collect_all_user_ids(comments)

        author_id = str(post["author"])
        user_ids = {author_id}
        user_ids.update(commenter_ids)
        users_dict = User.get_users_dict(user_ids)

        comments = Comment.swap_user_id_to_object(comments, users_dict)
        comments_dict = Comment.get_comments_dict(comments)

        post_comments = post["comments"]
        hierarchy_comments = []
        for comment_id in post_comments:
            hierarchy_comments.append(
                comments_dict.get(str(comment_id), None))
        hierarchy_comments.sort(key=lambda x: x["created_at"], reverse=True)
        post["comments"] = hierarchy_comments
        post["author"] = users_dict.get(author_id)

        return post

    def add_comment(self, comment, parent_id=None):
        if parent_id:
            exist = next((comment for comment in self.comments
                          if str(comment.id) == parent_id), None)
            if not exist:
                raise ValueError("Not found a valid comment.")
            comment_to_update = Comment.objects.get_or_404(id=parent_id)
            comment_to_update.update(push__comments=comment)
        else:
            self.update(push__comments=comment)


class Request(db.Document):
    meta = {
        'strict': False,
        'queryset_class': fm.BaseQuerySet,
        'index_opts': INDEX_OPTS,
        'index_background': INDEX_BACKGROUND,
        'index_cls': INDEX_CLS,
        'auto_create_index': AUTO_CREATE_INDEX,
        'indexes': ['user_from', 'user_to']
    }
    user_from = db.ReferenceField(User, required=True, reverse_delete_rule=db.CASCADE)
    user_to = db.ReferenceField(User, required=True, reverse_delete_rule=db.CASCADE)
    requested_at = db.LongField()
    request_type_id = db.IntField()
    response = db.IntField()
    responded_at = db.LongField()

    @classmethod
    def get(cls, **kwargs):
        _request = Request.objects.get_or_404(**kwargs).to_mongo()
        _request["user_to"] = User.get(id=_request["user_to"]).to_mongo()
        _request["user_from"] = User.get(id=_request["user_from"]).to_mongo()
        return _request

    @classmethod
    def list_requests(cls, **kwargs):
        requests = Request.objects(**kwargs).as_pymongo()
        requests = list(requests)

        user_ids = set()
        for _request in requests:
            user_ids.add(_request["user_to"])
            user_ids.add(_request["user_from"])

        user_index = User.get_users_dict(user_ids)

        result = []
        for _request in requests:
            _request["user_to"] = user_index.get(str(_request["user_to"]), None)
            _request["user_from"] = user_index.get(str(_request["user_from"]), None)
            if _request["user_to"] is not None and _request["user_from"] is not None:
                result.append(_request)

        return result


class StarRating(db.Document):
    meta = {
        'strict': False,
        'queryset_class': fm.BaseQuerySet,
        'index_opts': INDEX_OPTS,
        'index_background': INDEX_BACKGROUND,
        'index_cls': INDEX_CLS,
        'auto_create_index': AUTO_CREATE_INDEX,
        'indexes': ['user_from', 'user_to']
    }
    user_from = db.ReferenceField(User, required=True, reverse_delete_rule=db.CASCADE)
    user_to = db.ReferenceField(User, required=True, reverse_delete_rule=db.CASCADE)
    rated_at = db.LongField(required=True)
    score = db.IntField(required=True)


class EmbeddedMessage(db.EmbeddedDocument):
    meta = {
        'strict': False,
        'queryset_class': fm.BaseQuerySet,
    }
    # Document: _id, Embedded document: id.
    id = db.ObjectIdField(required=True, default=lambda: ObjectId())
    conversation_id = db.ObjectIdField()
    category = db.StringField(choices=["MESSAGE", "VOICE", "IMAGE", "VIDEO", "SYSTEM"], default="MESSAGE")
    url = db.StringField()
    user_id = db.ObjectIdField()
    message = db.StringField()
    created_at = db.LongField(required=True)


class Conversation(db.Document):
    meta = {
        'strict': False,
        'queryset_class': fm.BaseQuerySet,
        'index_opts': INDEX_OPTS,
        'index_background': INDEX_BACKGROUND,
        'index_cls': INDEX_CLS,
        'auto_create_index': AUTO_CREATE_INDEX,
        'indexes': ['participants']
    }
    title = db.StringField(max_length=500)
    participants = db.SortedListField(db.ReferenceField(User), reverse_delete_rule=db.CASCADE)
    references = db.ListField(db.ReferenceField(User), reverse_delete_rule=db.CASCADE)
    messages = db.EmbeddedDocumentListField(EmbeddedMessage)
    created_at = db.LongField(required=True)
    available = db.BooleanField(required=True, default=False)
    available_at = db.LongField()


class _Event(object):
    LOG_OUT = "LOG_OUT"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    BLOCKED = "BLOCKED"
    CONVERSATION = "CONVERSATION"
    POKE = "POKE"
    REQUEST = "REQUEST"
    COMMENT = "COMMENT"
    FAVORITE = "FAVORITE"
    MATCHED = "MATCHED"
    THUMB_UP = "THUMB_UP"
    CONVERSATION_OPEN = "CONVERSATION_OPEN"
    CONVERSATION_LEAVE = "CONVERSATION_LEAVE"
    LOOK_UP = "LOOK_UP"
    STAR_RATING = "STAR_RATING"


class AlarmRecord(db.EmbeddedDocument):
    meta = {
        'strict': False,
        'queryset_class': fm.BaseQuerySet
    }

    id = db.ObjectIdField(required=True, default=lambda: ObjectId())
    event = db.StringField(required=True, choices=[
        _Event.LOG_OUT,
        _Event.APPROVED,
        _Event.REJECTED,
        _Event.BLOCKED,
        _Event.CONVERSATION,
        _Event.POKE,
        _Event.REQUEST,
        _Event.COMMENT,
        _Event.FAVORITE,
        _Event.MATCHED,
        _Event.THUMB_UP,
        _Event.CONVERSATION_OPEN,
        _Event.CONVERSATION_LEAVE,
        _Event.LOOK_UP,
        _Event.STAR_RATING
    ])
    user_id = db.ObjectIdField()
    post_id = db.ObjectIdField()
    comment_id = db.ObjectIdField()
    request_id = db.ObjectIdField()
    conversation_id = db.ObjectIdField()
    message_id = db.ObjectIdField()  # ChatRoom@Message
    message = db.StringField()
    created_at = db.LongField(required=True)
    is_read = db.BooleanField()

    def as_dict(self, user: User = None):
        user = user or User.objects.get_or_404(id=self.user_id)

        event = self.event
        nickname = user.nickname or ""
        user_image = next(iter(user.user_images or []), None)
        image_url = user_image.url if user_image else ""

        push_id = self.id
        user_id = self.user_id
        post_id = self.post_id or ""
        comment_id = self.comment_id or ""
        request_id = self.request_id or ""
        message_id = self.message_id or ""
        conversation_id = self.conversation_id or ""

        message = self.message
        created_at = str(self.created_at)
        is_read = str(self.is_read)

        return dict(
            push_id=str(push_id),
            user_id=str(user_id),
            post_id=str(post_id),
            comment_id=str(comment_id),
            request_id=str(request_id),
            conversation_id=str(conversation_id),
            message_id=str(message_id),
            event=event,
            nickname=nickname,
            image_url=image_url,
            message=message,
            created_at=created_at,
            is_read=is_read
        )


class Alarm(db.Document):
    meta = {
        'strict': False,
        'queryset_class': fm.BaseQuerySet,
        'index_opts': INDEX_OPTS,
        'index_background': INDEX_BACKGROUND,
        'index_cls': INDEX_CLS,
        'auto_create_index': AUTO_CREATE_INDEX,
        'indexes': ['owner']
    }

    class Event(_Event):
        pass

    owner = db.ReferenceField(User, required=True, reverse_delete_rule=db.CASCADE, unique=True)
    records = db.SortedListField(db.EmbeddedDocumentField(AlarmRecord), ordering="created_at", reverse=True)

    @classmethod
    def create_alarm(cls,
                     event=None,
                     user_from=None,
                     user_to=None,
                     conversation=None,
                     post=None,
                     comment=None,
                     request=None,
                     message=None):

        current_time_stamp = pendulum.now().int_timestamp

        if not user_to or not user_from:
            raise Exception("Both user_from and user_to are required values.")

        alarm = Alarm.objects(owner=user_to).first()
        if not alarm:
            alarm = Alarm(owner=user_to).save()

        push = AlarmRecord(
            event=event,
            user_id=user_from.id,
            post_id=post.id if post else None,
            comment_id=comment.id if comment else None,
            request_id=request.id if request else None,
            conversation_id=conversation.id if conversation else None,
            message=message,
            created_at=current_time_stamp
        )

        alarm.records = alarm.records[:199]  # max 200
        alarm.records.append(push)
        alarm.save()

        return alarm


class Recommendation(db.Document):
    meta = {
        'strict': False,
        'queryset_class': fm.BaseQuerySet,
        'index_opts': INDEX_OPTS,
        'index_background': INDEX_BACKGROUND,
        'index_cls': INDEX_CLS,
        'auto_create_index': AUTO_CREATE_INDEX,
        'indexes': ['owner']
    }
    owner = db.ReferenceField(User, required=True, reverse_delete_rule=db.CASCADE, unique=True)
    user_ids = db.ListField(db.ObjectIdField())
    users = db.ListField(db.ReferenceField(User))
    last_recommended_at = db.LongField(required=True)


class Payment(db.Document):
    class Result(object):
        DUPLICATE = "DUPLICATE"
        INVALID = "INVALID"
        PURCHASED = "PURCHASED"

    meta = {
        'strict': False,
        'queryset_class': fm.BaseQuerySet,
        'index_opts': INDEX_OPTS,
        'index_background': INDEX_BACKGROUND,
        'index_cls': INDEX_CLS,
        'auto_create_index': AUTO_CREATE_INDEX,
        'indexes': ['owner']
    }
    owner = db.ReferenceField(User, required=True)
    order_id = db.StringField()
    product_id = db.StringField()
    type = db.StringField(required=True, choices=["PURCHASE", "CONSUME"])
    amount = db.IntField(required=True)  # PURCHASE: positive, CONSUME: negative
    platform = db.StringField()
    created_at = db.LongField(required=True)
    purchase_time_ms = db.LongField()


class Contact(db.Document):
    meta = {
        'strict': False,
        'queryset_class': fm.BaseQuerySet,
        'index_opts': INDEX_OPTS,
        'index_background': INDEX_BACKGROUND,
        'index_cls': INDEX_CLS,
        'auto_create_index': AUTO_CREATE_INDEX,
        'indexes': ['owner']
    }
    owner = db.ReferenceField(User, required=True, reverse_delete_rule=db.CASCADE, unique=True)
    phones = db.ListField(db.StringField(required=True))
    user_ids_know_me = db.ListField(db.ObjectIdField())
    last_updated_at = db.LongField(required=True)


class Admin(db.Document):
    meta = {
        'strict': False,
        'queryset_class': fm.BaseQuerySet,
        'index_opts': INDEX_OPTS,
        'index_background': INDEX_BACKGROUND,
        'index_cls': INDEX_CLS,
        'auto_create_index': AUTO_CREATE_INDEX,
        'indexes': []
    }

    uid = db.StringField(required=True, unique=True)
    user = db.ReferenceField(User, reverse_delete_rule=db.CASCADE, unique=True)
    available = db.BooleanField()


class Setting(db.Document):
    meta = {
        'strict': False,
        'queryset_class': fm.BaseQuerySet,
        'index_opts': INDEX_OPTS,
        'index_background': INDEX_BACKGROUND,
        'index_cls': INDEX_CLS,
        'auto_create_index': AUTO_CREATE_INDEX,
        'indexes': ['owner']
    }

    class Push(db.EmbeddedDocument):
        poke = db.BooleanField(default=True)
        request = db.BooleanField(default=True)
        comment = db.BooleanField(default=True)
        high_rate = db.BooleanField(default=True)
        match = db.BooleanField(default=True)
        favorite_comment = db.BooleanField(default=True)
        conversation = db.BooleanField(default=True)
        lookup = db.BooleanField(default=True)

        def set(self, push: dict):
            self.poke = push.get("poke", False)
            self.request = push.get("request", False)
            self.comment = push.get("comment", False)
            self.high_rate = push.get("high_rate", False)
            self.match = push.get("match", False)
            self.favorite_comment = push.get("favorite_comment", False)
            self.conversation = push.get("conversation", False)
            self.lookup = push.get("lookup", False)

    owner = db.ReferenceField(User, required=True, reverse_delete_rule=db.CASCADE, unique=True)
    push = db.EmbeddedDocumentField(Push, default=Push())


class Report(db.Document):
    meta = {
        'strict': False,
        'queryset_class': fm.BaseQuerySet,
        'index_opts': INDEX_OPTS,
        'index_background': INDEX_BACKGROUND,
        'index_cls': INDEX_CLS,
        'auto_create_index': AUTO_CREATE_INDEX,
        'indexes': []
    }
    reporter = db.ReferenceField(User, reverse_delete_rule=db.CASCADE, unique=True)
    reportee = db.ReferenceField(User, reverse_delete_rule=db.CASCADE, unique=True)
    description = db.StringField()
    reported_at = db.LongField(required=True)
    is_resolved = db.BooleanField(default=False)
    resolved_at = db.LongField()
    report_images = db.ListField(db.StringField())

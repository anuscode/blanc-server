import firebase_admin
import json
import io
import os
import random
import unittest
import uuid
import pendulum

from firebase_admin import auth
from app import create_app, init_firebase
from config import DevConfig
from model.models import Post, Comment, User, StarRating, Conversation, Request, Alarm
from model.models import Contact

phones = ["+821000000000",
          "+821020002736",
          "+821020073622",
          "+821020099682",
          "+821020122470",
          "+821020179875",
          "+821020229438",
          "+821020418935",
          "+821020440359",
          "+821020446420",
          "+821020463646",
          "+821020467724",
          "+821020586033",
          "+821020665331",
          "+821020865296",
          "+821021074714",
          "+821021389954",
          "+821022051161",
          "+821022063834",
          "+821022248396",
          "+821022320819",
          "+821022390205",
          "+821022393249",
          "+821022565339",
          "+821022999834",
          "+821023036898",
          "+821023038236",
          "+821023001208",
          "+821023005104",
          "+821023175798",
          "+821023779379",
          "+821023924728",
          "+821024030621",
          "+821024237760",
          "+821024330700",
          "+821024606304",
          "+821025051012",
          "+821025077146",
          "+821025364264",
          "+821025887205",
          "+821026641618",
          "+821026746039",
          "+821026831812",
          "+821026921378",
          "+821026918822",
          "+821027201754",
          "+821027274111",
          "+821027288713",
          "+821027305157",
          "+821027439948",
          "+821027463309",
          "+821027716590",
          "+821027989666",
          "+821028236900",
          "+821028421985",
          "+821028695679",
          "+821028858983",
          "+821028871522",
          "+821028904547",
          "+821029151707",
          "+821029564723",
          "+821029896158",
          "+821030006839",
          "+821030218631",
          "+821030557799",
          "+821030738088",
          "+821031070308",
          "+821031114620",
          "+821031387748",
          "+821031538929",
          "+821031602701",
          "+821031674352",
          "+821031811999",
          "+821031901876",
          "+821031986882",
          "+821032198118",
          "+821032235051",
          "+821032351103",
          "+821032725641",
          "+821032823203",
          "+821032857608",
          "+821032865102",
          "+821033022582",
          "+821033088941",
          "+821033113286",
          "+821033381826",
          "+821033484077",
          "+821033561298",
          "+821033581910",
          "+821033666272",
          "+821033750161",
          "+821033711910",
          "+821033818134",
          "+821033946755",
          "+821034429301",
          "+821034429301",
          "+821034599311",
          "+821034778048",
          "+821034962229",
          "+821035059641",
          "+821035135680",
          "+821035494323",
          "+821035500327",
          "+821035515726",
          "+821035556404",
          "+821035725455",
          "+821035757982",
          "+821036180139",
          "+821036625556",
          "+821036818162",
          "+821036862043",
          "+821036943003",
          "+821037073584",
          "+821037157411",
          "+821037206191",
          "+821037224506",
          "+821037261994",
          "+821037628004",
          "+821037680000",
          "+821037680917",
          "+821037746478",
          "+821037769087",
          "+821038007302",
          "+821038101123",
          "+821038223156",
          "+821038394222",
          "+821038575379",
          "+821038755423",
          "+821038756818",
          "+821039137411",
          "+821039191770",
          "+821039340630",
          "+821039964196",
          "+821040040876",
          "+821040133231",
          "+821040188007",
          "+821040274141",
          "+821040275355",
          "+821040484149",
          "+821040496575",
          "+821040575156",
          "+821040734535",
          "+821041159518",
          "+821041161910",
          "+821041407672",
          "+821041412834",
          "+821041548216",
          "+821041692255",
          "+821041725806",
          "+821041756797",
          "+821041783316",
          "+821041812660",
          "+821041863986",
          "+821041929727",
          "+821041919842",
          "+821042113777",
          "+821042551475",
          "+821042661061",
          "+821042981229",
          "+821043030140",
          "+821043141089",
          "+821043405787",
          "+821043550177",
          "+821043820314",
          "+821043813891",
          "+821044024544",
          "+821044211985",
          "+821044398284",
          "+821044415163",
          "+821044493352",
          "+821044813236",
          "+821044841002",
          "+821044872539",
          "+821045123531",
          "+821045179086",
          "+821045498856",
          "+821045694263",
          "+821045728705",
          "+821045811418",
          "+821045869599",
          "+821046210848",
          "+821046200236",
          "+821046301147",
          "+821046430728",
          "+821046526487",
          "+821046618631",
          "+821046955548",
          "+821046996165",
          "+821047020741",
          "+821047084904",
          "+821047248712",
          "+821047251482",
          "+821047252748",
          "+821047303243",
          "+821047384423",
          "+821047441807",
          "+821047626160",
          "+821047688871",
          "+821047697250",
          "+821047732919",
          "+821047737418",
          "+821047879081",
          "+821048153624",
          "+821048490458",
          "+821048802188",
          "+821049028258",
          "+821049180472",
          "+821049274443",
          "+821049343170",
          "+821049453578",
          "+821049481846",
          "+821050124560",
          "+821050557005",
          "+821050603262",
          "+821050952851",
          "+821050956660",
          "+821050960240",
          "+821051136378",
          "+821051240787",
          "+821051270848",
          "+821051632272",
          "+821051703887",
          "+821051755554",
          "+821051802954",
          "+821051909989",
          "+821052057672",
          "+821052135461",
          "+821052201840",
          "+821052285750",
          "+821052397387",
          "+821052401899",
          "+821052460855",
          "+821052491571",
          "+821052574887",
          "+821052610457",
          "+821052748773",
          "+821052938833",
          "+821052960224",
          "+821053243295",
          "+821053385224",
          "+821053692489",
          "+821053706932",
          "+821053707310",
          "+821053852214",
          "+821054295511",
          "+821054349923",
          "+821054449887",
          "+821054493061",
          "+821054498448",
          "+821054504045",
          "+821054559653",
          "+821054600024",
          "+821054770039",
          "+821055166558",
          "+821055315544",
          "+821055550441",
          "+821055795500",
          "+821055816798",
          "+821055838735",
          "+821055879293",
          "+821055975715",
          "+821056327060",
          "+821056563792",
          "+821056990962",
          "+821057559332",
          "+821057665798",
          "+821057793162",
          "+821058750725",
          "+821058828147",
          "+821062016489",
          "+821062162651",
          "+821062225753",
          "+821062288591",
          "+821062588876",
          "+821062588876",
          "+821062809532",
          "+821062888897",
          "+821062913462",
          "+821063190061",
          "+821063266542",
          "+821063274787",
          "+821063391663",
          "+821063523207",
          "+821063532094",
          "+821063657431",
          "+821063744423",
          "+821063894110",
          "+821064061275",
          "+821064087308",
          "+821064334958",
          "+821064445436",
          "+821064792678",
          "+821064809774",
          "+821064855385",
          "+821064959312",
          "+821065061348",
          "+821065105068",
          "+821065241149",
          "+821065258450",
          "+821065335923",
          "+821065417370",
          "+821065452867",
          "+821065506050",
          "+821065565265",
          "+821065695147",
          "+821065729292",
          "+821065756175",
          "+821066039997",
          "+821066184884",
          "+821066209010",
          "+821066330560",
          "+821066443411",
          "+821066488391",
          "+821066717071",
          "+821066989010",
          "+821067279293",
          "+821067470039",
          "+821067474431",
          "+821067584107",
          "+821067650988",
          "+821067683782",
          "+821067771384",
          "+821068123434",
          "+821068576527",
          "+821068717486",
          "+821071027872",
          "+821071116388",
          "+821071174482",
          "+821071186459",
          "+821071249961",
          "+821071670389",
          "+82107167142",
          "+821071733497",
          "+821071800326",
          "+821071950589",
          "+821072242841",
          "+821072460019",
          "+821072585329",
          "+821072878705",
          "+821072997997",
          "+821073435446",
          "+821073736580",
          "+821073761910",
          "+821073830523",
          "+821074086921",
          "+821074181325",
          "+821074308199",
          "+821074449417",
          "+821074455558",
          "+821074493487",
          "+821074735010",
          "+821074771445",
          "+821075104302",
          "+821075104302",
          "+821075157638",
          "+821075575856",
          "+821075630073",
          "+821075646150",
          "+821075791258",
          "+821075997529",
          "+821076001437",
          "+821076635150",
          "+821076761809",
          "+821077064016",
          "+821077078450",
          "+821077138600",
          "+821077349363",
          "+821077634915",
          "+821077667788",
          "+821079270084",
          "+821079405552",
          "+821080770346",
          "+821082335882",
          "+821083071300",
          "+821083080691",
          "+821083282848",
          "+821083307420",
          "+821083835131",
          "+821084060236",
          "+821084151012",
          "+821084489417",
          "+821084608270",
          "+821084632121",
          "+821084880147",
          "+821084991177",
          "+821085035959",
          "+821085198687",
          "+821085377797",
          "+821085555531",
          "+821085793988",
          "+821086294979",
          "+821086386165",
          "+821086665811",
          "+821086756502",
          "+821086790364",
          "+821086881713",
          "+821087071712",
          "+821087028524",
          "+821087156872",
          "+821087244677",
          "+821087575236",
          "+821087582644",
          "+821087627111",
          "+821087689272",
          "+821087750397",
          "+821087850178",
          "+821087920378",
          "+821087929250",
          "+821088283509",
          "+821088339975",
          "+821088450377",
          "+821088799933",
          "+821088848465",
          "+821088874378",
          "+821089181776",
          "+821089182215",
          "+821089389777",
          "+821089584787",
          "+821089589962",
          "+821089681911",
          "+821089898164",
          "+821089960529",
          "+821090284860",
          "+821090396587",
          "+821090497451",
          "+821090504548",
          "+821090526642",
          "+821090529998",
          "+821090649629",
          "+821090763867",
          "+821090786756",
          "+821090810638",
          "+821090869914",
          "+821090903354",
          "+821091257337",
          "+821091320067",
          "+821091457565",
          "+821091569387",
          "+821091601056",
          "+821091634333",
          "+821091654310",
          "+821091851233",
          "+821091996805",
          "+821092282882",
          "+821092290134",
          "+821092343431",
          "+821092509422",
          "+821092804031",
          "+821092927230",
          "+821093343039",
          "+821093354854",
          "+821093407171",
          "+821093435919",
          "+821093655421",
          "+821093793651",
          "+821093951514",
          "+821093989525",
          "+821094009268",
          "+821094213804",
          "+821094229663",
          "+821094479387",
          "+821094983045",
          "+821095079584",
          "+821095334921",
          "+821095415369",
          "+821095432015",
          "+821095885818",
          "+821096253545",
          "+821096557643",
          "+821096600410",
          "+821097202333",
          "+821097429939",
          "+821097575322",
          "+821097578905",
          "+821097678705",
          "+821097798510",
          "+821097800727",
          "+821097881659",
          "+821098004855",
          "+821098388474",
          "+821098480602",
          "+821098764331",
          "+821099194225",
          "+821099208044",
          "+821099231319",
          "+821099329110",
          "+821099356427",
          "+821099482160",
          "+821099574780",
          "+821099596150",
          "+821099667987",
          "+821099730426",
          "+821099759966",
          "+821099761899",
          "+821099817870",
          "+821099826623",
          "+821099827953",
          "+821099950067",
          "+821099962895",
          "+821099988599",
          "+821022138436",
          "+821028515731",
          "+821034229665",
          "+821052249124",
          "+821054947230",
          "+821083750677",
          "+821093445213",
          "+821094678062"]


class PostsBlueprintTestCase(unittest.TestCase):
    
    def setUp(self) -> None:
        app = create_app(DevConfig)
        app.app_context().push()
        self.app = app.test_client()
    
    def test_create_post(self):
        """Checks to create a post properly."""
        
        users = User.objects.all()
        user_1 = users[0]
        user_2 = users[1]
        
        # insert user then create post
        file_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'testdata/nyan.png')
        
        # insert post1
        for i in range(2, 20):
            with open(file_dir, "rb") as image:
                b = bytearray(image.read())
                response = self.app.post(
                    "/posts/users/{uid}".format(uid=user_2["uid"]),
                    data=dict(title="dummy_title{0}".format(i),
                              description="dummy_description",
                              post_image=(io.BytesIO(b), 'test.jpg')),
                    follow_redirects=False,
                    content_type='multipart/form-data')
    
    def test_send_message_to_conversation(self):
        conversations = Conversation.objects.all()
        room_id = conversations[0].id
        uid = conversations[0].participants[0].uid
        # insert message_1
        self.app.post("/conversations/{room_id}/users/{uid}".format(
            room_id=room_id, uid=uid),
            data=json.dumps(dict(message="321321321")),
            content_type='application/json')
        print(conversations)
    
    def test_insert_mock_user_dump(self):
        # GxM4qD1jPMUo80TrrGHx9JI4OnO2
        # W56U9v84nfXiM842el1EWgENuzo1
        
        male_images = [
            dict(index=0,
                 url="https://storage.googleapis.com/pingme-280512.appspot.com/user_images/W56U9v84nfXiM842el1EWgENuzo1_0_9280f814-ead6-11ea-9038-907841698cfa"),
            dict(index=1,
                 url="https://storage.googleapis.com/pingme-280512.appspot.com/user_images/W56U9v84nfXiM842el1EWgENuzo1_1_999790cc-ead6-11ea-9038-907841698cfa"),
            dict(index=2,
                 url="https://storage.googleapis.com/pingme-280512.appspot.com/user_images/W56U9v84nfXiM842el1EWgENuzo1_2_a3a38abc-ead6-11ea-9038-907841698cfa"),
            dict(index=3,
                 url="https://storage.googleapis.com/pingme-280512.appspot.com/user_images/W56U9v84nfXiM842el1EWgENuzo1_3_920579c2-ead7-11ea-8b30-907841698cfa"),
            dict(index=4,
                 url="https://storage.googleapis.com/pingme-280512.appspot.com/user_images/W56U9v84nfXiM842el1EWgENuzo1_4_9ae50bf2-ead7-11ea-8b30-907841698cfa"),
            dict(index=5,
                 url="https://storage.googleapis.com/pingme-280512.appspot.com/user_images/W56U9v84nfXiM842el1EWgENuzo1_5_a475a41a-ead7-11ea-8b30-907841698cfa")
        ]
        
        female_images = [
            dict(index=0,
                 url="https://storage.googleapis.com/pingme-280512.appspot.com/user_images/GxM4qD1jPMUo80TrrGHx9JI4OnO2_0_c185da2c-ead5-11ea-9038-907841698cfa"),
            dict(index=1,
                 url="https://storage.googleapis.com/pingme-280512.appspot.com/user_images/GxM4qD1jPMUo80TrrGHx9JI4OnO2_1_e747faf6-ead5-11ea-9038-907841698cfa"),
            dict(index=2,
                 url="https://storage.googleapis.com/pingme-280512.appspot.com/user_images/GxM4qD1jPMUo80TrrGHx9JI4OnO2_2_ef52e4c2-ead5-11ea-9038-907841698cfa"),
            dict(index=3,
                 url="https://storage.googleapis.com/pingme-280512.appspot.com/user_images/GxM4qD1jPMUo80TrrGHx9JI4OnO2_3_f549d804-ead5-11ea-9038-907841698cfa"),
            dict(index=4,
                 url="https://storage.googleapis.com/pingme-280512.appspot.com/user_images/GxM4qD1jPMUo80TrrGHx9JI4OnO2_4_fc555c36-ead5-11ea-9038-907841698cfa"),
            dict(index=5,
                 url="https://storage.googleapis.com/pingme-280512.appspot.com/user_images/GxM4qD1jPMUo80TrrGHx9JI4OnO2_5_0953235a-ead6-11ea-9038-907841698cfa")
        ]
        
        array_to_dump = []
        for j in range(0, 700):
            for i in range(0, 1000):
                
                if i % 2 == 1:
                    sex = "M"
                    sex_kor = "남자"
                    random.shuffle(male_images)
                    user_images = []
                    for index, image in enumerate(male_images):
                        user_images.append(dict(index=index, url=image.get("url")))
                else:
                    sex = "F"
                    sex_kor = "여자"
                    random.shuffle(female_images)
                    user_images = []
                    for index, image in enumerate(female_images):
                        user_images.append(dict(index=index, url=image.get("url")))
                
                latitude = random.randrange(33125798, 38550609) / 1000000
                longitude = random.randrange(126018599, 129576299) / 1000000
                
                user_to_insert = dict(
                    uid=str(uuid.uuid1()),
                    nickname='{0} 사람_{1}'.format(sex_kor, i), sex=sex,
                    birthed_at=random.randrange(495644400, 969030000),
                    height=random.randrange(160, 185),
                    body_id=random.randrange(1, 4),
                    occupation=random.choice(["군인", "변호사", "유튜버", "연예인", "의사", "소방관", "거지"]),
                    education=random.choice(["초졸", "중졸", "고졸", "전문대졸", "4년제졸", "석사", "박사"]),
                    religion_id=random.randrange(0, 5),
                    drink_id=random.randrange(0, 3),
                    smoking_id=random.randrange(0, 3),
                    blood_id=random.randrange(0, 3),
                    device_token=str(uuid.uuid1()),
                    location=[longitude, latitude],
                    introduction='hello I am dummy user.',
                    joined_at=pendulum.now().int_timestamp,
                    last_login_at=pendulum.now().int_timestamp,
                    user_images=user_images,
                    charm_ids=[3, 4, 5, 7, 8], ideal_type_ids=[1, 5, 7, 8, 11],
                    interest_ids=[3, 5, 6, 9, 13, 15])
                
                array_to_dump.append(User(**user_to_insert))
            
            User.objects.insert(array_to_dump)
            array_to_dump = []
    
    def test_insert_default_user(self):
        man = dict(
            uid='GxM4qD1jPMUo80TrrGHx9JI4OnO2', nickname='mock_user_1', sex='F',
            birthed_at=1597509312, height=181, body_id=1, occupation="LAWER", education="UNIVERSITY",
            religion_id=2, drink_id=1, smoking_id=2, blood_id=1,
            device_token='cPFFTaZTQ2ivAN-bAmxNI5:APA91bFsgmm', introduction='hello mock_user_1', joined_at=1597509312,
            last_login_at=1597509312, user_images=[
                dict(index=0,
                     url="https://storage.googleapis.com/pingme-280512.appspot.com/user_images/GxM4qD1jPMUo80TrrGHx9JI4OnO2_0_c185da2c-ead5-11ea-9038-907841698cfa"),
                dict(index=1,
                     url="https://storage.googleapis.com/pingme-280512.appspot.com/user_images/GxM4qD1jPMUo80TrrGHx9JI4OnO2_1_e747faf6-ead5-11ea-9038-907841698cfa"),
                dict(index=2,
                     url="https://storage.googleapis.com/pingme-280512.appspot.com/user_images/GxM4qD1jPMUo80TrrGHx9JI4OnO2_2_ef52e4c2-ead5-11ea-9038-907841698cfa"),
                dict(index=3,
                     url="https://storage.googleapis.com/pingme-280512.appspot.com/user_images/GxM4qD1jPMUo80TrrGHx9JI4OnO2_3_f549d804-ead5-11ea-9038-907841698cfa"),
                dict(index=4,
                     url="https://storage.googleapis.com/pingme-280512.appspot.com/user_images/GxM4qD1jPMUo80TrrGHx9JI4OnO2_4_fc555c36-ead5-11ea-9038-907841698cfa"),
                dict(index=5,
                     url="https://storage.googleapis.com/pingme-280512.appspot.com/user_images/GxM4qD1jPMUo80TrrGHx9JI4OnO2_5_0953235a-ead6-11ea-9038-907841698cfa")
            ], charm_ids=[3, 4, 5, 7, 8, 9], ideal_type_ids=[1, 5, 7, 11, 13], interest_ids=[1, 3, 6, 13])
        
        woman = dict(
            uid='W56U9v84nfXiM842el1EWgENuzo1', nickname='mock_user_2', sex='M',
            birthed_at=1597509312, height=181, body_id=1, occupation="LAWER", education="UNIVERSITY",
            religion_id=2, drink_id=1, smoking_id=2, blood_id=1,
            device_token='bAmxNI5:APA91bFsgmm-cPFFTaZTQ2ivAN', introduction='hello mock_user_2', joined_at=1597509312,
            last_login_at=1597509312, user_images=[
                dict(index=0,
                     url="https://storage.googleapis.com/pingme-280512.appspot.com/user_images/W56U9v84nfXiM842el1EWgENuzo1_0_9280f814-ead6-11ea-9038-907841698cfa"),
                dict(index=1,
                     url="https://storage.googleapis.com/pingme-280512.appspot.com/user_images/W56U9v84nfXiM842el1EWgENuzo1_1_999790cc-ead6-11ea-9038-907841698cfa"),
                dict(index=2,
                     url="https://storage.googleapis.com/pingme-280512.appspot.com/user_images/W56U9v84nfXiM842el1EWgENuzo1_2_a3a38abc-ead6-11ea-9038-907841698cfa"),
                dict(index=3,
                     url="https://storage.googleapis.com/pingme-280512.appspot.com/user_images/W56U9v84nfXiM842el1EWgENuzo1_3_920579c2-ead7-11ea-8b30-907841698cfa"),
                dict(index=4,
                     url="https://storage.googleapis.com/pingme-280512.appspot.com/user_images/W56U9v84nfXiM842el1EWgENuzo1_4_9ae50bf2-ead7-11ea-8b30-907841698cfa"),
                dict(index=5,
                     url="https://storage.googleapis.com/pingme-280512.appspot.com/user_images/W56U9v84nfXiM842el1EWgENuzo1_5_a475a41a-ead7-11ea-8b30-907841698cfa")
            ],
            charm_ids=[6, 7, 9], ideal_type_ids=[1, 3, 9], interest_ids=[2, 3, 7])
        
        User(**man).save()
        User(**woman).save()
    
    def test_insert_an_comments(self):
        post = Post.objects.order_by("-created_at").first()
        user = User.objects.first()
        comment = Comment(
            user=user,
            comment="아무말이나 적어 놉니다 3.",
            created_at=pendulum.now().int_timestamp,
            favorite=False
        )
        comment.save()
        post.update(push__comments=comment)
        post.save()
    
    def test_insert_an_sub_comments(self):
        post = Post.objects.order_by("-created_at").first()
        user = User.objects.first()
        comment = Comment(
            user=user,
            comment="Sub comment test.",
            created_at=pendulum.now().int_timestamp,
            favorite=False
        ).save()
        post_comment = post.comments[0]
        post_comment.update(push__comments=comment)
        
        post.update(push__comments=comment)
        post.save()
    
    def test_update_geo_location(self):
        user = User.objects.all()[1]
        
        alarms = Alarm.objects.all()
        for alarm in alarms:
            alarm.delete()
        
        requests = Request.objects(user_from=user).all()
        for r in requests:
            r.delete()
        
        requests = Request.objects(user_to=user).all()
        for r in requests:
            r.delete()
        
        conversations = Conversation.objects.all()
        for c in conversations:
            c.delete()
        
        # user.update(set__location=dict(coordinates=[127.0936859, 37.505808], type='Point'))
    
    def test_insert_request(self):
        import random
        
        for batch in range(0, 100000):
            requests = []
            print(batch)
            
            result = list(User.objects.aggregate([{'$sample': {'size': 100}}]))
            
            for i in range(0, 100):
                user_1 = User.objects.get_or_404(id=str(result[int(random.random() * 100)]["_id"]))
                user_2 = User.objects.get_or_404(id=str(result[int(random.random() * 100)]["_id"]))
                
                requests.append(Request(
                    user_from=user_1,
                    user_to=user_2,
                    requested_at=pendulum.now().int_timestamp))
            
            Request.objects.insert(requests)
    
    def test_update_user_available(self):
        import requests
        
        user = User.objects(uid="AVZlVCmIXlWHy9ibTcLFT9b6YK02").first()
        url = 'http://127.0.0.1:5000/users/{user_id}/status/approval'.format(
            user_id=str(user.id)
        )
        headers = {
            "uid": user.uid,
            'content-type': 'application/json'
        }
        response = requests.put(url, headers=headers)
        self.assertEqual(response.status_code, 200)
    
    def test_insert_star_rating(self):
        auth.create_user("KAKAO:Kt2xktKtBgl_XmPeKt2xktKtBgl_XmPe")
        auth.create_custom_token("KAKAO:Kt2xktKtBgl_XmPe")
    
    def test_regex(self):
        import re
        phone = "+8201022889311 ".strip()
        replace_regex = "^\+82010"
        phone = re.sub(replace_regex, "+8210", phone)
        regex = r"^(\+820?10)[0-9]{3,4}[0-9]{4}$"
        match = re.match(regex, "+8201022889311")
        match.group(1).sub("+8210")
        print(match)
    
    def test_sha256(self):
        import hashlib
        m = hashlib.sha256(bytes("!@#", 'utf-8')).hexdigest()
        print(m)
    
    def test_phone(self):
        import pendulum
        from blueprints.users_blueprint import _geo_query_users
        users = User.objects.aggregate([{
            '$sample': {'size': 2000}
        }])
        nin_ids = []
        for user in users:
            nin_ids.append(str(user.get("_id")))
        user = User.objects(id="5f953b8afa57d31f717d31a9").first()
        start = pendulum.now().int_timestamp
        result = _geo_query_users(user, set(nin_ids))
        end = pendulum.now().int_timestamp
        print(end - start)
        print(len(result))
    
    def test_phone(self):
        user = User.objects(uid="AVZlVCmIXlWHy9ibTcLFT9b6YK02").first()
        start = pendulum.now().int_timestamp
        contact = Contact.objects(owner=user).first()
        phone_users = User.objects(phone__in=contact.phones).only("id").all()
        user_ids = set([str(user.id) for user in phone_users])
        end = pendulum.now().int_timestamp
        elapsed = end - start
        print(elapsed)


if __name__ == "__main__":
    unittest.main()

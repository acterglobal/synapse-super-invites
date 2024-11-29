
from .test_integrations import SuperInviteHomeserverTestCase

# type: ignore[import-untyped]
from matrix_synapse_testutils.unittest import override_config
import hashlib
from tempfile import TemporaryDirectory

test_dir = TemporaryDirectory()
URL_PREFIX = "https://app.example.com/p/"

TEST_CONFIG = {
    "modules": [
        {
            "module": "synapse_super_invites.SynapseSuperInvites",
            "config": {
                "sql_url": "sqlite:///",
                "share_link_generator": {
                    "url_prefix": URL_PREFIX,
                    "target_path": test_dir.name,
                }
            },
        }
    ]
}


class ShareLinkTests(SuperInviteHomeserverTestCase):

    def make_target_uri(self, path: str, user_id='', query='') -> str:
        if user_id[0] == '@':
            user_id = user_id[1:]  # remove leading `@`
        uriFormatter = "{uriPrefix}{hash}?{query}#{path}"
        q = '{query}&userId={userId}'.format(query=query, userId=user_id) if len(
            query) != 0 else 'userId={userId}'.format(userId=user_id)
        targetHash = hashlib.sha1(
            uriFormatter.format(
                uriPrefix=URL_PREFIX,
                hash='',  # no hash here
                query=q,
                path=path,
            ).encode()
        ).hexdigest()

        return uriFormatter.format(
            uriPrefix=URL_PREFIX,
            hash=targetHash,  # no hash here
            query=q,
            path=path,
        )

    @override_config(TEST_CONFIG)  # type: ignore[misc]
    def test_pin_object(self) -> None:
        m_id = self.register_user("meeko", "password")
        m_access_token = self.login("meeko", "password")

        # this is our new backend.
        channel = self.make_request(
            "PUT", "/_synapse/client/share_link/", access_token=m_access_token,
            content={
                "type": "spaceObject",
                "objectId": "objectId",
                "objectType": "pin",
                "roomId": "roomId",
            },
        )

        self.assertEqual(channel.code, 200, msg=channel.result)
        self.assertEqual(channel.json_body["url"], self.make_target_uri(
            "o/roomId/pin/objectId", user_id=m_id))

    @override_config(TEST_CONFIG)  # type: ignore[misc]
    def test_task_list_object(self) -> None:
        m_id = self.register_user("meeko", "password")
        m_access_token = self.login("meeko", "password")

        # this is our new backend.
        channel = self.make_request(
            "PUT", "/_synapse/client/share_link/", access_token=m_access_token,
            content={
                "type": "spaceObject",
                "objectId": "randomId",
                "objectType": "taskList",
                "roomId": "myRoomId:example.org",
            },
        )

        self.assertEqual(channel.code, 200, msg=channel.result)
        self.assertEqual(channel.json_body["url"], self.make_target_uri(
            "o/myRoomId:example.org/taskList/randomId", user_id=m_id))

    @override_config(TEST_CONFIG)  # type: ignore[misc]
    def test_boost_object(self) -> None:
        m_id = self.register_user("meeko", "password")
        m_access_token = self.login("meeko", "password")

        # this is our new backend.
        channel = self.make_request(
            "PUT", "/_synapse/client/share_link/", access_token=m_access_token,
            content={
                "type": "spaceObject",
                "objectId": "boostId",
                "objectType": "boost",
                "roomId": "newRoom:acter.global",
            },
        )

        self.assertEqual(channel.code, 200, msg=channel.result)
        self.assertEqual(channel.json_body["url"], self.make_target_uri(
            "o/newRoom:acter.global/boost/boostId", user_id=m_id))

    @override_config(TEST_CONFIG)  # type: ignore[misc]
    def test_calenderEvent_object(self) -> None:
        m_id = self.register_user("meeko", "password")
        m_access_token = self.login("meeko", "password")

        # this is our new backend.
        channel = self.make_request(
            "PUT", "/_synapse/client/share_link/", access_token=m_access_token,
            content={
                "type": "spaceObject",
                "objectId": "idOfEvent",
                "objectType": "calendarEvent",
                "roomId": "newRoom:acter.global",
            },
        )

        self.assertEqual(channel.code, 200, msg=channel.result)
        self.assertEqual(channel.json_body["url"], self.make_target_uri(
            "o/newRoom:acter.global/calendarEvent/idOfEvent", user_id=m_id))

    @override_config(TEST_CONFIG)  # type: ignore[misc]
    def test_with_query_preview(self) -> None:
        m_id = self.register_user("meeko", "password")
        m_access_token = self.login("meeko", "password")

        # this is our new backend.
        channel = self.make_request(
            "PUT", "/_synapse/client/share_link/", access_token=m_access_token,
            content={
                "type": "spaceObject",
                "objectId": "objectId",
                "objectType": "pin",
                "roomId": "roomId",
                "query": 'roomDisplayName=My+cool+space&title=Pin+Title'
            },
        )

        self.assertEqual(channel.code, 200, msg=channel.result)
        self.assertEqual(channel.json_body["url"], self.make_target_uri(
            "o/roomId/pin/objectId", user_id=m_id, query='roomDisplayName=My+cool+space&title=Pin+Title',))

    @override_config(TEST_CONFIG)  # type: ignore[misc]
    def test_with_query_via(self) -> None:
        m_id = self.register_user("meeko", "password")
        m_access_token = self.login("meeko", "password")

        # this is our new backend.
        channel = self.make_request(
            "PUT", "/_synapse/client/share_link/", access_token=m_access_token,
            content={
                "type": "spaceObject",
                "objectId": "objectId",
                "objectType": "pin",
                "roomId": "roomId",
                "query": 'via=acer.global&via=matrix.org'
            },
        )

        self.assertEqual(channel.code, 200, msg=channel.result)
        self.assertEqual(channel.json_body["url"], self.make_target_uri(
            "o/roomId/pin/objectId", user_id=m_id, query='via=acer.global&via=matrix.org',))

    @override_config(TEST_CONFIG)  # type: ignore[misc]
    def test_cant_spoof_user_id(self) -> None:
        m_id = self.register_user("meeko", "password")
        m_access_token = self.login("meeko", "password")

        # trying to add a userId
        channel = self.make_request(
            "PUT", "/_synapse/client/share_link/", access_token=m_access_token,
            content={
                "type": "spaceObject",
                "objectId": "objectId",
                "objectType": "pin",
                "roomId": "roomId",
                "query": 'roomDisplayName=test+room&userId=otherId:example.org'
            },
        )

        self.assertEqual(channel.code, 200, msg=channel.result)
        self.assertEqual(channel.json_body["url"], self.make_target_uri(
            "o/roomId/pin/objectId", user_id=m_id, query='roomDisplayName=test+room'))

        # lets try at the beginning
        channel = self.make_request(
            "PUT", "/_synapse/client/share_link/", access_token=m_access_token,
            content={
                "type": "spaceObject",
                "objectId": "objectId",
                "objectType": "pin",
                "roomId": "roomId",
                "query": 'userId=notallowed:example.org&roomDisplayName=test+room'
            },
        )

        self.assertEqual(channel.code, 200, msg=channel.result)
        self.assertEqual(channel.json_body["url"], self.make_target_uri(
            "o/roomId/pin/objectId", user_id=m_id, query='roomDisplayName=test+room'))

        # lets try multiple times
        channel = self.make_request(
            "PUT", "/_synapse/client/share_link/", access_token=m_access_token,
            content={
                "type": "spaceObject",
                "objectId": "objectId",
                "objectType": "pin",
                "roomId": "roomId",
                "query": 'userId=notallowed:example.org&roomDisplayName=test+room&userId=nope:example.org'
            },
        )

        self.assertEqual(channel.code, 200, msg=channel.result)
        self.assertEqual(channel.json_body["url"], self.make_target_uri(
            "o/roomId/pin/objectId", user_id=m_id, query='roomDisplayName=test+room'))

    @override_config(TEST_CONFIG)  # type: ignore[misc]
    def test_super_invite_with_preview_data(self) -> None:
        m_id = self.register_user("meeko", "password")
        m_access_token = self.login("meeko", "password")

        # this is our new backend.
        channel = self.make_request(
            "PUT", "/_synapse/client/share_link/", access_token=m_access_token,
            content={
                "type": "superInvite",
                "inviteCode": "superInviteCode",
                "server": "acter.global",
                "query": "userDisplayName=superBen&rooms=4"
            },
        )

        self.assertEqual(channel.code, 200, msg=channel.result)
        self.assertEqual(channel.json_body["url"], self.make_target_uri(
            "i/acter.global/superInviteCode", user_id=m_id, query="userDisplayName=superBen&rooms=4"))

from typing import Any

from matrix_synapse_testutils.unittest import (  # type: ignore[import-untyped]
    HomeserverTestCase,
    override_config,
)
from synapse.rest import admin
from synapse.rest.client import login, profile, register, room, sync
from synapse.server import HomeServer
from synapse.types import Dict  # type: ignore[attr-defined]
from synapse.util import Clock
from twisted.test.proto_helpers import MemoryReactor
from twisted.web.resource import Resource

from .test_config import DEFAULT_CONFIG as DEFAULT_MODULE_CFG

DEFAULT_CONFIG = {
    "modules": [
        {
            "module": "synapse_super_invites.SynapseSuperInvites",
            "config": DEFAULT_MODULE_CFG,
        }
    ]
}


# Some more local helpers
class SuperInviteHomeserverTestCase(HomeserverTestCase):  # type: ignore[misc]
    servlets = [
        admin.register_servlets,
        login.register_servlets,
        room.register_servlets,
        profile.register_servlets,
        sync.register_servlets,
        register.register_servlets,
    ]

    def prepare(self, reactor: MemoryReactor, clock: Clock, hs: HomeServer) -> None:
        self.store = hs.get_datastores().main
        self.module_api = hs.get_module_api()
        self.event_creation_handler = hs.get_event_creation_handler()
        self.sync_handler = hs.get_sync_handler()
        self.auth_handler = hs.get_auth_handler()

    def create_resource_dict(self) -> Dict[str, Resource]:
        d: Dict[str, Resource] = super().create_resource_dict()
        for key in self.hs._module_web_resources:
            d[key] = self.hs._module_web_resources[key]
        return d

    # create a room with the given access_token, return the roomId
    def create_room(self, user_id: str) -> str:
        room_id: str = self.get_success(
            self.module_api.create_room(user_id=user_id, config={}, ratelimit=False)
        )[0]
        return room_id

    # create a room with the given access_token, return the roomId
    def create_public_room(self, user_id: str) -> str:
        room_id: str = self.get_success(
            self.module_api.create_room(
                user_id=user_id,
                config={"preset": "public_chat", "visibility": "public"},
                ratelimit=False,
            )
        )[0]
        return room_id

    def getState(
        self, room_data: dict[Any, Any], type_key: str, state_key: str | None
    ) -> Any | None:
        for e in reversed(room_data.get("timeline", {}).get("events", [])):
            if e.get("type") == type_key:
                if state_key is not None:
                    if e.get("state_key") == state_key:
                        return e.get("content")
                else:
                    return e.get("content")
        return None


class SimpleInviteTests(SuperInviteHomeserverTestCase):
    @override_config(DEFAULT_CONFIG)  # type: ignore[misc]
    def test_edit_invite_token_rooms(self) -> None:
        m_id = self.register_user("meeko", "password")
        m_access_token = self.login("meeko", "password")

        # this is our new backend.
        channel = self.make_request(
            "GET", "/_synapse/client/super_invites/tokens", access_token=m_access_token
        )
        self.assertEqual(channel.code, 200, msg=channel.result)
        self.assertEqual(channel.json_body["tokens"], [])

        # creating five channel
        roomA = self.create_room(m_id)
        roomB = self.create_room(m_id)
        roomC = self.create_room(m_id)
        roomD = self.create_room(m_id)
        roomE = self.create_room(m_id)

        rooms_to_invite = [
            roomB,
            roomC,
            roomD,
        ]
        # create a new one for testing.
        channel = self.make_request(
            "POST",
            "/_synapse/client/super_invites/tokens",
            access_token=m_access_token,
            content={"rooms": rooms_to_invite},
        )
        self.assertEqual(channel.code, 200, msg=channel.result)
        token_data = channel.json_body["token"]
        self.assertCountEqual(token_data["rooms"], rooms_to_invite)
        self.assertEqual(token_data["create_dm"], False)
        token = token_data["token"]

        # now we update the roomlist

        rooms_to_invite = [
            roomA,
            roomC,
            roomE,
        ]
        # create a new one for testing.
        channel = self.make_request(
            "POST",
            "/_synapse/client/super_invites/tokens",
            access_token=m_access_token,
            content={"token": token, "create_dm": True, "rooms": rooms_to_invite},
        )
        self.assertEqual(channel.code, 200, msg=channel.result)
        token_data = channel.json_body["token"]
        self.assertEqual(token_data["token"], token)
        self.assertCountEqual(token_data["rooms"], rooms_to_invite)
        self.assertEqual(token_data["create_dm"], True)

    @override_config(DEFAULT_CONFIG)  # type: ignore[misc]
    def test_simple_invite_token_test(self) -> None:
        m_id = self.register_user("meeko", "password")
        m_access_token = self.login("meeko", "password")

        # this is our new backend.
        channel = self.make_request(
            "GET", "/_synapse/client/super_invites/tokens", access_token=m_access_token
        )
        self.assertEqual(channel.code, 200, msg=channel.result)
        self.assertEqual(channel.json_body["tokens"], [])

        # creating five channel
        _roomA = self.create_room(m_id)
        roomB = self.create_room(m_id)
        roomC = self.create_room(m_id)
        roomD = self.create_room(m_id)
        _roomE = self.create_room(m_id)

        rooms_to_invite = [
            roomB,
            roomC,
            roomD,
        ]
        # create a new one for testing.
        channel = self.make_request(
            "POST",
            "/_synapse/client/super_invites/tokens",
            access_token=m_access_token,
            content={"rooms": rooms_to_invite},
        )
        self.assertEqual(channel.code, 200, msg=channel.result)
        token_data = channel.json_body["token"]
        self.assertCountEqual(token_data["rooms"], rooms_to_invite)
        self.assertEquals(token_data["accepted_count"], 0)
        self.assertFalse(token_data["create_dm"])
        token = token_data["token"]

        # redeem the new token

        _f_id = self.register_user("flit", "flit")
        f_access_token = self.login("flit", "flit")

        channel = self.make_request(
            "GET",
            "/_synapse/client/super_invites/info?token={token}".format(token=token),
            access_token=f_access_token,
        )
        self.assertEqual(channel.code, 200, msg=channel.result)
        # list the rooms we were invited to

        self.assertEqual(channel.json_body["rooms_count"], 3)
        self.assertEqual(channel.json_body["create_dm"], False)
        self.assertEqual(channel.json_body["has_redeemed"], False)
        self.assertEqual(channel.json_body["inviter"]["user_id"], "@meeko:test")
        self.assertEqual(channel.json_body["inviter"]["display_name"], "meeko")

        channel = self.make_request(
            "POST",
            "/_synapse/client/super_invites/redeem?token={token}".format(token=token),
            access_token=f_access_token,
        )
        self.assertEqual(channel.code, 200, msg=channel.result)
        # list the rooms we were invited to
        self.assertCountEqual(channel.json_body["rooms"], rooms_to_invite)

        # we see it has been redeemed
        channel = self.make_request(
            "GET",
            "/_synapse/client/super_invites/tokens?token={token}".format(token=token),
            access_token=m_access_token,
        )
        self.assertEqual(channel.code, 200, msg=channel.result)
        token_data = channel.json_body["token"]
        self.assertEquals(token_data["accepted_count"], 1)

        channel = self.make_request(
            "GET",
            "/_synapse/client/super_invites/info?token={token}".format(token=token),
            access_token=f_access_token,
        )
        self.assertEqual(channel.code, 200, msg=channel.result)
        self.assertEqual(channel.json_body["has_redeemed"], True)

        # and flit was invited to these, too:
        channel = self.make_request(
            "GET", "/_matrix/client/v3/sync", access_token=f_access_token
        )
        self.assertEqual(channel.code, 200, msg=channel.result)
        self.assertEqual(channel.json_body["rooms"].get("invite"), None)
        self.assertCountEqual(
            channel.json_body["rooms"]["join"].keys(), rooms_to_invite
        )

    @override_config(DEFAULT_CONFIG)  # type: ignore[misc]
    def test_simple_can_join_public_room_test(self) -> None:
        m_id = self.register_user("meeko", "password")
        m_access_token = self.login("meeko", "password")

        # this is our new backend.
        channel = self.make_request(
            "GET", "/_synapse/client/super_invites/tokens", access_token=m_access_token
        )
        self.assertEqual(channel.code, 200, msg=channel.result)
        self.assertEqual(channel.json_body["tokens"], [])

        # creating five channel
        _roomA = self.create_room(m_id)
        roomB = self.create_public_room(m_id)  # this is public
        roomC = self.create_room(m_id)
        roomD = self.create_room(m_id)
        _roomE = self.create_room(m_id)

        rooms_to_invite = [
            roomB,
            roomC,
            roomD,
        ]
        # create a new one for testing.
        channel = self.make_request(
            "POST",
            "/_synapse/client/super_invites/tokens",
            access_token=m_access_token,
            content={"rooms": rooms_to_invite},
        )
        self.assertEqual(channel.code, 200, msg=channel.result)
        token_data = channel.json_body["token"]
        self.assertCountEqual(token_data["rooms"], rooms_to_invite)
        self.assertEquals(token_data["accepted_count"], 0)
        self.assertFalse(token_data["create_dm"])
        token = token_data["token"]

        # redeem the new token

        _f_id = self.register_user("flit", "flit")
        f_access_token = self.login("flit", "flit")

        channel = self.make_request(
            "POST",
            "/_synapse/client/super_invites/redeem?token={token}".format(token=token),
            access_token=f_access_token,
        )
        self.assertEqual(channel.code, 200, msg=channel.result)
        # list the rooms we were invited to
        self.assertCountEqual(channel.json_body["rooms"], rooms_to_invite)

        # we see it has been redeemed
        channel = self.make_request(
            "GET",
            "/_synapse/client/super_invites/tokens?token={token}".format(token=token),
            access_token=m_access_token,
        )
        self.assertEqual(channel.code, 200, msg=channel.result)
        token_data = channel.json_body["token"]
        self.assertEquals(token_data["accepted_count"], 1)

        # and flit was invited to these, too:
        channel = self.make_request(
            "GET", "/_matrix/client/v3/sync", access_token=f_access_token
        )
        self.assertEqual(channel.code, 200, msg=channel.result)
        self.assertEqual(channel.json_body["rooms"].get("invite"), None)
        self.assertCountEqual(
            channel.json_body["rooms"]["join"].keys(), rooms_to_invite
        )
        # ensure the dm matches what we are expecting
        public_room = channel.json_body["rooms"]["join"][roomB]
        join_rule = self.getState(public_room, "m.room.join_rules", None)
        self.assertEquals(join_rule["join_rule"], "public", join_rule)

    @override_config(
        {
            "enable_registration": True,
            "registration_requires_token": True,
            "modules": [
                {
                    "module": "synapse_super_invites.SynapseSuperInvites",
                    "config": {
                        "sql_url": "sqlite:///",
                        "generate_registration_token": True,
                    },
                }
            ],
        }
    )  # type: ignore[misc]
    def test_simple_invite_as_registration_token_test(self) -> None:
        _m_id = self.register_user("meeko", "password")
        m_access_token = self.login("meeko", "password")

        # this is our new backend.
        channel = self.make_request(
            "GET", "/_synapse/client/super_invites/tokens", access_token=m_access_token
        )
        self.assertEqual(channel.code, 200, msg=channel.result)
        self.assertEqual(channel.json_body["tokens"], [])

        # create a new token for testing.
        channel = self.make_request(
            "POST",
            "/_synapse/client/super_invites/tokens",
            {"rooms": []},
            access_token=m_access_token,
        )
        self.assertEqual(channel.code, 200, msg=channel.result)
        token = channel.json_body["token"]
        registration_token = channel.json_body["registration_token"]
        self.assertTrue(registration_token["valid"])

        # let's see if the token exists and is valid
        channel = self.make_request(
            "GET",
            "/_matrix/client/v1/register/m.login.registration_token/validity?token={token}".format(
                token=token["token"]
            ),
        )
        self.assertEqual(channel.code, 200, msg=channel.result)
        self.assertTrue(channel.json_body["valid"])

        # create a new token for testing, no registration
        channel = self.make_request(
            "POST",
            "/_synapse/client/super_invites/tokens",
            {"rooms": [], "as_registration_token": False},
            access_token=m_access_token,
        )
        self.assertEqual(channel.code, 200, msg=channel.result)
        token = channel.json_body["token"]
        registration_token = channel.json_body["registration_token"]
        self.assertFalse(registration_token["valid"])
        self.assertEquals(registration_token["reason"], "NOT_REQUESTED")

        # let's see if the token exists and is valid
        channel = self.make_request(
            "GET",
            "/_matrix/client/v1/register/m.login.registration_token/validity?token={token}".format(
                token=token["token"]
            ),
        )
        self.assertEqual(channel.code, 200, msg=channel.result)
        self.assertFalse(channel.json_body["valid"])

    @override_config(
        {
            "enable_registration": True,
            "registration_requires_token": True,
            "modules": [
                {
                    "module": "synapse_super_invites.SynapseSuperInvites",
                    "config": {
                        "sql_url": "sqlite:///",
                        "generate_registration_token": False,
                    },
                }
            ],
        }
    )  # type: ignore[misc]
    def test_simple_invite_as_registration_token_not_available_test(self) -> None:
        _m_id = self.register_user("meeko", "password")
        m_access_token = self.login("meeko", "password")

        # this is our new backend.
        channel = self.make_request(
            "GET", "/_synapse/client/super_invites/tokens", access_token=m_access_token
        )
        self.assertEqual(channel.code, 200, msg=channel.result)
        self.assertEqual(channel.json_body["tokens"], [])

        # create a new token for testing.
        channel = self.make_request(
            "POST",
            "/_synapse/client/super_invites/tokens",
            {"rooms": [], "as_registration_token": True},
            access_token=m_access_token,
        )
        self.assertEqual(channel.code, 200, msg=channel.result)
        token = channel.json_body["token"]
        registration_token = channel.json_body["registration_token"]
        self.assertFalse(registration_token["valid"])
        self.assertEquals(registration_token["reason"], "NOT_ENABLED")

        # let's see if the token exists and is valid
        channel = self.make_request(
            "GET",
            "/_matrix/client/v1/register/m.login.registration_token/validity?token={token}".format(
                token=token["token"]
            ),
        )
        self.assertEqual(channel.code, 200, msg=channel.result)
        self.assertFalse(channel.json_body["valid"])

    @override_config(DEFAULT_CONFIG)  # type: ignore[misc]
    def test_simple_invite_token_only_dm_test(self) -> None:
        _m_id = self.register_user("meeko", "password")
        m_access_token = self.login("meeko", "password")

        # this is our new backend.
        channel = self.make_request(
            "GET", "/_synapse/client/super_invites/tokens", access_token=m_access_token
        )
        self.assertEqual(channel.code, 200, msg=channel.result)
        self.assertEqual(channel.json_body["tokens"], [])

        # create a new one for testing.
        channel = self.make_request(
            "POST",
            "/_synapse/client/super_invites/tokens",
            access_token=m_access_token,
            content={"rooms": [], "create_dm": True},
        )
        self.assertEqual(channel.code, 200, msg=channel.result)
        token_data = channel.json_body["token"]
        self.assertCountEqual(token_data["rooms"], [])
        self.assertEquals(token_data["accepted_count"], 0)
        self.assertTrue(token_data["create_dm"])
        token = token_data["token"]

        channel = self.make_request(
            "GET", "/_synapse/client/super_invites/tokens", access_token=m_access_token
        )
        self.assertEqual(channel.code, 200, msg=channel.result)
        self.assertEqual(len(channel.json_body["tokens"]), 1)

        # redeem the new token

        _f_id = self.register_user("flit", "flit")
        f_access_token = self.login("flit", "flit")

        channel = self.make_request(
            "POST",
            "/_synapse/client/super_invites/redeem?token={token}".format(token=token),
            access_token=f_access_token,
        )
        self.assertEqual(channel.code, 200, msg=channel.result)
        # only the DM added to
        self.assertEquals(len(channel.json_body["rooms"]), 1)

        new_dm = channel.json_body["rooms"][0]

        # we see it has been redeemed
        channel = self.make_request(
            "GET",
            "/_synapse/client/super_invites/tokens?token={token}".format(token=token),
            access_token=m_access_token,
        )
        self.assertEqual(channel.code, 200, msg=channel.result)
        token_data = channel.json_body["token"]
        self.assertEquals(token_data["accepted_count"], 1)

        # and flit was invited to these, too:
        channel = self.make_request(
            "GET", "/_matrix/client/v3/sync", access_token=f_access_token
        )
        self.assertEqual(channel.code, 200, msg=channel.result)
        # we are the author of the DM, so we aren't invited, but just added
        self.assertEqual(channel.json_body["rooms"].get("invite"), None)
        self.assertCountEqual(channel.json_body["rooms"]["join"].keys(), [new_dm])

        # ensure the dm matches what we are expecting
        dm = channel.json_body["rooms"]["join"][new_dm]
        join_rule = self.getState(dm, "m.room.join_rules", None)
        self.assertEquals(join_rule["join_rule"], "invite", join_rule)

        # and the other has been invited, too
        member = self.getState(dm, "m.room.member", "@meeko:test")
        self.assertEquals(member.get("membership"), "invite", member)
        # to the DM
        self.assertEquals(member.get("is_direct"), True, member)

    @override_config(DEFAULT_CONFIG)  # type: ignore[misc]
    def test_simple_invite_token_with_dm_test(self) -> None:
        m_id = self.register_user("meeko", "password")
        m_access_token = self.login("meeko", "password")

        # this is our new backend.
        channel = self.make_request(
            "GET", "/_synapse/client/super_invites/tokens", access_token=m_access_token
        )
        self.assertEqual(channel.code, 200, msg=channel.result)
        self.assertEqual(channel.json_body["tokens"], [])

        roomB = self.create_room(m_id)
        roomC = self.create_room(m_id)
        roomD = self.create_room(m_id)

        rooms_to_invite = [
            roomB,
            roomC,
            roomD,
        ]
        # create a new one for testing.
        channel = self.make_request(
            "POST",
            "/_synapse/client/super_invites/tokens",
            access_token=m_access_token,
            content={"rooms": rooms_to_invite, "create_dm": True},
        )
        self.assertEqual(channel.code, 200, msg=channel.result)
        token_data = channel.json_body["token"]
        self.assertCountEqual(token_data["rooms"], rooms_to_invite)
        self.assertEquals(token_data["accepted_count"], 0)
        self.assertTrue(token_data["create_dm"])
        token = token_data["token"]

        channel = self.make_request(
            "GET", "/_synapse/client/super_invites/tokens", access_token=m_access_token
        )
        self.assertEqual(channel.code, 200, msg=channel.result)
        self.assertEqual(len(channel.json_body["tokens"]), 1)

        # redeem the new token

        _f_id = self.register_user("flit", "flit")
        f_access_token = self.login("flit", "flit")

        channel = self.make_request(
            "POST",
            "/_synapse/client/super_invites/redeem?token={token}".format(token=token),
            access_token=f_access_token,
        )
        self.assertEqual(channel.code, 200, msg=channel.result)
        # list the rooms we were invited to
        dm_rooms = []
        for r in channel.json_body["rooms"]:
            if r in rooms_to_invite:
                continue
            dm_rooms.append(r)
        self.assertEqual(len(dm_rooms), 1)

        # we see it has been redeemed
        channel = self.make_request(
            "GET",
            "/_synapse/client/super_invites/tokens?token={token}".format(token=token),
            access_token=m_access_token,
        )
        self.assertEqual(channel.code, 200, msg=channel.result)
        token_data = channel.json_body["token"]
        self.assertEquals(token_data["accepted_count"], 1)

        # and flit was invited to these, too:
        channel = self.make_request(
            "GET", "/_matrix/client/v3/sync", access_token=f_access_token
        )
        self.assertEqual(channel.code, 200, msg=channel.result)
        self.assertEqual(channel.json_body["rooms"].get("invite"), None)
        self.assertCountEqual(
            channel.json_body["rooms"]["join"].keys(), rooms_to_invite + dm_rooms
        )

    @override_config(DEFAULT_CONFIG)  # type: ignore[misc]
    def test_only_dm_redeem_once(self) -> None:
        _m_id = self.register_user("meeko", "password")
        m_access_token = self.login("meeko", "password")

        # this is our new backend.
        channel = self.make_request(
            "GET", "/_synapse/client/super_invites/tokens", access_token=m_access_token
        )
        self.assertEqual(channel.code, 200, msg=channel.result)
        self.assertEqual(channel.json_body["tokens"], [])

        # create a new one for testing.
        channel = self.make_request(
            "POST",
            "/_synapse/client/super_invites/tokens",
            access_token=m_access_token,
            content={"rooms": [], "create_dm": True},
        )
        self.assertEqual(channel.code, 200, msg=channel.result)
        token_data = channel.json_body["token"]
        self.assertEquals(token_data["accepted_count"], 0)
        self.assertTrue(token_data["create_dm"])
        token = token_data["token"]

        channel = self.make_request(
            "GET", "/_synapse/client/super_invites/tokens", access_token=m_access_token
        )
        self.assertEqual(channel.code, 200, msg=channel.result)
        self.assertEqual(len(channel.json_body["tokens"]), 1)

        # redeem the new token
        _f_id = self.register_user("flit", "flit")
        f_access_token = self.login("flit", "flit")

        channel = self.make_request(
            "POST",
            "/_synapse/client/super_invites/redeem?token={token}".format(token=token),
            access_token=f_access_token,
        )
        self.assertEqual(channel.code, 200, msg=channel.result)
        # list the rooms we were invited to
        self.assertEquals(len(channel.json_body["rooms"]), 1)

        # we see it has been redeemed
        channel = self.make_request(
            "GET",
            "/_synapse/client/super_invites/tokens?token={token}".format(token=token),
            access_token=m_access_token,
        )
        self.assertEqual(channel.code, 200, msg=channel.result)
        token_data = channel.json_body["token"]
        self.assertEquals(token_data["accepted_count"], 1)

        # trying to redeem again fails.
        channel = self.make_request(
            "POST",
            "/_synapse/client/super_invites/redeem?token={token}".format(token=token),
            access_token=f_access_token,
        )
        self.assertEqual(channel.code, 400, msg=channel.result)

    @override_config(DEFAULT_CONFIG)  # type: ignore[misc]
    def test_deletion(self) -> None:
        _m_id = self.register_user("meeko", "password")
        m_access_token = self.login("meeko", "password")

        # this is our new backend.
        channel = self.make_request(
            "GET", "/_synapse/client/super_invites/tokens", access_token=m_access_token
        )
        self.assertEqual(channel.code, 200, msg=channel.result)
        self.assertEqual(channel.json_body["tokens"], [])

        # create a new one for testing.
        channel = self.make_request(
            "POST",
            "/_synapse/client/super_invites/tokens",
            access_token=m_access_token,
            content={"rooms": [], "create_dm": True},
        )
        self.assertEqual(channel.code, 200, msg=channel.result)
        token_data = channel.json_body["token"]
        self.assertEquals(token_data["accepted_count"], 0)
        self.assertTrue(token_data["create_dm"])
        token = token_data["token"]

        channel = self.make_request(
            "GET", "/_synapse/client/super_invites/tokens", access_token=m_access_token
        )
        self.assertEqual(channel.code, 200, msg=channel.result)
        self.assertEqual(len(channel.json_body["tokens"]), 1)

        # we can access it
        channel = self.make_request(
            "GET",
            "/_synapse/client/super_invites/tokens?token={token}".format(token=token),
            access_token=m_access_token,
        )
        self.assertEqual(channel.code, 200, msg=channel.result)

        # delete it
        channel = self.make_request(
            "DELETE",
            "/_synapse/client/super_invites/tokens?token={token}".format(token=token),
            access_token=m_access_token,
        )
        self.assertEqual(channel.code, 200, msg=channel.result)

        # we can't access it
        channel = self.make_request(
            "GET",
            "/_synapse/client/super_invites/tokens?token={token}".format(token=token),
            access_token=m_access_token,
        )
        self.assertEqual(channel.code, 404, msg=channel.result)

        # and it doesn't show up in the user listing
        channel = self.make_request(
            "GET", "/_synapse/client/super_invites/tokens", access_token=m_access_token
        )
        self.assertEqual(channel.code, 200, msg=channel.result)
        self.assertEqual(channel.json_body["tokens"], [])

        # trying to redeem token
        _f_id = self.register_user("flit", "flit")
        f_access_token = self.login("flit", "flit")

        # and it can't be found
        channel = self.make_request(
            "GET",
            "/_synapse/client/super_invites/info?token={token}".format(token=token),
            access_token=f_access_token,
        )
        self.assertEqual(channel.code, 403, msg=channel.result)  # access denied

        # and it can't be redeemed
        channel = self.make_request(
            "POST",
            "/_synapse/client/super_invites/redeem?token={token}".format(token=token),
            access_token=f_access_token,
        )
        self.assertEqual(channel.code, 404, msg=channel.result)

    @override_config(DEFAULT_CONFIG)  # type: ignore[misc]
    def test_cant_redeem_my_own(self) -> None:
        _m_id = self.register_user("meeko", "password")
        m_access_token = self.login("meeko", "password")

        # this is our new backend.
        channel = self.make_request(
            "GET", "/_synapse/client/super_invites/tokens", access_token=m_access_token
        )
        self.assertEqual(channel.code, 200, msg=channel.result)
        self.assertEqual(channel.json_body["tokens"], [])

        # create a new one for testing.
        channel = self.make_request(
            "POST",
            "/_synapse/client/super_invites/tokens",
            access_token=m_access_token,
            content={"rooms": [], "create_dm": True},
        )
        self.assertEqual(channel.code, 200, msg=channel.result)
        token_data = channel.json_body["token"]
        self.assertEquals(token_data["accepted_count"], 0)
        self.assertTrue(token_data["create_dm"])
        token = token_data["token"]

        channel = self.make_request(
            "GET", "/_synapse/client/super_invites/tokens", access_token=m_access_token
        )
        self.assertEqual(channel.code, 200, msg=channel.result)
        self.assertEqual(len(channel.json_body["tokens"]), 1)

        # and it can't be redeemed
        channel = self.make_request(
            "POST",
            "/_synapse/client/super_invites/redeem?token={token}".format(token=token),
            access_token=m_access_token,
        )
        self.assertEqual(channel.code, 400, msg=channel.result)

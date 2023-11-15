from unittest import TestCase
from unittest.mock import Mock

from twisted.test.proto_helpers import MemoryReactor

from synapse.types import JsonDict, Dict
from synapse.server import HomeServer
from synapse.util import Clock
from synapse.rest.client import login, room, profile
from synapse.rest import admin
from twisted.web.resource import Resource

from matrix_synapse_testutils.unittest import HomeserverTestCase, override_config
from matrix_synapse_testutils.test_utils import simple_async_mock

from .test_config import DEFAULT_CONFIG as DEFAULT_MODULE_CFG

DEFAULT_CONFIG = {
    
    "modules": [{
        "module": "synapse_super_invites.SynapseSuperInvites",
        "config": DEFAULT_MODULE_CFG
    }]
}


# Some more local helpers
class SuperInviteHomeserverTestCase(HomeserverTestCase):


    servlets = [
        admin.register_servlets,
        login.register_servlets,
        room.register_servlets,
        profile.register_servlets,
    ]


    def prepare(self, reactor: MemoryReactor, clock: Clock, hs: HomeServer) -> None:
        self.store = hs.get_datastores().main
        self.module_api = hs.get_module_api()
        self.event_creation_handler = hs.get_event_creation_handler()
        self.sync_handler = hs.get_sync_handler()
        self.auth_handler = hs.get_auth_handler()

    def create_resource_dict(self) -> Dict[str, Resource]:
        d = super().create_resource_dict()
        for key in self.hs._module_web_resources:
            d[key] = self.hs._module_web_resources[key]
        return d

    # create a room with the given access_token, return the roomId
    def create_room(self, user_id, config={}) -> str: 
        return self.get_success(self.module_api.create_room(user_id=user_id, config=config, ratelimit=False))[0]


class SimpleInviteTests(SuperInviteHomeserverTestCase):

    @override_config(DEFAULT_CONFIG)
    def test_simple_invite_token_test(self) -> None:
        m_id = self.register_user("meeko", "password")
        m_access_token = self.login("meeko", "password")

        # this is our new backend.
        channel = self.make_request("GET", "/_synapse/client/super_invites/tokens", access_token=m_access_token)
        self.assertEqual(channel.code, 200, msg=channel.result)
        self.assertEqual(channel.json_body["tokens"], [])

        # creating five channel
        roomA = self.create_room(m_id)
        roomB = self.create_room(m_id)
        roomC = self.create_room(m_id)
        roomD = self.create_room(m_id)
        roomE = self.create_room(m_id)

        rooms_to_invite = [
            roomB,  roomC, roomD,
        ]
        # create a new one for testing.
        channel = self.make_request("POST", "/_synapse/client/super_invites/tokens", access_token=m_access_token, content={"rooms": rooms_to_invite })
        self.assertEqual(channel.code, 200, msg=channel.result)
        token_data = channel.json_body["token"]
        self.assertEqual(token_data['rooms'], rooms_to_invite)
        token = token_data["token"]

        # redeem the new token

        f_id = self.register_user("flit", "flit")
        f_access_token = self.login("flit", "flit")

        channel = self.make_request("GET", "/_synapse/client/super_invites/redeem", access_token=f_access_token, content={"token": token})
        self.assertEqual(channel.code, 200, msg=channel.result)
        self.assertEqual(channel.json_body["rooms"], rooms_to_invite)

        # and flit was invited to these, too:

        channel = self.make_request("GET", "/_matrix/sync", access_token=f_access_token)
        self.assertEqual(channel.code, 200, msg=channel.result)
        self.assertEqual(channel.json_body["rooms"]["invited"].keys(), rooms_to_invite)


    @override_config(DEFAULT_CONFIG)
    def test_simple_invite_as_registration_token_test(self) -> None:
        m_id = self.register_user("meeko", "password")
        m_access_token = self.login("meeko", "password")

        # this is our new backend.
        channel = self.make_request("GET", "/_synapse/client/super_invites/tokens", access_token=m_access_token)
        self.assertEqual(channel.code, 200, msg=channel.result)
        self.assertEqual(channel.json_body["tokens"], [])

        # create a new one for testing.
        channel = self.make_request("POST", "/_synapse/client/super_invites/tokens", {"rooms": []}, access_token=m_access_token, )
        self.assertEqual(channel.code, 200, msg=channel.result)
        token = channel.json_body["token"]

        # trying to register with that new token


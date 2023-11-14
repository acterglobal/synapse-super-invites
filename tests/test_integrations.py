from unittest import TestCase
from synapse.types import JsonDict
from matrix_synapse_testutils.unittest import HomeserverTestCase, override_config
from .test_config import DEFAULT_CONFIG as DEFAULT_MODULE_CFG

DEFAULT_CONFIG = {"modules": [{
        "module": "synapse_super_invites.SynapseSuperInvites",
        "config": DEFAULT_MODULE_CFG
    }]
}


# Some more local helpers
class SuperInviteHomeserverTestCase(HomeserverTestCase):

    # create a room with the given access_token, return the roomId
    def create_room(self, access_token, body=JsonDict) -> str: 
        channel = self.make_request("POST", " /_matrix/client/v3/createRoom", access_token=m_access_token, body=body)
        self.assertEqual(channel.code, 200, msg=channel.result)
        return channel.json_body["room_id"]


class SimpleInviteTests(SuperInviteHomeserverTestCase):

    @override_config(DEFAULT_CONFIG)
    def test_simple_invite_token_test(self) -> None:
        m_id = self.register_user("meeko", "meeko")
        m_access_token = self.login("meeko", "meeko")

        # this is our new backend.
        channel = self.make_request("GET", "/_synapse/synapse_super_invites/tokens", access_token=m_access_token)
        self.assertEqual(channel.code, 200, msg=channel.result)
        self.assertEqual(channel.json_body["tokens"], [])

        # creating five channel
        roomA = self.create_room(m_access_token)
        roomB = self.create_room(m_access_token)
        roomC = self.create_room(m_access_token)
        roomD = self.create_room(m_access_token)
        roomE = self.create_room(m_access_token)

        rooms_to_invite = [
            roomB, roomC, roomD,
        ]
        # create a new one for testing.
        channel = self.make_request("POST", "/_synapse/synapse_super_invites/tokens", access_token=m_access_token, body={"rooms": rooms_to_invite })
        self.assertEqual(channel.code, 200, msg=channel.result)
        self.assertEqual(channel.json_body['rooms'], rooms_to_invite)
        token = channel.json_body["token"]

        # redeem the new token

        f_id = self.register_user("flit", "flit")
        f_access_token = self.login("flit", "flit")

        channel = self.make_request("GET", "/_synapse/synapse_super_invites/redeem", access_token=f_access_token, body={"token": token})
        self.assertEqual(channel.code, 200, msg=channel.result)
        self.assertEqual(channel.json_body["rooms"], rooms_to_invite)

        # and flit was invited to these, too:

        channel = self.make_request("GET", "/_matrix/sync", access_token=f_access_token)
        self.assertEqual(channel.code, 200, msg=channel.result)
        self.assertEqual(channel.json_body["rooms"]["invited"].keys(), rooms_to_invite)


    @override_config(DEFAULT_CONFIG)
    def test_simple_invite_as_registration_token_test(self) -> None:
        m_id = self.register_user("meeko", "meeko")
        m_access_token = self.login("meeko", "meeko")

        # this is our new backend.
        channel = self.make_request("GET", "/_synapse/synapse_super_invites/tokens", access_token=m_access_token)
        self.assertEqual(channel.code, 200, msg=channel.result)
        self.assertEqual(channel.json_body["tokens"], [])

        # create a new one for testing.
        channel = self.make_request("POST", "/_synapse/synapse_super_invites/tokens", access_token=m_access_token, body={"rooms": []})
        self.assertEqual(channel.code, 200, msg=channel.result)
        token = channel.json_body["token"]

        # trying to register with that new token


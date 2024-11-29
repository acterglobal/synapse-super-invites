
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
    @override_config(TEST_CONFIG)  # type: ignore[misc]
    def test_basic(self) -> None:
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

        uriFormatter = "{uriPrefix}{hash}?{query}#{path}"

        targetHash = hashlib.sha1(
            uriFormatter.format(
                uriPrefix=URL_PREFIX,
                hash='',  # no hash here
                query='userId={userId}'.format(userId=m_id),
                path="o/roomId/pin/objectId",
            ).encode()
        ).hexdigest()
        self.assertEqual(channel.code, 200, msg=channel.result)
        self.assertEqual(channel.json_body["url"],
                         uriFormatter.format(
            uriPrefix=URL_PREFIX,
            hash=targetHash,  # no hash here
            query='userId={userId}'.format(userId=m_id),
            path="o/roomId/pin/objectId",
        ))


from .test_integrations import SuperInviteHomeserverTestCase

# type: ignore[import-untyped]
from matrix_synapse_testutils.unittest import override_config

from tempfile import TemporaryDirectory

test_dir = TemporaryDirectory()

TEST_CONFIG = {
    "modules": [
        {
            "module": "synapse_super_invites.SynapseSuperInvites",
            "config": {
                "sql_url": "sqlite:///",
                "link_share_generator": {
                    "url_prefix": 'https://app.example.com/p/',
                    "target_path": "test_dir.name",
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
            "POST", "/_synapse/client/share_link/", access_token=m_access_token
        )
        self.assertEqual(channel.code, 200, msg=channel.result)
        self.assertEqual(channel.json_body["tokens"], [])

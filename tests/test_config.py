from unittest import TestCase
from synapse.config import ConfigError
from synapse.types import JsonDict
from synapse_super_invites import SynapseSuperInvitesConfig, SynapseSuperInvites

DEFAULT_CONFIG = {
            "sql_url": "sqlite:///"
        }

class ConfigParsingTests(TestCase):

    def test_default_config(self) -> None:
        config = SynapseSuperInvites.parse_config(DEFAULT_CONFIG)
        self.assertEqual(config.generate_registration_token, True)

    def test_fails_no_sql(self) -> None:
        with self.assertRaises(ConfigError):
            SynapseSuperInvites.parse_config({})

    def test_disable_registration_token(self) -> None:
        config = SynapseSuperInvites.parse_config({"sql_url": "sqlite:///", "generate_registration_token": False})
        self.assertEqual(config.generate_registration_token, False)
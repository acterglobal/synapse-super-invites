from unittest import TestCase
from synapse.types import JsonDict
from synapse_super_invites import SynapseSuperInvitesConfig, SynapseSuperInvites

class ConfigParsingTests(TestCase):

    def test_default_config(self) -> None:
        config = SynapseSuperInvites.parse_config({})
        self.assertEqual(config.generate_registration_token, True)

    def test_disable_registration_token(self) -> None:
        config = SynapseSuperInvites.parse_config({"generate_registration_token": False})
        self.assertEqual(config.generate_registration_token, False)

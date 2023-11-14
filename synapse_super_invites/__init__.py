from typing import Any, Dict

import attr
from synapse.config import ConfigError
from synapse.module_api import ModuleApi


@attr.define
class SynapseSuperInvitesConfig:
    sql_url: str
    generate_registration_token : bool = attr.field(default = True)


class SynapseSuperInvites:
    def __init__(self, config: SynapseSuperInvitesConfig, api: ModuleApi):
        # Keep a reference to the config and Module API
        self._api = api
        self._config = config

    @staticmethod
    def parse_config(config: Dict[str, Any]) -> SynapseSuperInvitesConfig:
        try:
            return SynapseSuperInvitesConfig(**config)
        except TypeError as e:
            raise ConfigError(e)

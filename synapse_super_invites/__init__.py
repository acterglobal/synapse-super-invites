from typing import Any, Dict

import attr
import os
from synapse.config import ConfigError
from synapse.module_api import ModuleApi
from twisted.web.static import File

import alembic.config
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .config import run_alembic, SynapseSuperInvitesConfig
from .model import Token
from .resource import TokensResource, RedeemResource

PKG_DIR = os.path.dirname(os.path.realpath(__file__)) 

class SynapseSuperInvites:
    def __init__(self, config: SynapseSuperInvitesConfig, api: ModuleApi):
        # Keep a reference to the config and Module API
        engine = create_engine(config.sql_url)
        run_alembic(engine)
        self._sessions = sessionmaker(engine)
        self._api = api
        self._config = config
        self.setup()

    def setup(self):
        self._api.register_web_resource('/_synapse/client/super_invites/static', File(os.path.join(PKG_DIR, "static")))
        self._api.register_web_resource('/_synapse/client/super_invites/tokens', TokensResource(self._config, self._api, self._sessions))
        self._api.register_web_resource('/_synapse/client/super_invites/redeem', RedeemResource(self._config, self._api, self._sessions))
        

    @staticmethod
    def parse_config(config: Dict[str, Any]) -> SynapseSuperInvitesConfig:
        try:
            return SynapseSuperInvitesConfig(**config)
        except TypeError as e:
            raise ConfigError(e)

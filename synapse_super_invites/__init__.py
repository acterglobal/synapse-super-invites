import os
from typing import Any, Dict

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from synapse.config import ConfigError
from synapse.module_api import ModuleApi
from twisted.web.static import File

from .config import SynapseSuperInvitesConfig, ShareLinkGeneratorConfig,  run_alembic
from .resource import (
    RedeemResource,
    TokenInfoResource,
    TokensResource,
    WebAccessResource,
    ShareLink,
)

__version__ = "0.8.4"

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

    def setup(self) -> None:
        self._api.register_web_resource(
            "/_synapse/client/super_invites/info",
            TokenInfoResource(self._config, self._api, self._sessions),
        )
        self._api.register_web_resource(
            "/_synapse/client/super_invites/tokens",
            TokensResource(self._config, self._api, self._sessions),
        )
        self._api.register_web_resource(
            "/_synapse/client/super_invites/redeem",
            RedeemResource(self._config, self._api, self._sessions),
        )

        if self._config.enable_web:
            self._api.register_web_resource(
                "/_synapse/client/super_invites/access.js",
                WebAccessResource(self._api),
            )
            self._api.register_web_resource(
                "/_synapse/client/super_invites",
                File(os.path.join(PKG_DIR, "static/")),
            )

        if self._config.share_link_generator is not None:
            self._api.register_web_resource(
                "/_synapse/client/share_link/",
                ShareLink(self._config.share_link_generator,
                          self._api),
            )

    @staticmethod
    def parse_config(config: Dict[str, Any]) -> SynapseSuperInvitesConfig:
        share_link_cfg = config.get('share_link_generator', None)
        if share_link_cfg is not None:
            try:
                config['share_link_generator'] = ShareLinkGeneratorConfig(
                    **share_link_cfg)
            except TypeError as e:
                raise ConfigError(str(e))

        try:
            return SynapseSuperInvitesConfig(**config)
        except TypeError as e:
            raise ConfigError(str(e))

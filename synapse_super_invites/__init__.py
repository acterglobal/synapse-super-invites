from typing import Any, Dict

import attr
import os
from synapse.config import ConfigError
from synapse.module_api import ModuleApi

import alembic.config
from .model import Token

def do_upgrade(revision, context):
    return alembic_script._upgrade_revs(script.get_heads(), revision)

def run_alembic(sql_url):
    from alembic.config import Config
    from alembic import command, autogenerate
    from alembic.script import ScriptDirectory
    from alembic.runtime.environment import EnvironmentContext

    alembic_cfg = Config()
    alembic_cfg.set_main_option("script_location", os.path.join(os.path.dirname(os.path.realpath(__file__)), "migration"))
    alembic_cfg.set_main_option("sqlalchemy.url", sql_url)
    alembic.command.upgrade(alembic_cfg, 'head')

@attr.define
class SynapseSuperInvitesConfig:
    sql_url: str
    generate_registration_token : bool = attr.field(default = True)


class SynapseSuperInvites:
    def __init__(self, config: SynapseSuperInvitesConfig, api: ModuleApi):
        # Keep a reference to the config and Module API
        run_alembic(config.sql_url)
        self._api = api
        self._config = config

    @staticmethod
    def parse_config(config: Dict[str, Any]) -> SynapseSuperInvitesConfig:
        try:
            return SynapseSuperInvitesConfig(**config)
        except TypeError as e:
            raise ConfigError(e)

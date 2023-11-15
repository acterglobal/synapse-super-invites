import os

import alembic.config
import attr

PKG_DIR = os.path.dirname(os.path.realpath(__file__))


def run_alembic(engine):
    from alembic.config import Config

    alembic_cfg = Config(os.path.join(PKG_DIR, "..", "alembic.ini"))
    alembic_cfg.set_main_option("script_location", os.path.join(PKG_DIR, "migration"))

    with engine.begin() as connection:
        alembic_cfg.attributes["connection"] = connection
        alembic.command.upgrade(alembic_cfg, "head")


@attr.define
class SynapseSuperInvitesConfig:
    sql_url: str
    generate_registration_token: bool = attr.field(default=False)

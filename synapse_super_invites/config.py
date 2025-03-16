import os

import alembic
import attr
from alembic.config import Config
from sqlalchemy import Engine

PKG_DIR = os.path.dirname(os.path.realpath(__file__))


def run_alembic(engine: Engine) -> None:
    alembic_cfg = Config(os.path.join(PKG_DIR, "alembic.ini"))
    alembic_cfg.set_main_option(
        "script_location", os.path.join(PKG_DIR, "migration"))

    with engine.begin() as connection:
        alembic_cfg.attributes["connection"] = connection
        alembic.command.upgrade(alembic_cfg, "head")


@attr.define
class ShareLinkGeneratorConfig:
    url_prefix: str
    target_path: str
    template_path: str | None = attr.field(default=None)


@attr.define
class SynapseSuperInvitesConfig:
    sql_url: str
    generate_registration_token: bool = attr.field(default=False)
    enable_web: bool = attr.field(default=False)
    share_link_generator: ShareLinkGeneratorConfig | None = attr.field(
        default=None)

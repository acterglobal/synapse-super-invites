from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from synapse.http.server import (
    DirectServeJsonResource,
)
from synapse.module_api import ModuleApi
from synapse.types import JsonDict, Requester

from synapse_super_invites.config import SynapseSuperInvitesConfig
from synapse_super_invites.model import Token


def can_edit_token(token: Token, requester: Requester) -> bool:
    # kept outside so we can make it more sophisticated later
    return token.owner == str(requester.user)


def serialize_token(token: Token) -> JsonDict:
    return {
        "token": token.token,
        "create_dm": token.create_dm,
        "accepted_count": len(token.accepted),
        "rooms": [r.nameOrAlias for r in token.rooms],
    }


def token_query(token_id: str):  # type: ignore[no-untyped-def]
    return select(Token).where(
        Token.token == token_id, Token.deleted_at == None  # noqa: E711
    )


class SuperInviteResourceBase(DirectServeJsonResource):
    def __init__(
        self, config: SynapseSuperInvitesConfig, api: ModuleApi, sessions: sessionmaker  # type: ignore[type-arg]
    ):
        super().__init__()
        self.config = config
        self.api = api
        self.db = sessions

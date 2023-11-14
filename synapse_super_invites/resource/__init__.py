
from twisted.application.internet import TCPServer
from twisted.application.service import Application
from twisted.web.resource import Resource
from twisted.web.server import Site

from synapse.types import Tuple, JsonDict
from synapse.http.site import SynapseRequest
from synapse.http.server import DirectServeJsonResource
from synapse.module_api import ModuleApi

from synapse_super_invites.config import SynapseSuperInvitesConfig
from synapse_super_invites.model import Token, Room

from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select


class TokensPage(DirectServeJsonResource):

    def __init__(self, config: SynapseSuperInvitesConfig, api: ModuleApi, sessions: sessionmaker):
        super().__init__()
        self.config = config
        self.api = api
        self.db = sessions

    async def _async_render_GET(self, request: SynapseRequest) -> Tuple[int, JsonDict]:
        requester = await self.api.get_user_by_req(request, allow_guest=False)
        tokens = []
        with self.db.begin() as session:
            for token in session.scalars(select(Token).where(Token.owner==str(requester.user))).all():
                tokens.push({
                    "token": token.token,
                    # "rooms": token.rooms,
                })
        return 200, {"tokens": tokens}
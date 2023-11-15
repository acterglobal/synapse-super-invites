
from twisted.application.internet import TCPServer
from twisted.application.service import Application
from twisted.web.resource import Resource
from twisted.web.server import Site

from synapse.types import Tuple, JsonDict, Requester
from synapse.http.site import SynapseRequest
from synapse.http.servlet import parse_json_object_from_request
from synapse.http.server import DirectServeJsonResource
from synapse.module_api import ModuleApi

from synapse_super_invites.config import SynapseSuperInvitesConfig
from synapse_super_invites.model import Token, Room

from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, insert, update

def can_edit_token(token: Token, requester: Requester) -> bool:
    # kept outside so we can make it more sophisticated later
    return token.owner == str(requester.user_id)

def serialize_token(token: Token) -> JsonDict:
    return {"token" : token.token, "create_dm": token.create_dm, "rooms": [] }



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
                tokens.push(serialize_token(token))
        return 200, {"tokens": tokens}

    async def _async_render_POST(self, request: SynapseRequest) -> Tuple[int, JsonDict]:
        requester = await self.api.get_user_by_req(request, allow_guest=False)
        payload = parse_json_object_from_request(request)
        token_id = payload.get("token", None)
        rooms = payload.get("rooms", [])
        create_dm = payload.get("create_dm", False)
        token_data = None
        with self.db.begin() as session:

            token = None
            if token_id: 
                token = session.scalar(select(Token).where(Token.token==token_id)).one()
            
                if token:
                    # check if we have the permission
                    if not can_edit_token(token, requester):
                        return 403, {"error": "Permission denied", "errcode": ""}

                    # token.rooms = rooms
                    token.create_dm = create_dm
                    session.execute(update(token))
                    session.flush()

            if not token:
                token = Token(token=token_id, create_dm=create_dm, owner=str(requester.user))
                session.add(token)
                session.flush()

            token_data = serialize_token(token)
        
        return 200, {"token": token_data}
        

from twisted.application.internet import TCPServer
from twisted.application.service import Application
from twisted.web.resource import Resource
from twisted.web.server import Site

from synapse.types import Tuple, JsonDict, Requester
from synapse.http.site import SynapseRequest
from synapse.http.servlet import parse_json_object_from_request, parse_string
from synapse.http.server import DirectServeJsonResource
from synapse.module_api import ModuleApi

from synapse_super_invites.config import SynapseSuperInvitesConfig
from synapse_super_invites.model import Token, Room, Accepted

from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, insert, update

def can_edit_token(token: Token, requester: Requester) -> bool:
    # kept outside so we can make it more sophisticated later
    return token.owner == str(requester.user)

def serialize_token(token: Token) -> JsonDict:
    return {"token" : token.token, "create_dm": token.create_dm, "accepted_count": len(token.accepted), "rooms": list(map(lambda r: r.nameOrAlias, token.rooms))}


def token_query(token_id: str):
    return select(Token).where(Token.token==token_id)

class SuperInviteResourceBase(DirectServeJsonResource):

    def __init__(self, config: SynapseSuperInvitesConfig, api: ModuleApi, sessions: sessionmaker):
        super().__init__()
        self.config = config
        self.api = api
        self.db = sessions


class TokensResource(SuperInviteResourceBase):

    async def _async_render_GET(self, request: SynapseRequest) -> Tuple[int, JsonDict]:
        requester = await self.api.get_user_by_req(request, allow_guest=False)

        token_id = parse_string(request, "token")
        # query for a specific token
        if token_id:
            token_data = None
            with self.db.begin() as session:
                token = session.scalar(token_query(token_id))
                if not token:
                    return 404, {"error": "Token not found", "errcode": "NOT_FOUND"}
                if not can_edit_token(token, requester):
                    return 403, {"error": "Permission denied", "errcode": ""}

                token_data = serialize_token(token)

            return 200, {"token": token_data }
                
        # by default, we list all tokens
        tokens = []
        with self.db.begin() as session:
            for token in session.scalars(select(Token).where(Token.owner==str(requester.user))).all():
                tokens.push(serialize_token(token))
        return 200, {"tokens": tokens}

    async def _async_render_POST(self, request: SynapseRequest) -> Tuple[int, JsonDict]:
        requester = await self.api.get_user_by_req(request, allow_guest=False)
        payload = parse_json_object_from_request(request)
        token_id = payload.get("token", None)
        create_dm = payload.get("create_dm", False)

        token_data = None
        with self.db.begin() as session:

            rooms = list(map(lambda key: session.merge(Room(nameOrAlias = key)), payload.get("rooms", [])))

            token = None
            if token_id: 
                token = session.scalar(select(Token).where(Token.token==token_id))
            
                if token:
                    # check if we have the permission
                    if not can_edit_token(token, requester):
                        return 403, {"error": "Permission denied", "errcode": ""}

                    # token.rooms = rooms
                    token.create_dm = create_dm
                    token.rooms = rooms

            if not token:
                token = Token(token=token_id, create_dm=create_dm, owner=str(requester.user), rooms=rooms)
                session.add(token)


            session.flush()

            token_data = serialize_token(token)

        if self.config.generate_registration_token:
            token_id = token_data["token"]
            # FIXME: it'd be great if we didn't have to resort to using internal args...
            if not (await self.api._store.registration_token_is_valid(token_id)):
                await self.api._store.create_registration_token(token=token_id, uses_allowed=None, expiry_time=None)
        
        return 200, {"token": token_data}
        

class RedeemResource(SuperInviteResourceBase):

    async def _async_render_POST(self, request: SynapseRequest) -> Tuple[int, JsonDict]:
        requester = await self.api.get_user_by_req(request, allow_guest=False)
        my_id = str(requester.user)
        token_id = parse_string(request, "token", required=True)
        invited_rooms = []
        with self.db.begin() as session:
            token = session.scalar(token_query(token_id))
            if not token:
                return 404, {"error": "Token not found", "errcode": "NOT_FOUND"}

            owner = token.owner
            for room in token.rooms:
                await self.api.update_room_membership(sender=owner, target=my_id, room_id=room.nameOrAlias, new_membership = "invite")
                invited_rooms.append(room.nameOrAlias)

            if token.create_dm:
                dm_data = await self.api.create_room(my_id, config={"preset": "trusted_private_chat", "invite": [owner]})
                invited_rooms.append(dm_data[0])

            # keep the accepted record
            session.add(Accepted(token=token, user=my_id))
            session.flush()

        return 200, {"rooms": invited_rooms}

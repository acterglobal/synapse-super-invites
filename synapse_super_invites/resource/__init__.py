from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker
from synapse.http.server import (
    DirectServeHtmlResource,
    DirectServeJsonResource,
    finish_request,
    logger,
    set_clickjacking_protection_headers,
)
from synapse.http.servlet import parse_json_object_from_request, parse_string
from synapse.http.site import SynapseRequest
from synapse.module_api import ModuleApi
from synapse.types import Any, JsonDict, Requester, Tuple  # type: ignore[attr-defined]

from synapse_super_invites.config import SynapseSuperInvitesConfig
from synapse_super_invites.model import Accepted, Room, Token


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


class AccessResource(DirectServeHtmlResource):
    def __init__(
        self,
        api: ModuleApi,
    ):
        super().__init__()
        self.api = api

    def _send_response(
        self,
        request: "SynapseRequest",
        code: int,
        response_object: Any,
    ) -> None:
        """Implements _AsyncResource._send_response"""
        # We expect to get bytes for us to write
        assert isinstance(response_object, bytes)
        js_bytes = response_object

        # The response code must always be set, for logging purposes.
        request.setResponseCode(code)

        # could alternatively use request.notifyFinish() and flip a flag when
        # the Deferred fires, but since the flag is RIGHT THERE it seems like
        # a waste.
        if request._disconnected:
            logger.warning(
                "Not sending response to request %s, already disconnected.", request
            )
            return None

        request.setHeader(b"Content-Type", b"text/javascript; charset=utf-8")
        request.setHeader(b"Content-Length", b"%d" % (len(js_bytes),))

        # Ensure this content cannot be embedded.
        set_clickjacking_protection_headers(request)

        request.write(js_bytes)
        finish_request(request)

    async def _async_render_GET(self, request: SynapseRequest) -> Tuple[int, JsonDict]:
        # ensure logged int
        _requester = await self.api.get_user_by_req(request, allow_guest=False)
        access_token = await self.api._auth.get_access_token_from_request(request)
        return 200, 'startApp("{t}")'.format(t=access_token)


class SuperInviteResourceBase(DirectServeJsonResource):
    def __init__(
        self, config: SynapseSuperInvitesConfig, api: ModuleApi, sessions: sessionmaker  # type: ignore[type-arg]
    ):
        super().__init__()
        self.config = config
        self.api = api
        self.db = sessions


class TokensResource(SuperInviteResourceBase):
    async def _async_render_DELETE(
        self, request: SynapseRequest
    ) -> Tuple[int, JsonDict]:
        requester = await self.api.get_user_by_req(request, allow_guest=False)

        token_id = parse_string(request, "token", required=True)
        # query for a specific token
        with self.db.begin() as session:
            token = session.scalar(token_query(token_id))
            if not token:
                return 404, {"error": "Token not found", "errcode": "NOT_FOUND"}
            if not can_edit_token(token, requester):
                return 403, {"error": "Permission denied", "errcode": ""}

            token.deleted_at = func.now()
            session.flush()

        return 200, {}

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

            return 200, {"token": token_data}

        # by default, we list all tokens
        tokens = []
        with self.db.begin() as session:
            for token in session.scalars(
                select(Token).where(
                    Token.owner == str(requester.user),
                    Token.deleted_at == None,  # noqa: E711
                )
            ).all():
                tokens.append(serialize_token(token))
        return 200, {"tokens": tokens}

    async def _async_render_POST(self, request: SynapseRequest) -> Tuple[int, JsonDict]:
        requester = await self.api.get_user_by_req(request, allow_guest=False)
        payload = parse_json_object_from_request(request)
        token_id = payload.get("token", None)
        create_dm = payload.get("create_dm", False)

        token_data = None
        with self.db.begin() as session:
            rooms = [
                session.merge(Room(nameOrAlias=key)) for key in payload.get("rooms", [])
            ]

            token = None
            if token_id:
                token = session.scalar(select(Token).where(Token.token == token_id))

                if token:
                    # check if we have the permission
                    if not can_edit_token(token, requester):
                        return 403, {"error": "Permission denied", "errcode": ""}

                    # token.rooms = rooms
                    token.create_dm = create_dm
                    token.rooms = rooms

            if not token:
                token = Token(
                    token=token_id,
                    create_dm=create_dm,
                    owner=str(requester.user),
                    rooms=rooms,
                )
                session.add(token)

            session.flush()

            token_data = serialize_token(token)

        if self.config.generate_registration_token:
            token_id = token_data["token"]
            # FIXME: it'd be great if we didn't have to resort to using internal args...
            if not (await self.api._store.registration_token_is_valid(token_id)):
                await self.api._store.create_registration_token(
                    token=token_id, uses_allowed=None, expiry_time=None
                )

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

            if session.scalar(
                select(Accepted).where(Accepted.user == my_id, Accepted.token == token)
            ):
                return 400, {
                    "error": "Token already redeemed found",
                    "errcode": "ALREADY_REDEEMED",
                }

            if token.owner == my_id:
                return 400, {
                    "error": "Can't redeem your own token",
                    "errcode": "CANT_REDEEM",
                }

            owner = token.owner
            for room in token.rooms:
                await self.api.update_room_membership(
                    sender=owner,
                    target=my_id,
                    room_id=room.nameOrAlias,
                    new_membership="invite",
                )

                await self.api.update_room_membership(
                    sender=my_id,
                    target=my_id,
                    room_id=room.nameOrAlias,
                    new_membership="join",
                )
                invited_rooms.append(room.nameOrAlias)

            if token.create_dm:
                dm_data = await self.api.create_room(
                    my_id, config={"preset": "trusted_private_chat", "invite": [owner]}
                )
                invited_rooms.append(dm_data[0])

            # keep the accepted record
            session.add(Accepted(token=token, user=my_id))
            session.flush()

        return 200, {"rooms": invited_rooms}

from typing import Any

from sqlalchemy import func, select
from synapse.http.servlet import parse_json_object_from_request, parse_string
from synapse.http.site import SynapseRequest
from synapse.types import JsonDict, Tuple  # type: ignore[attr-defined]

from synapse_super_invites.model import Room, Token

from .base import SuperInviteResourceBase, can_edit_token, serialize_token, token_query


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
        as_registration_token = payload.get("as_registration_token", True)

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

        registration_token: dict[Any, Any] = {}
        if as_registration_token:
            if not self.config.generate_registration_token:
                registration_token["valid"] = False
                registration_token["reason"] = "NOT_ENABLED"
            else:
                token_id = token_data["token"]
                # FIXME: it'd be great if we didn't have to resort to using internal args...
                if not (await self.api._store.registration_token_is_valid(token_id)):
                    await self.api._store.create_registration_token(
                        token=token_id, uses_allowed=None, expiry_time=None
                    )
                    registration_token["valid"] = True
                else:
                    registration_token["valid"] = True
        else:
            registration_token["valid"] = False
            registration_token["reason"] = "NOT_REQUESTED"

        return 200, {"token": token_data, "registration_token": registration_token}

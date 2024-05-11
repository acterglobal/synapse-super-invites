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

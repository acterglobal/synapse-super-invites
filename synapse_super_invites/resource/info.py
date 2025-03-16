from sqlalchemy import select
from synapse.http.servlet import parse_string
from synapse.http.site import SynapseRequest
from synapse.types import JsonDict, Tuple, UserID  # type: ignore[attr-defined]

from synapse_super_invites.model import Accepted, Token
from .base import SuperInviteResourceBase


class TokenInfoResource(SuperInviteResourceBase):
    async def _async_render_GET(self, request: SynapseRequest) -> Tuple[int, JsonDict]:
        requester = await self.api.get_user_by_req(request, allow_guest=False)
        my_id = str(requester.user)
        token_id = parse_string(request, "token", required=True)
        with self.db.begin() as session:
            token = session.scalar(
                select(Token).where(Token.token == token_id)  # noqa: E711
            )
            if not token:
                return 403, {"error": "Token not found", "errcode": "NOT_FOUND"}

            if token.deleted_at is not None:
                return 403, {
                    "error": "Token not longer valid",
                    "errcode": "CANT_REDEEM",
                }

            has_redeemed = (
                session.scalar(
                    select(Accepted).where(
                        Accepted.user == my_id, Accepted.token == token
                    )
                )
                is not None
            )

            rooms_count = len(token.rooms)
            if token.create_dm:
                rooms_count += 1

            user_id = token.owner
            owner_info = await self.api._store.get_profileinfo(
                UserID.from_string(user_id)
            )

            return 200, {
                "rooms_count": rooms_count,
                "has_redeemed": has_redeemed,
                "create_dm": token.create_dm,
                "inviter": {
                    "user_id": user_id,
                    "display_name": owner_info.display_name,
                    "avatar_url": owner_info.avatar_url,
                },
            }

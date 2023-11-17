from sqlalchemy import select
from synapse.http.servlet import parse_string
from synapse.http.site import SynapseRequest
from synapse.types import JsonDict, Tuple  # type: ignore[attr-defined]

from synapse_super_invites.model import Accepted

from .base import SuperInviteResourceBase, token_query


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

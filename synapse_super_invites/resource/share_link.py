import re
import hashlib
from synapse.http.server import (
    DirectServeHtmlResource,
    finish_request,
    logger,
    set_clickjacking_protection_headers,
    DirectServeJsonResource,
)
from synapse.http.site import SynapseRequest
from synapse.http.servlet import parse_json_object_from_request, parse_string
from synapse.module_api import ModuleApi
from ..config import ShareLinkGeneratorConfig
from string import Template
# type: ignore[attr-defined]
from synapse.types import Dict, Any, Tuple, JsonDict, Requester


user_id_query_matcher = re.compile(r'(?:^|&)userId=[^&]*&?')

uriFormatter = "{uriPrefix}{hash}?{query}#{path}"


class ShareLink(DirectServeJsonResource):
    def __init__(
        # type: ignore[type-arg]
        self, config: ShareLinkGeneratorConfig, api: ModuleApi
    ):
        super().__init__()
        self.config = config
        if config.template_path is not None:
            pass
        self.api = api

    def _gen_uri(self, user_id: str, path: str, query=None) -> Tuple[str, str]:
        if query is not None and len(query) > 0:
            q = '{query}&userId={user_id}'.format(
                # there was a userId in the query, remove it.
                query=re.sub(user_id_query_matcher, '', query),
                user_id=user_id)
        else:
            q = 'userId={user_id}'.format(user_id=user_id)
        url_prefix = self.config.url_prefix
        uriHash = hashlib.sha1(
            uriFormatter.format(
                uriPrefix=url_prefix,
                hash='',  # no hash here
                query=q,
                path=path,
            ).encode()
        ).hexdigest()

        return uriHash, uriFormatter.format(
            uriPrefix=url_prefix,
            hash=uriHash,
            query=q,
            path=path,
        )

    def _gen_spaceObject(self, requester: Requester, payload: Dict[str, Any]) -> Tuple[int, JsonDict]:
        path = "o/{roomId}/{objectType}/{objectId}".format(**payload)
        user_id = requester.user.to_string()[1:]  # w/o leading 0;
        _uriHash, final_url = self._gen_uri(
            user_id=user_id, path=path, query=payload.get('query'))

        return 200, {
            'url': final_url
        }

    def _gen_superInvite(self, requester: Requester, payload: Dict[str, Any]) -> Tuple[int, JsonDict]:
        path = "i/{server}/{inviteCode}".format(**payload)
        user_id = requester.user.to_string()[1:]  # w/o leading 0;
        _uriHash, final_url = self._gen_uri(
            user_id=user_id, path=path, query=payload.get('query'))

        return 200, {
            'url': final_url
        }

    def _gen_roomId(self, requester: Requester, payload: Dict[str, Any]) -> Tuple[int, JsonDict]:
        path = "roomid/{roomId}".format(**payload)
        user_id = requester.user.to_string()[1:]  # w/o leading 0;
        _uriHash, final_url = self._gen_uri(
            user_id=user_id, path=path, query=payload.get('query'))

        return 200, {
            'url': final_url
        }

    def _gen_roomAlias(self, requester: Requester, payload: Dict[str, Any]) -> Tuple[int, JsonDict]:
        path = "r/{roomAlias}".format(**payload)
        user_id = requester.user.to_string()[1:]  # w/o leading 0;
        _uriHash, final_url = self._gen_uri(
            user_id=user_id, path=path, query=payload.get('query'))

        return 200, {
            'url': final_url
        }

    def _gen_userId(self, requester: Requester, payload: Dict[str, Any]) -> Tuple[int, JsonDict]:
        path = "u/{userId}".format(**payload)
        user_id = requester.user.to_string()[1:]  # w/o leading 0;
        _uriHash, final_url = self._gen_uri(
            user_id=user_id, path=path, query=payload.get('query'))

        return 200, {
            'url': final_url
        }

    async def _async_render_PUT(self, request: SynapseRequest) -> Tuple[int, JsonDict]:
        # ensure logged int
        requester = await self.api.get_user_by_req(request, allow_guest=False)
        payload = parse_json_object_from_request(request)
        uri_type = payload.get('type', None)
        if uri_type == "spaceObject":
            return self._gen_spaceObject(requester, payload)
        elif uri_type == "superInvite":
            return self._gen_superInvite(requester, payload)
        elif uri_type == "roomId":
            return self._gen_roomId(requester, payload)
        elif uri_type == "roomAlias":
            return self._gen_roomAlias(requester, payload)
        elif uri_type == "userId":
            return self._gen_userId(requester, payload)
        else:
            return 403, {
                "error": "unsupported object type='{uri_type}' ".format(uri_type=uri_type),
                "errcode": "NOT_SUPPORTED",
            }

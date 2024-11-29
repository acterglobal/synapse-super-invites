from ..config import ShareLinkGeneratorConfig
from string import Template
from synapse.types import Any, Tuple, JsonDict  # type: ignore[attr-defined]
from synapse.module_api import ModuleApi
from synapse.http.servlet import parse_json_object_from_request, parse_string
from synapse.http.site import SynapseRequest
from synapse.http.server import (
    DirectServeHtmlResource,
    finish_request,
    logger,
    set_clickjacking_protection_headers,
    DirectServeJsonResource,
)

import hashlib

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

    async def _async_render_PUT(self, request: SynapseRequest) -> Tuple[int, JsonDict]:
        # ensure logged int
        requester = await self.api.get_user_by_req(request, allow_guest=False)
        payload = parse_json_object_from_request(request)
        url_prefix = self.config.url_prefix
        uri_type = payload.get('type', None)
        if uri_type == "spaceObject":
            path = "o/{roomId}/{objectType}/{objectId}".format(**payload)

        else:
            return 403, {
                "error": "unsupported object type='{uri_type}' ".format(uri_type=uri_type),
                "errcode": "NOT_SUPPORTED",
            }

        query = 'userId={userId}'.format(userId=requester.user.to_string())
        uriHash = hashlib.sha1(
            uriFormatter.format(
                uriPrefix=url_prefix,
                hash='',  # no hash here
                query=query,
                path=path,
            ).encode()
        ).hexdigest()

        final_url = uriFormatter.format(
            uriPrefix=url_prefix,
            hash=uriHash,
            query=query,
            path=path,
        )

        return 200, {
            'url': final_url
        }

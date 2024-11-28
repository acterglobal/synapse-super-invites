from synapse.http.server import (
    DirectServeHtmlResource,
    finish_request,
    logger,
    set_clickjacking_protection_headers,
)
from synapse.http.site import SynapseRequest
from synapse.module_api import ModuleApi
from synapse.types import Any, Tuple  # type: ignore[attr-defined]
from string import Template


class ShareLink(DirectServeJsonResource):
    def __init__(
        # type: ignore[type-arg]
        self, config: ShareLinkGeneratorConfig, api: ModuleApi, sessions: sessionmaker
    ):
        super().__init__()
        self.config = config
        if config.template_path is not None:
            pass
        self.api = api
        self.db = sessions

    async def _async_render_GET(self, request: SynapseRequest) -> Tuple[int, str]:
        # ensure logged int
        _requester = await self.api.get_user_by_req(request, allow_guest=False)
        access_token = self.api._auth.get_access_token_from_request(request)
        return 200, 'startApp("{t}")'.format(t=access_token)

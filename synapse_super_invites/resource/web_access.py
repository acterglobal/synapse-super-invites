from synapse.http.server import (
    DirectServeHtmlResource,
    finish_request,
    logger,
    set_clickjacking_protection_headers,
)
from synapse.http.site import SynapseRequest
from synapse.module_api import ModuleApi
from synapse.types import Any, Tuple  # type: ignore[attr-defined]


class WebAccessResource(DirectServeHtmlResource):
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
        request.setResponseCode(code)  # type: ignore[no-untyped-call]

        # could alternatively use request.notifyFinish() and flip a flag when
        # the Deferred fires, but since the flag is RIGHT THERE it seems like
        # a waste.
        if request._disconnected:
            logger.warning(
                "Not sending response to request %s, already disconnected.", request
            )
            return None

        request.setHeader(b"Content-Type", b"text/javascript; charset=utf-8")  # type: ignore[no-untyped-call]
        request.setHeader(b"Content-Length", b"%d" % (len(js_bytes),))  # type: ignore[no-untyped-call]

        # Ensure this content cannot be embedded.
        set_clickjacking_protection_headers(request)

        request.write(js_bytes)  # type: ignore[no-untyped-call]
        finish_request(request)

    async def _async_render_GET(self, request: SynapseRequest) -> Tuple[int, str]:
        # ensure logged int
        _requester = await self.api.get_user_by_req(request, allow_guest=False)
        access_token = self.api._auth.get_access_token_from_request(request)
        return 200, 'startApp("{t}")'.format(t=access_token)

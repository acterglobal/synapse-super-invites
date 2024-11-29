from synapse.types import Dict, Any, Tuple, JsonDict, Requester
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

from jinja2 import (
    Environment,
    PackageLoader,
    ChoiceLoader,
    FileSystemLoader,
    select_autoescape,
)
from PIL import Image, ImageDraw, ImageFont
import qrcode
import qrcode.image.svg
import os

MY_DIR = os.path.dirname(os.path.realpath(__file__))

# type: ignore[attr-defined]

user_id_query_matcher = re.compile(r'(?:^|&)userId=[^&]*&?')

uriFormatter = "{uriPrefix}{hash}?{query}#{path}"
acterUriFormatter = "acter:{path}?{query}"


class ShareLink(DirectServeJsonResource):
    def __init__(
        # type: ignore[type-arg]
        self, config: ShareLinkGeneratorConfig, api: ModuleApi
    ):
        super().__init__()
        self.config = config
        loaders = [PackageLoader("synapse_super_invites")]
        if config.template_path is not None:
            loaders.insert(0, FileSystemLoader(config.template_path))

        self.env = Environment(
            loader=ChoiceLoader(loaders),
            autoescape=select_autoescape()
        )
        self.template = self.env.get_template("share_link.html")
        self.dir_path = config.target_path
        self.api = api

    def _generate_qrcode(self, uri: str) -> str:
        qr = qrcode.QRCode(image_factory=qrcode.image.svg.SvgPathFillImage)
        qr.add_data(uri)
        qr.make(fit=True)
        img = qr.make_image()
        return img.to_string(encoding='unicode')

    def _generate_image(self, targetHash: str, **params):
        im = PIL.Image.new('RGB', (1200, 630), 'white')
        file_name = os.path.join(
            self.dir_path, '{fn}.png'.format(fn=targetHash))
        with open(file_name, mode='w') as f:
            im.save(f)

    def _generate_template(self, targetHash: str, **params):
        file_name = os.path.join(
            self.dir_path, '{fn}.html'.format(fn=targetHash))
        with open(file_name, mode='w') as f:
            f.write(self.template.render(**params))

    def _gen_uri(self, user_id: str, path: str, query=None) -> Tuple[str, str, str]:
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

        return uriHash, acterUriFormatter.format(
            query=q, path=path
        ), uriFormatter.format(
            uriPrefix=url_prefix,
            hash=uriHash,
            query=q,
            path=path,
        )

    def _gen_spaceObject(self, requester: Requester, payload: Dict[str, Any]) -> Tuple[int, JsonDict]:

        path = "o/{roomId}/{objectType}/{objectId}".format(**payload)
        user_id = requester.user.to_string()[1:]  # w/o leading 0;
        targetHash, acter_uri, final_url = self._gen_uri(
            user_id=user_id, path=path, query=payload.get('query'))

        qrcode = self._generate_qrcode(acter_uri)
        self._generate_template(targetHash,
                                url=final_url,
                                acter_uri=acter_uri,
                                qrcode=qrcode
                                )

        return 200, {
            'url': final_url,
            'targetUri': acter_uri,
        }

    def _gen_superInvite(self, requester: Requester, payload: Dict[str, Any]) -> Tuple[int, JsonDict]:
        path = "i/{server}/{inviteCode}".format(**payload)
        user_id = requester.user.to_string()[1:]  # w/o leading 0;
        targetHash, acter_uri, final_url = self._gen_uri(
            user_id=user_id, path=path, query=payload.get('query'))

        qrcode = self._generate_qrcode(acter_uri)
        self._generate_template(targetHash,
                                url=final_url,
                                acter_uri=acter_uri,
                                qrcode=qrcode
                                )

        return 200, {
            'url': final_url,
            'targetUri': acter_uri,
        }

    def _gen_roomId(self, requester: Requester, payload: Dict[str, Any]) -> Tuple[int, JsonDict]:
        path = "roomid/{roomId}".format(**payload)
        user_id = requester.user.to_string()[1:]  # w/o leading 0;
        targetHash, acter_uri, final_url = self._gen_uri(
            user_id=user_id, path=path, query=payload.get('query'))

        qrcode = self._generate_qrcode(acter_uri)
        self._generate_template(targetHash,
                                url=final_url,
                                acter_uri=acter_uri,
                                qrcode=qrcode
                                )

        return 200, {
            'url': final_url,
            'targetUri': acter_uri,
        }

    def _gen_roomAlias(self, requester: Requester, payload: Dict[str, Any]) -> Tuple[int, JsonDict]:
        path = "r/{roomAlias}".format(**payload)
        user_id = requester.user.to_string()[1:]  # w/o leading 0;
        targetHash, acter_uri, final_url = self._gen_uri(
            user_id=user_id, path=path, query=payload.get('query'))

        qrcode = self._generate_qrcode(acter_uri)
        self._generate_template(targetHash,
                                url=final_url,
                                acter_uri=acter_uri,
                                qrcode=qrcode
                                )

        return 200, {
            'url': final_url,
            'targetUri': acter_uri,
        }

    def _gen_userId(self, requester: Requester, payload: Dict[str, Any]) -> Tuple[int, JsonDict]:
        path = "u/{userId}".format(**payload)
        user_id = requester.user.to_string()[1:]  # w/o leading 0;
        targetHash, acter_uri, final_url = self._gen_uri(
            user_id=user_id, path=path, query=payload.get('query'))

        qrcode = self._generate_qrcode(acter_uri)
        self._generate_template(targetHash,
                                url=final_url,
                                acter_uri=acter_uri,
                                qrcode=qrcode
                                )

        return 200, {
            'url': final_url,
            'targetUri': acter_uri,
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

from synapse.types import Dict, Any, Tuple, JsonDict, UserID
import hashlib
from synapse.http.server import (
    DirectServeHtmlResource,
    finish_request,
    logger,
    set_clickjacking_protection_headers,
    DirectServeJsonResource,
)
from synapse.storage.roommember import ProfileInfo
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
from urllib.parse import urlencode
import qrcode
import qrcode.image.svg
import os

MY_DIR = os.path.dirname(os.path.realpath(__file__))


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

    def _generate_og_image(self, targetHash: str, **params) -> str:
        im = Image.new('RGB', (1200, 630), 'white')
        file_name = os.path.join(
            self.dir_path, '{fn}.png'.format(fn=targetHash))
        im.save(file_name)
        return file_name

    def _generate_square_image(self, targetHash: str, **params) -> str:
        im = Image.new('RGB', (1200, 1200), 'white')
        file_name = os.path.join(
            self.dir_path, '{fn}_square.png'.format(fn=targetHash))
        im.save(file_name)
        return file_name

    def _generate_template(self, targetHash: str, params: Dict[Any, Any]):
        file_name = os.path.join(
            self.dir_path, '{fn}.html'.format(fn=targetHash))
        with open(file_name, mode='w') as f:
            f.write(self.template.render(params))

    def _gen_uri(self, user_id: str, path: str, query: Dict[str, Any] | None = None) -> Tuple[str, str, str]:
        query_params = query or dict()
        query_params["userId"] = user_id
        q = urlencode(query_params)
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

    def _gen_spaceObject(self, user_id: str, owner_info: ProfileInfo, payload: Dict[str, Any]) -> Tuple[int, JsonDict]:
        path = "o/{roomId}/{objectType}/{objectId}".format(**payload)
        targetHash, acter_uri, final_url = self._gen_uri(
            user_id=user_id, path=path, query=payload.get('query'))
        url_prefix = self.config.url_prefix

        qrcode = self._generate_qrcode(acter_uri)
        # og_image_name = self._generate_og_image(targetHash,
        #                                         acter_uri=acter_uri,)
        # square_image_name = self._generate_square_image(targetHash,
        #                                                 acter_uri=acter_uri,)
        # main_image_full = '{p}{f}'.format(p=url_prefix,
        #                                   f=og_image_name)
        icon = '📗'
        objectType = payload.get('objectType', None)
        if objectType == 'pin':
            icon = '📌'
        elif objectType == 'boost':
            icon = '🚀'
        elif objectType == 'calendarEvent':
            icon = '🗓️'
        elif objectType == 'taskList':
            icon = '📋'

        query_params = payload.get('query', {}) or {}
        params = dict(
            sharerId=user_id,
            url=final_url,
            acter_uri=acter_uri,
            qrcode=qrcode,
            icon=icon,
            objectId=payload.get('objectId', None),
            # images=[
            #     (main_image_full, (1200, 630)),
            #     ('{p}{f}'.format(p=url_prefix,
            #                      f=square_image_name), (1200, 1200)),
            # ],
            title=query_params.get('title', None),
            roomId=payload.get('roomId', None),
            sharerDisplayName=owner_info.display_name,
            roomDisplayName=query_params.get(
                'roomDisplayName', None)
        )
        self._generate_template(targetHash, params)

        return 200, {
            'url': final_url,
            'targetUri': acter_uri,
        }

    def _gen_superInvite(self, user_id: str, owner_info: ProfileInfo, payload: Dict[str, Any]) -> Tuple[int, JsonDict]:
        path = "i/{server}/{inviteCode}".format(**payload)
        targetHash, acter_uri, final_url = self._gen_uri(
            user_id=user_id, path=path, query=payload.get('query'))

        qrcode = self._generate_qrcode(acter_uri)

        query_params = payload.get('query', {}) or {}
        params = dict(
            sharerId=user_id,
            url=final_url,
            acter_uri=acter_uri,
            qrcode=qrcode,
            icon='🎟️',
            inviteCode=payload.get('inviteCode', None),
            sharerDisplayName=owner_info.display_name,
            rooms=query_params.get(
                'rooms', None),
        )
        self._generate_template(targetHash, params)

        return 200, {
            'url': final_url,
            'targetUri': acter_uri,
        }

    def _gen_roomId(self, user_id: str, owner_info: ProfileInfo, payload: Dict[str, Any]) -> Tuple[int, JsonDict]:
        path = "roomid/{roomId}".format(**payload)
        targetHash, acter_uri, final_url = self._gen_uri(
            user_id=user_id, path=path, query=payload.get('query'))

        qrcode = self._generate_qrcode(acter_uri)

        query_params = payload.get('query', {}) or {}
        params = dict(
            sharerId=user_id,
            url=final_url,
            acter_uri=acter_uri,
            qrcode=qrcode,
            icon='#️⃣',
            roomId=payload.get('roomId', None),
            sharerDisplayName=owner_info.display_name,
            roomDisplayName=query_params.get(
                'roomDisplayName', None),
        )
        self._generate_template(targetHash, params)

        return 200, {
            'url': final_url,
            'targetUri': acter_uri,
        }

    def _gen_roomAlias(self, user_id: str, owner_info: ProfileInfo, payload: Dict[str, Any]) -> Tuple[int, JsonDict]:
        path = "r/{roomAlias}".format(**payload)
        targetHash, acter_uri, final_url = self._gen_uri(
            user_id=user_id, path=path, query=payload.get('query'))

        qrcode = self._generate_qrcode(acter_uri)

        query_params = payload.get('query', {}) or {}
        params = dict(
            sharerId=user_id,
            url=final_url,
            acter_uri=acter_uri,
            qrcode=qrcode,
            icon='#️⃣',
            roomAlias=payload.get('roomAlias', None),
            sharerDisplayName=owner_info.display_name,
            roomDisplayName=query_params.get(
                'roomDisplayName', None),
        )
        self._generate_template(targetHash, params)
        return 200, {
            'url': final_url,
            'targetUri': acter_uri,
        }

    def _gen_userId(self, user_id: str, owner_info: ProfileInfo, payload: Dict[str, Any]) -> Tuple[int, JsonDict]:
        path = "u/{userId}".format(**payload)
        targetHash, acter_uri, final_url = self._gen_uri(
            user_id=user_id, path=path, query=payload.get('query'))

        qrcode = self._generate_qrcode(acter_uri)

        query_params = payload.get('query', {}) or {}
        params = dict(
            sharerId=user_id,
            url=final_url,
            acter_uri=acter_uri,
            qrcode=qrcode,
            userId=payload.get('userId'),
            sharerDisplayName=owner_info.display_name,
        )
        self._generate_template(targetHash, params)

        return 200, {
            'url': final_url,
            'targetUri': acter_uri,
        }

    async def _async_render_PUT(self, request: SynapseRequest) -> Tuple[int, JsonDict]:
        # ensure logged in
        requester = await self.api.get_user_by_req(request, allow_guest=False)
        full_id = requester.user.to_string()
        user_id = full_id[1:]  # w/o leading 0;
        owner_info = await self.api._store.get_profileinfo(
            UserID.from_string(full_id)
        )
        payload = parse_json_object_from_request(request)
        uri_type = payload.get('type', None)
        if uri_type == "spaceObject":
            return self._gen_spaceObject(user_id, owner_info, payload)
        elif uri_type == "superInvite":
            return self._gen_superInvite(user_id, owner_info, payload)
        elif uri_type == "roomId":
            return self._gen_roomId(user_id, owner_info, payload)
        elif uri_type == "roomAlias":
            return self._gen_roomAlias(user_id, owner_info, payload)
        elif uri_type == "userId":
            return self._gen_userId(user_id, owner_info, payload)
        else:
            return 403, {
                "error": "unsupported object type='{uri_type}' ".format(uri_type=uri_type),
                "errcode": "NOT_SUPPORTED",
            }

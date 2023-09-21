import requests

import xraypanels.xuipanels


class Inbounds:
    def get_inbounds(self: "xraypanels.xuipanels.XUI"):
        inbounds_request = requests.get(url=f'{self.api_url}/list/',
                                        cookies={'session': self.session_cookie},
                                        verify=self.https)
        print(inbounds_request.json())
        if (inbounds_request.status_code // 100 == 2
                and inbounds_request.headers.get('Content-Type').startswith('application/json')):
            return inbounds_request.json()
        else:
            return False

    def get_inbound(self: "xraypanels.xuipanels.XUI", inbound_id: int):
        inbound_request = requests.get(url=f'{self.api_url}/get/{inbound_id}',
                                       cookies={'session': self.session_cookie},
                                       verify=self.https)
        if (inbound_request.status_code // 100 == 2
                and inbound_request.headers.get('Content-Type').startswith('application/json')):
            return inbound_request.json()
        else:
            return False

import json

import requests

import xraypanels.xuipanels


class Clients:
    def get_client(self: "xraypanels.xuipanels.XUI",
                   email: str = False,
                   uuid: str = False,
                   inbound_id: int = False):
        if not email and not uuid:
            return False, None

        inbounds = self.get_inbounds()
        if not inbounds:
            return False, None

        for inbound in inbounds['obj']:
            if inbound_id and inbound_id != inbound['id']:
                continue
            settings = json.loads(inbound["settings"])
            for client in settings['clients']:
                if client['email'] == email or client['id'] == uuid:
                    return client, inbound
        return False, None

    def get_client_traffics_by_email(self: "xraypanels.xuipanels.XUI", email: str):
        if not email:
            return False
        client_traffics_request = requests.get(url=f'{self.api_url}/getClientTraffics/{email}/',
                                               cookies={'session': self.session_cookie},
                                               verify=self.https)
        if (client_traffics_request.status_code // 100 == 2
                and client_traffics_request.headers.get('Content-Type').startswith('application/json')):
            return client_traffics_request.json()['obj']
        else:
            return False

    def get_client_traffics_by_uuid(self: "xraypanels.xuipanels.XUI", uuid: str, inbound_id: int = None):
        if not uuid:
            return False
        client, inbound = self.get_client(uuid=uuid, inbound_id=inbound_id)
        for client_traffics in inbound['clientStats']:
            if client_traffics['email'] == client['email']:
                return client_traffics, client, inbound
        return False

    def add_client(self: "xraypanels.xuipanels.XUI",
                   inbound_id: int,
                   email: str,
                   uuid: str,
                   total_gb: int = 0,
                   expire_time: int = 0,
                   ip_limit: int = 0,
                   enable: bool = True,
                   subscription_id: str = '',
                   telegram_id: str = ''
                   ):
        if not inbound_id or not email or not uuid:
            return False

        settings = {
            'clients': [
                {
                    'enable': enable,
                    'email': email,
                    'alterId': 0,
                    'id': uuid,
                    "subId": subscription_id,
                    "tgId": telegram_id,
                    'limitIp': ip_limit,
                    'totalGB': total_gb,
                    'expiryTime': int(expire_time),
                }
            ]
        }
        add_client_request = requests.post(url=f'{self.api_url}/addClient/',
                                           data={'id': inbound_id, 'settings': json.dumps(settings)},
                                           cookies={'session': self.session_cookie},
                                           verify=self.https)
        if (add_client_request.status_code // 100 == 2
                and add_client_request.headers.get('Content-Type').startswith('application/json')):
            return True
        return False

    def update_client(self: "xraypanels.xuipanels.XUI",
                      email: str,
                      uuid: str,
                      inbound_id: int = None,
                      total_gb: int = 0,
                      expire_time: int = 0,
                      ip_limit: int = 0,
                      enable: bool = True,
                      subscription_id: str = '',
                      telegram_id: str = ''
                      ):
        if not email or not uuid:
            return False
        client, inbound = self.get_client(email=email, uuid=uuid, inbound_id=inbound_id or False)
        if not client:
            return False
        settings = {
            'clients': [
                {
                    'enable': enable,
                    'email': email,
                    'alterId': 0,
                    'id': uuid,
                    "subId": subscription_id,
                    "tgId": telegram_id,
                    'limitIp': ip_limit,
                    'totalGB': total_gb,
                    'expiryTime': int(expire_time),
                }
            ]
        }

        update_client_request = requests.post(url=f'{self.api_url}/updateClient/{client["id"]}/',
                                              data={'id': inbound['id'], 'settings': json.dumps(settings)},
                                              cookies={'session': self.session_cookie},
                                              verify=self.https)
        if (update_client_request.status_code // 100 == 2
                and update_client_request.headers.get('Content-Type').startswith('application/json')):
            return True
        return False

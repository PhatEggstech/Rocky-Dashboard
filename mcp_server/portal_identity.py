"""Rocky identity broker: use documented frontend login/refresh contracts only."""
import base64
import json
import time
from urllib.parse import urlparse

import httpx
from .config import ROCKY_DASHBOARD_IDENTITY_BASE_URL, ROCKY_DASHBOARD_API_BASE_URL


class PortalIdentityError(RuntimeError):
    pass


def _url(base,path):
    if urlparse(base).scheme!='https':
        raise PortalIdentityError('Rocky identity endpoints require HTTPS')
    return base.rstrip('/')+path


def _claims_from_issued_token(token):
    # Only consume tokens received directly from the configured HTTPS identity
    # service, never a token/subject submitted by a browser or MCP tool argument.
    try:
        encoded=token.removeprefix('Bearer ').split('.')[1]
        claims=json.loads(base64.urlsafe_b64decode(encoded+'='*(-len(encoded)%4)))
        subject=claims.get('id')
        expiry=float(claims['exp'])
        if not isinstance(subject,str) or not subject or expiry<=time.time():
            raise ValueError()
        return subject,expiry
    except (ValueError,KeyError,IndexError,TypeError):
        raise PortalIdentityError('Rocky did not return a usable identity and expiry') from None


def authenticate(username,password):
    try:
        with httpx.Client(timeout=20,follow_redirects=False) as client:
            response=client.post(_url(ROCKY_DASHBOARD_IDENTITY_BASE_URL,'/Identity/Login/Password'),
                headers={'appCode':'ROCKY','Accept':'application/json'},
                json={'username':username,'password':password})
            if response.status_code!=200:
                raise PortalIdentityError('Rocky sign-in was rejected')
            data=response.json().get('data') or {}
            token=data.get('accessToken')
            refresh=data.get('refreshToken') or ''
            if not isinstance(token,str) or not token:
                raise PortalIdentityError('Rocky returned no access token')
            # The portal sends the returned token verbatim in Authorization.
            profile=client.get(_url(ROCKY_DASHBOARD_API_BASE_URL,'/Admin/Account/CurrentProfile'),
                headers={'Authorization':token,'Accept':'application/json'})
            if profile.status_code!=200 or not isinstance(profile.json().get('data'),dict):
                raise PortalIdentityError('Rocky profile verification failed')
            subject,expiry=_claims_from_issued_token(token)
            return {'rk_user_id':subject,'access_token':token,'refresh_token':refresh,'token_expires_at':expiry}
    except (httpx.HTTPError,ValueError,TypeError,AttributeError):
        raise PortalIdentityError('Rocky identity service is unavailable') from None


def refresh_session(vault,raw_session,session):
    if not session.get('refresh_token'):
        return None
    try:
        response=httpx.post(_url(ROCKY_DASHBOARD_IDENTITY_BASE_URL,'/Identity/RefreshToken'),
            json={'refreshToken':session['refresh_token']},headers={'Accept':'application/json'},
            timeout=20,follow_redirects=False)
        if response.status_code in (400,401,403):
            vault.revoke_session(raw_session)
            return None
        if response.status_code!=200:
            return None
        data=response.json().get('data') or {}
        token=data.get('accessToken','')
        subject,expiry=_claims_from_issued_token(token)
        if subject!=session['rk_user_id']:
            vault.revoke_session(raw_session)
            return None
        refresh=data.get('refreshToken') or session['refresh_token']
        if not vault.update_tokens(raw_session,token,refresh,token_expires_at=expiry):
            return None
        return vault.get_session(raw_session)
    except (httpx.HTTPError,ValueError,PortalIdentityError,TypeError,AttributeError):
        return None

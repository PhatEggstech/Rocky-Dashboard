"""Per-request portal credentials; never fall back to the shared admin token."""
import os
from pathlib import Path
import time
import hashlib
import threading
import weakref

_refresh_locks=weakref.WeakValueDictionary()
_refresh_guard=threading.Lock()


def _refresh_lock(session):
    key=hashlib.sha256(session.encode()).hexdigest()
    with _refresh_guard:
        lock=_refresh_locks.get(key)
        if lock is None:
            lock=threading.Lock()
            _refresh_locks[key]=lock
        return lock


def store():
    from .portal_sessions import PortalSessionStore
    path=os.environ.get('MCP_PORTAL_SESSION_DB_PATH','')
    keyfile=os.environ.get('MCP_PORTAL_KEY_FILE','')
    if not path or not keyfile:
        raise RuntimeError('Portal vault is not configured')
    key=Path(keyfile).read_bytes().strip()
    return PortalSessionStore(path,key)


def resolve_portal_user(bearer):
    if not bearer.startswith('rkps_'):
        return None
    try:
        data=store().get_session(bearer)
    except Exception:
        return None
    if not data:
        return None
    from .auth import UserContext
    return UserContext(user_id=data['user_id'],role='portal',store_id=None,staff_id=None,
        name='Rocky portal user',username='rk:'+data['rk_user_id'],
        portal_session=bearer,rk_user_id=data['rk_user_id'])


def portal_access_token(user, force_refresh=False):
    if not user.portal_session:
        return '',{'error':'Individual Rocky sign-in required','code':401,'login_required':True}
    try:
        vault=store()
        data=vault.get_session(user.portal_session)
        if not data or data['rk_user_id']!=user.rk_user_id:
            return '',{'error':'Portal session expired or revoked','code':401,'login_required':True}
        if force_refresh or data['token_expires_at']<=time.time()+30:
            old_token=data['access_token']
            with _refresh_lock(user.portal_session):
                data=vault.get_session(user.portal_session)
                if not data or data['rk_user_id']!=user.rk_user_id:
                    return '',{'error':'Portal session expired or revoked','code':401,'login_required':True}
                if data['token_expires_at']<=time.time()+30 or (force_refresh and data['access_token']==old_token):
                    from .portal_identity import refresh_session
                    data=refresh_session(vault,user.portal_session,data)
                    if not data:
                        return '',{'error':'Rocky token expired; sign in again','code':401,'login_required':True}
        return data['access_token'],None
    except Exception:
        return '',{'error':'Portal credentials unavailable','code':503}

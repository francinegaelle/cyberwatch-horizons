import json
import os
import threading
from datetime import datetime, timezone
import requests

TOKEN = os.getenv('GITHUB_GIST_TOKEN', '')
API = 'https://api.github.com'
FILE_NAME = 'cyberwatch_state.json'
DESCRIPTION = 'CyberWatch Horizons persistent state'
_HEADERS = {
    'Accept': 'application/vnd.github+json',
    'X-GitHub-Api-Version': '2026-03-10',
    'User-Agent': 'CyberWatch-Horizons/3.0',
}
if TOKEN:
    _HEADERS['Authorization'] = f'Bearer {TOKEN}'

_DEFAULT_STATE = {
    'settings': {
        'recipient_email': '',
        'email_enabled': True,
        'p1_immediate': True,
        'p2_immediate': True,
        'h2_weekly': True,
        'h3_monthly': True,
        'browser_enabled': False,
    },
    'sent_alerts': [],
    'scheduler_state': {},
    'updated_at': None,
}
_lock = threading.Lock()
_gist_id = None
_fallback = json.loads(json.dumps(_DEFAULT_STATE))


def configured():
    return bool(TOKEN)


def _copy_default():
    return json.loads(json.dumps(_DEFAULT_STATE))


def _find_or_create():
    global _gist_id
    if _gist_id:
        return _gist_id
    if not TOKEN:
        return None
    r = requests.get(f'{API}/gists', headers=_HEADERS, params={'per_page': 100}, timeout=20)
    r.raise_for_status()
    for gist in r.json():
        if FILE_NAME in (gist.get('files') or {}):
            _gist_id = gist['id']
            return _gist_id
    payload = {
        'description': DESCRIPTION,
        'public': False,
        'files': {FILE_NAME: {'content': json.dumps(_DEFAULT_STATE, ensure_ascii=False, indent=2)}},
    }
    r = requests.post(f'{API}/gists', headers=_HEADERS, json=payload, timeout=20)
    r.raise_for_status()
    _gist_id = r.json()['id']
    return _gist_id


def get_state():
    global _fallback
    gid = _find_or_create()
    if not gid:
        return json.loads(json.dumps(_fallback)), False
    r = requests.get(f'{API}/gists/{gid}', headers=_HEADERS, timeout=20)
    r.raise_for_status()
    f = (r.json().get('files') or {}).get(FILE_NAME)
    if not f:
        return _copy_default(), True
    content = f.get('content') or '{}'
    if f.get('truncated') and f.get('raw_url'):
        rr = requests.get(f['raw_url'], headers=_HEADERS, timeout=20)
        rr.raise_for_status()
        content = rr.text
    try:
        raw = json.loads(content)
    except Exception:
        raw = {}
    state = _copy_default()
    state['settings'].update(raw.get('settings') or {})
    state['sent_alerts'] = list(raw.get('sent_alerts') or [])[-1000:]
    state['scheduler_state'].update(raw.get('scheduler_state') or {})
    state['updated_at'] = raw.get('updated_at')
    return state, True


def save_state(state):
    global _fallback
    state['updated_at'] = datetime.now(timezone.utc).isoformat()
    state['sent_alerts'] = list(state.get('sent_alerts') or [])[-1000:]
    gid = _find_or_create()
    if not gid:
        _fallback = json.loads(json.dumps(state))
        return False
    payload = {
        'description': DESCRIPTION,
        'files': {FILE_NAME: {'content': json.dumps(state, ensure_ascii=False, indent=2)}},
    }
    r = requests.patch(f'{API}/gists/{gid}', headers=_HEADERS, json=payload, timeout=20)
    r.raise_for_status()
    return True


def mutate(mutator):
    with _lock:
        state, persistent = get_state()
        result = mutator(state)
        saved = save_state(state)
        return result, bool(persistent and saved)

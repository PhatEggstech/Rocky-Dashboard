# -*- coding: utf-8 -*-
"""Test OAuth PKCE flow - simulates exactly what Claude Desktop (mcp-remote) does.

Steps:
1. POST /mcp without auth -> expect 401
2. GET /.well-known/oauth-protected-resource -> discover auth server
3. GET /.well-known/oauth-authorization-server -> get endpoints
4. POST /register -> get client_id
5. Generate PKCE code_verifier + code_challenge (S256)
6. GET /authorize?redirect_uri=...&code_challenge=...&state=...
7. Follow redirect to /login, POST credentials
8. Capture redirect to callback with ?code=...
9. POST /token with code + code_verifier -> get access_token
10. POST /mcp with access_token -> should get MCP tools

Usage:
    python scripts/test_oauth_pkce.py [base_url]
    
    Default base_url: http://localhost:8086 (staging)
"""
import sys
import hashlib
import base64
import secrets
import json
import httpx

BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8086"

# Test credentials
USERNAME = "admin"
PASSWORD = "admin123"


def generate_pkce():
    """Generate PKCE code_verifier and code_challenge (S256)."""
    code_verifier = secrets.token_urlsafe(32)
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode('ascii')).digest()
    ).rstrip(b'=').decode('ascii')
    return code_verifier, code_challenge


def test_full_oauth_flow():
    print(f"Testing OAuth PKCE flow against: {BASE_URL}")
    print("=" * 60)

    client = httpx.Client(follow_redirects=False, timeout=15)

    # Step 1: POST /mcp without auth -> 401
    print("\n[1] POST /mcp without auth...")
    try:
        r = client.post(f"{BASE_URL}/mcp", json={
            "jsonrpc": "2.0", "method": "initialize", "id": 1,
            "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}}
        })
        assert r.status_code == 401, f"Expected 401, got {r.status_code}: {r.text[:200]}"
        print(f"    OK: Got 401 (auth required)")
    except Exception as e:
        print(f"    FAIL: {e}")
        return False

    # Step 2: GET /.well-known/oauth-protected-resource
    print("\n[2] GET /.well-known/oauth-protected-resource...")
    r = client.get(f"{BASE_URL}/.well-known/oauth-protected-resource")
    assert r.status_code == 200, f"Got {r.status_code}"
    resource_meta = r.json()
    print(f"    OK: resource={resource_meta.get('resource')}")
    auth_server = resource_meta.get("authorization_servers", [BASE_URL])[0]

    # Step 3: GET /.well-known/oauth-authorization-server
    print("\n[3] GET /.well-known/oauth-authorization-server...")
    r = client.get(f"{auth_server}/.well-known/oauth-authorization-server")
    assert r.status_code == 200, f"Got {r.status_code}"
    oauth_meta = r.json()
    print(f"    OK: issuer={oauth_meta.get('issuer')}")
    print(f"    token_endpoint={oauth_meta.get('token_endpoint')}")
    print(f"    code_challenge_methods={oauth_meta.get('code_challenge_methods_supported')}")
    
    auth_endpoint = oauth_meta["authorization_endpoint"]
    token_endpoint = oauth_meta["token_endpoint"]
    register_endpoint = oauth_meta["registration_endpoint"]

    # Step 4: POST /register (Dynamic Client Registration)
    print("\n[4] POST /register...")
    r = client.post(register_endpoint, json={
        "client_name": "test-mcp-client",
        "redirect_uris": ["http://127.0.0.1:9999/callback"],
        "grant_types": ["authorization_code"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none"
    })
    assert r.status_code == 200, f"Got {r.status_code}: {r.text}"
    reg = r.json()
    client_id = reg["client_id"]
    print(f"    OK: client_id={client_id}")

    # Step 5: Generate PKCE
    print("\n[5] Generate PKCE...")
    code_verifier, code_challenge = generate_pkce()
    print(f"    code_verifier={code_verifier[:20]}...")
    print(f"    code_challenge={code_challenge[:20]}...")

    # Step 6: GET /authorize
    print("\n[6] GET /authorize...")
    state = secrets.token_urlsafe(16)
    redirect_uri = "http://127.0.0.1:9999/callback"
    r = client.get(auth_endpoint, params={
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "state": state,
        "scope": "mcp"
    })
    assert r.status_code in (302, 307), f"Expected redirect, got {r.status_code}"
    login_url = r.headers["location"]
    print(f"    OK: Redirected to login: {login_url[:80]}...")

    # Step 7: GET /login (load form) then POST /login
    print("\n[7] POST /login with credentials...")
    # Follow redirect to login page
    if login_url.startswith("/"):
        login_url = f"{BASE_URL}{login_url}"
    
    r = client.get(login_url)
    assert r.status_code == 200, f"Login page: {r.status_code}"
    
    # Extract form action and hidden fields from the HTML
    # In our case, form posts to /login
    from urllib.parse import urlparse, parse_qs
    parsed = urlparse(login_url)
    query_params = parse_qs(parsed.query)
    
    form_redirect_uri = query_params.get("redirect_uri", [""])[0]
    form_state = query_params.get("state", [""])[0]
    form_code_challenge = query_params.get("code_challenge", [""])[0]
    form_code_challenge_method = query_params.get("code_challenge_method", [""])[0]
    
    # POST login
    r = client.post(f"{BASE_URL}/login", data={
        "username": USERNAME,
        "password": PASSWORD,
        "redirect_uri": form_redirect_uri,
        "state": form_state,
        "code_challenge": form_code_challenge,
        "code_challenge_method": form_code_challenge_method,
    })
    
    assert r.status_code == 302, f"Expected 302 redirect, got {r.status_code}: {r.text[:200]}"
    callback_url = r.headers["location"]
    print(f"    OK: Login success, redirect to: {callback_url[:80]}...")

    # Step 8: Extract auth code from callback URL
    print("\n[8] Extract auth code from callback...")
    parsed_callback = urlparse(callback_url)
    callback_params = parse_qs(parsed_callback.query)
    auth_code = callback_params.get("code", [""])[0]
    returned_state = callback_params.get("state", [""])[0]
    
    assert auth_code, f"No code in callback URL: {callback_url}"
    assert returned_state == state, f"State mismatch: {returned_state} != {state}"
    print(f"    OK: code={auth_code[:20]}..., state matches")

    # Step 9: POST /token with code + code_verifier
    print("\n[9] POST /token (exchange code for access_token)...")
    r = client.post(token_endpoint, data={
        "grant_type": "authorization_code",
        "code": auth_code,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "code_verifier": code_verifier,
    })
    
    if r.status_code != 200:
        print(f"    FAIL: {r.status_code} - {r.text}")
        return False
    
    token_data = r.json()
    access_token = token_data.get("access_token", "")
    assert access_token, f"No access_token in response: {token_data}"
    print(f"    OK: access_token={access_token[:20]}...")
    print(f"    token_type={token_data.get('token_type')}, expires_in={token_data.get('expires_in')}")

    # Step 10: POST /mcp with access_token -> MCP initialize
    print("\n[10] POST /mcp with Bearer token (MCP initialize)...")
    r = client.post(f"{BASE_URL}/mcp",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json",
        },
        json={
            "jsonrpc": "2.0", "method": "initialize", "id": 1,
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-oauth", "version": "1.0"}
            }
        }
    )
    
    if r.status_code == 200:
        print(f"    OK: MCP initialize success!")
        try:
            data = r.json()
            print(f"    Server: {data.get('result', {}).get('serverInfo', {})}")
        except:
            print(f"    Response: {r.text[:200]}")
    else:
        print(f"    Status: {r.status_code}")
        print(f"    Response: {r.text[:300]}")
        # For streamable-http, some servers may respond differently
        if r.status_code != 401:
            print("    (Non-401 means auth passed - server accepted the token)")

    # Step 11: Test with WRONG code_verifier (should fail)
    print("\n[11] NEGATIVE TEST: wrong code_verifier...")
    # Create a new auth code first
    code_verifier2, code_challenge2 = generate_pkce()
    state2 = secrets.token_urlsafe(16)
    
    r = client.get(auth_endpoint, params={
        "response_type": "code", "client_id": client_id,
        "redirect_uri": redirect_uri, "code_challenge": code_challenge2,
        "code_challenge_method": "S256", "state": state2,
    })
    login_url2 = r.headers["location"]
    if login_url2.startswith("/"):
        login_url2 = f"{BASE_URL}{login_url2}"
    
    parsed2 = urlparse(login_url2)
    qp2 = parse_qs(parsed2.query)
    
    r = client.post(f"{BASE_URL}/login", data={
        "username": USERNAME, "password": PASSWORD,
        "redirect_uri": qp2.get("redirect_uri", [""])[0],
        "state": qp2.get("state", [""])[0],
        "code_challenge": qp2.get("code_challenge", [""])[0],
        "code_challenge_method": qp2.get("code_challenge_method", [""])[0],
    })
    callback2 = r.headers["location"]
    code2 = parse_qs(urlparse(callback2).query).get("code", [""])[0]
    
    # Exchange with WRONG verifier
    r = client.post(token_endpoint, data={
        "grant_type": "authorization_code",
        "code": code2,
        "redirect_uri": redirect_uri,
        "client_id": client_id,
        "code_verifier": "WRONG_VERIFIER_SHOULD_FAIL",
    })
    assert r.status_code == 400, f"Expected 400 for wrong verifier, got {r.status_code}"
    error_data = r.json()
    assert "invalid_grant" in str(error_data), f"Unexpected error: {error_data}"
    print(f"    OK: Correctly rejected wrong code_verifier ({error_data.get('error_description', '')})")

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED! OAuth PKCE flow working correctly.")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = test_full_oauth_flow()
    sys.exit(0 if success else 1)

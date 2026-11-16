import asyncio
import time
from types import SimpleNamespace
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from app import mcp_bridge as bridge
import pytest


def test_mcp_fail_closed_and_tools():
    with pytest.raises(RuntimeError): bridge.application()
    with pytest.raises(PermissionError): bridge.list_projects()
    names={t.name for t in asyncio.run(bridge.mcp.list_tools())}
    assert {'list_projects','send_message','search_shared_memory','create_task','start_collaboration'}<=names
    with pytest.raises(ValueError): bridge.send_message('invalid','test',False)


def test_oauth_signature_audience_expiry_subject(monkeypatch):
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    monkeypatch.setattr(bridge,'OWNER','owner')
    monkeypatch.setattr(bridge,'ISSUER','https://issuer.example/')
    monkeypatch.setattr(bridge,'RESOURCE','https://workspace.example/mcp')
    verifier=bridge.Verifier()
    verifier.keys=SimpleNamespace(get_signing_key_from_jwt=lambda token:SimpleNamespace(key=key.public_key()))
    payload={'iss':bridge.ISSUER,'aud':bridge.RESOURCE,'sub':'owner','iat':int(time.time()),'exp':int(time.time())+60,'scope':'workspace:read'}
    def check(data): return asyncio.run(verifier.verify_token(jwt.encode(data,key,algorithm='RS256')))
    assert check(payload).scopes==['workspace:read']
    assert check(dict(payload,aud='other')) is None
    assert check(dict(payload,sub='other')) is None
    assert check(dict(payload,exp=1)) is None
    assert asyncio.run(verifier.verify_token('invalid')) is None


def test_authenticated_streamable_http_protocol(monkeypatch):
    from fastapi.testclient import TestClient
    from mcp.server.auth.provider import AccessToken
    from mcp.server.auth.settings import AuthSettings
    from mcp.server.fastmcp import FastMCP
    class TestVerifier:
        async def verify_token(self, token):
            if token=='valid':
                return AccessToken(token=token,client_id='test',scopes=['workspace:read'])
            return None
    server=FastMCP('Protocol test',token_verifier=TestVerifier(),
        auth=AuthSettings(issuer_url='https://issuer.example',resource_server_url='https://workspace.example/mcp',required_scopes=['workspace:read']),
        stateless_http=True,json_response=True)
    # Exercise the actual DualMind tools through SDK dispatch and HTTP auth.
    for tool in asyncio.run(bridge.mcp.list_tools()):
        server.add_tool(bridge.mcp._tool_manager.get_tool(tool.name).fn,name=tool.name)
    with TestClient(server.streamable_http_app(),base_url='http://localhost:8000') as client:
        headers={'Accept':'application/json, text/event-stream'}
        body={'jsonrpc':'2.0','id':1,'method':'initialize','params':{'protocolVersion':'2025-03-26','capabilities':{},'clientInfo':{'name':'test','version':'1'}}}
        assert client.post('/mcp',headers=headers,json=body).status_code==401
        headers['Authorization']='Bearer valid'
        response=client.post('/mcp',headers=headers,json=body)
        assert response.status_code==200
        assert response.json()['result']['serverInfo']['name']=='Protocol test'
        response=client.post('/mcp',headers=headers,json={'jsonrpc':'2.0','id':2,'method':'tools/list'})
        assert len(response.json()['result']['tools'])==12
        # A read-only OAuth client must not be able to invoke a write tool.
        response=client.post('/mcp',headers=headers,json={'jsonrpc':'2.0','id':3,'method':'tools/call','params':{'name':'send_message','arguments':{'project_id':'00000000-0000-0000-0000-000000000000','content':'test','confirmed':True}}})
        assert response.json()['result']['isError'] is True

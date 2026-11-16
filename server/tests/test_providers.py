import httpx
import pytest
from fastapi import HTTPException
from app import main

@pytest.mark.parametrize('provider', ['openai','gemini'])
def test_adapter_http_contract_and_failure(monkeypatch,provider):
    monkeypatch.setenv('OPENAI_API_KEY','test-openai')
    monkeypatch.setenv('GEMINI_API_KEY','test-gemini')
    real_client=httpx.Client
    seen=[]
    def handler(request):
        seen.append(request)
        if provider=='openai':
            assert request.headers['authorization']=='Bearer test-openai'
            return httpx.Response(200,json={'output':[{'type':'message','content':[{'type':'output_text','text':'answer'}]}]})
        assert request.headers['x-goog-api-key']=='test-gemini'
        return httpx.Response(200,json={'candidates':[{'content':{'parts':[{'text':'answer'}]}}]})
    monkeypatch.setattr(main.httpx,'Client',lambda **kwargs:real_client(transport=httpx.MockTransport(handler),**kwargs))
    fn=main.openai_reply if provider=='openai' else main.gemini_reply
    assert fn('test')=='answer'
    assert len(seen)==1
    monkeypatch.setattr(main.httpx,'Client',lambda **kwargs:real_client(transport=httpx.MockTransport(lambda r:httpx.Response(429)),**kwargs))
    with pytest.raises(HTTPException) as exc: fn('test')
    assert exc.value.status_code==502

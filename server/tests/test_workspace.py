import time
from test_api import client, HEADERS
from app import main


def project():
    return client.post('/rooms',headers=HEADERS,json={'name':'Workspace'}).json()['id']


def test_records_consent_search_revision_export_delete():
    rid=project()
    data={'kind':'task','title':'Ship','content':'literal % query','source':'user:manual'}
    path=f'/rooms/{rid}/records'
    assert client.post(path,headers=HEADERS,json=data).status_code==422
    data['approved']=True
    created=client.post(path,headers=HEADERS,json=data).json()
    oid=created['id']
    assert client.get(path,headers=HEADERS,params={'q':'%'}).json()[0]['id']==oid
    assert client.get(path,headers=HEADERS,params={'q':"' OR 1=1--"}).json()==[]
    assert client.put(path+'/'+oid,headers=HEADERS,json=data).status_code==409
    data.update(revision=1,status='done')
    assert client.put(path+'/'+oid,headers=HEADERS,json=data).json()['revision']==2
    assert client.get(path+'/'+oid,headers=HEADERS).json()['status']=='done'
    assert client.get(f'/rooms/{project()}/records/{oid}',headers=HEADERS).status_code==404
    exported=client.get(f'/rooms/{rid}/export',headers=HEADERS).json()
    assert len(exported['audit'])==2
    assert client.delete(f'/rooms/{rid}',headers=HEADERS).status_code==200
    assert client.get(path+'/'+oid,headers=HEADERS).status_code==404


def test_run_mocked_providers_and_persistence(monkeypatch):
    rid=project()
    monkeypatch.setattr(main,'openai_reply',lambda p:'proposal')
    monkeypatch.setattr(main,'gemini_reply',lambda p:'critique')
    path=f'/rooms/{rid}/runs'
    assert client.post(path,headers=HEADERS,json={'prompt':'Build'}).status_code==422
    response=client.post(path,headers=HEADERS,json={'prompt':'Build','allow_provider_transfer':True})
    assert response.status_code==202
    run_id=response.json()['id']
    for _ in range(100):
        result=client.get('/runs/'+run_id,headers=HEADERS).json()
        if result['state'] not in ('queued','running'): break
        time.sleep(.01)
    assert result['state']=='completed'
    assert result['calls']==3
    assert result['result']=='proposal'
    assert len(client.get(f'/rooms/{rid}/messages',headers=HEADERS).json())==4


def test_auth_strict_bearer_and_pagination():
    assert client.get('/rooms',headers={'Authorization':HEADERS['Authorization'][7:]}).status_code==401
    assert client.get('/rooms/x/messages?limit=999',headers=HEADERS).status_code==422


def test_cancel_prevents_second_provider_and_missing_auth(monkeypatch):
    from threading import Event
    entered, release = Event(), Event()
    def slow(prompt):
        entered.set()
        assert release.wait(5)
        return 'discard after cancellation'
    monkeypatch.setattr(main,'openai_reply',slow)
    monkeypatch.setattr(main,'gemini_reply',lambda p: (_ for _ in ()).throw(AssertionError('must not call Gemini')))
    rid=project()
    created=client.post(f'/rooms/{rid}/runs',headers=HEADERS,json={'prompt':'test','allow_provider_transfer':True}).json()
    run_id=created['id']
    try:
        assert entered.wait(2)
        assert client.get('/runs/'+run_id).status_code==401
        assert client.delete('/rooms/'+rid,headers=HEADERS).status_code==409
        assert client.post('/runs/'+run_id+'/cancel',headers=HEADERS).json()['state']=='cancelled'
    finally:
        release.set()
    time.sleep(.05)
    assert client.get('/runs/'+run_id,headers=HEADERS).json()['calls']==1
    assert [r['role'] for r in client.get(f'/rooms/{rid}/messages',headers=HEADERS).json()]==['user']


def test_provider_failure_is_durable_without_automatic_retry(monkeypatch):
    from fastapi import HTTPException
    def failure(prompt): raise HTTPException(503,'key missing')
    monkeypatch.setattr(main,'openai_reply',failure)
    rid=project()
    created=client.post(f'/rooms/{rid}/runs',headers=HEADERS,json={'prompt':'test','allow_provider_transfer':True}).json()
    for _ in range(100):
        result=client.get('/runs/'+created['id'],headers=HEADERS).json()
        if result['state']=='failed': break
        time.sleep(.01)
    assert result['state']=='failed'
    assert result['calls']==1
    assert result['error']=='HTTPException'

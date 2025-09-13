from fastapi.testclient import TestClient


def test_request_id_header_present_and_hex(monkeypatch):
    import apps.block0_api.main as api
    with TestClient(api.app) as client:
        r = client.get('/healthz')
        assert 'X-Request-ID' in r.headers
        rid = r.headers['X-Request-ID']
        assert len(rid) == 16
        int(rid, 16)  # raises ValueError if not hex


def test_request_id_header_preserved(monkeypatch):
    import apps.block0_api.main as api
    with TestClient(api.app) as client:
        given = 'abcdef0123456789'
        r = client.get('/healthz', headers={'X-Request-ID': given})
        assert r.headers.get('X-Request-ID') == given


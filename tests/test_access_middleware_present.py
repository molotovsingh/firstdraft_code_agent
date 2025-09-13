def test_access_and_request_id_middleware_present():
    import apps.block0_api.main as api
    names = {m.cls.__name__ for m in api.app.user_middleware}
    assert 'RequestIDMiddleware' in names
    assert 'HTTPAccessLogMiddleware' in names


def test_middleware_order():
    import importlib
    import apps.block0_api.main as api
    importlib.reload(api)
    names = [m.cls.__name__ for m in api.app.user_middleware]
    # Expect RequestID first, then Access, then APIKeyAuth
    assert names[0:3] == ['RequestIDMiddleware', 'HTTPAccessLogMiddleware', 'APIKeyAuthMiddleware']


import os
import importlib


def test_worker_health_wsgi(monkeypatch):
    # Patch the simple_server module before import so worker grabs our dummy
    captured = {"app": None}

    class DummyServer:
        def __init__(self, host, port, app):
            captured["app"] = app
            self.server_port = port or 0

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def serve_forever(self):
            # Return immediately so thread exits
            return

    # Create a faux module object with make_server symbol
    import types
    fake_srv = types.SimpleNamespace(make_server=lambda host, port, app: DummyServer(host, port, app))
    # Inject fake prometheus_client to avoid registry side effects
    class _DummyMetric:
        def __init__(self, *args, **kwargs):
            pass
        def labels(self, *args, **kwargs):
            return self
        def inc(self, *args, **kwargs):
            return None
        def observe(self, *args, **kwargs):
            return None

    def _make_wsgi_app():
        def _app(environ, start_response):
            start_response('200 OK', [('Content-Type', 'text/plain; charset=utf-8')])
            return [b'# HELP dummy\n# TYPE dummy counter\n']
        return _app

    fake_prom = types.SimpleNamespace(Counter=_DummyMetric, Histogram=_DummyMetric, make_wsgi_app=_make_wsgi_app)

    # Inject into sys.modules for import hook before worker import
    import sys
    sys.modules['wsgiref.simple_server'] = fake_srv
    sys.modules['prometheus_client'] = fake_prom

    # Ensure METRICS_PORT is set so worker starts the HTTP server
    os.environ['METRICS_PORT'] = '0'

    # Import (or reload) the worker
    # Import the worker module (after patches) — avoid double import elsewhere
    if 'apps.block0_worker.worker' in sys.modules:
        del sys.modules['apps.block0_worker.worker']
    import apps.block0_worker.worker as worker

    # We should have captured a WSGI app
    app = captured["app"]
    assert app is not None

    # Helper to call WSGI app
    def call(path):
        status_headers = {}

        def start_response(status, headers):
            status_headers['status'] = status
            status_headers['headers'] = headers

        body = b''.join(app({
            'REQUEST_METHOD': 'GET',
            'PATH_INFO': path,
            'wsgi.input': None,
            'SERVER_NAME': 'test',
            'SERVER_PORT': '0',
            'wsgi.version': (1, 0),
            'wsgi.url_scheme': 'http',
            'wsgi.errors': None,
            'wsgi.multithread': False,
            'wsgi.multiprocess': False,
            'wsgi.run_once': False,
        }, start_response))
        return status_headers['status'], dict(status_headers['headers']), body

    status, headers, body = call('/health')
    assert status.startswith('200')
    assert body == b'ok'

    status, headers, body = call('/metrics')
    assert status.startswith('200')
    # metrics body should contain HELP or TYPE lines
    assert b'HELP' in body or b'TYPE' in body

from shared.ocr.adapters.ocrmypdf import OCRmyPDFAdapter
import builtins


def test_ocrmypdf_extra_args_passed(monkeypatch):
    calls = {}

    def fake_run(cmd, check, capture_output, timeout):
        calls['cmd'] = cmd
        class R:
            returncode = 0
            stdout = b''
            stderr = b''
        return R()

    monkeypatch.setattr('subprocess.run', fake_run)
    adapter = OCRmyPDFAdapter(timeout_seconds=5, fast_mode=False, extra_args=['--foo', 'bar'])
    adapter.process(b'%PDF-1.4', 'application/pdf', languages=['eng'])
    assert '--foo' in calls['cmd'] and 'bar' in calls['cmd']


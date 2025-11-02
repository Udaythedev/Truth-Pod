from click.testing import CliRunner
import device_sdk.client as sdk_client
from device_sdk.cli import main as cli_main
import tempfile
import os


def test_enroll_command(monkeypatch):
    def fake_enroll(self, token, user_id, image_b64, meta=None):
        return {'user_id': user_id, 'face_image_url': '/media/fake.jpg'}

    monkeypatch.setattr(sdk_client.DeviceClient, 'enroll_face', fake_enroll)

    # create a small temp image file
    fd, path = tempfile.mkstemp(suffix='.jpg')
    try:
        with open(path, 'wb') as f:
            f.write(b'\xff\xd8\xff' + b'0' * 10)

        runner = CliRunner()
        result = runner.invoke(cli_main, ['--base-url', 'http://test', 'enroll', '--token', 'tk', 'alice', path])
        assert result.exit_code == 0
        assert 'face_image_url' in result.output
    finally:
        try:
            os.close(fd)
        except Exception:
            pass


def test_recognize_command(monkeypatch):
    def fake_recognize(self, token, image_b64, limit=5):
        return {'user_id': None, 'user_name': 'UNKNOWN', 'confidence': 0.0}

    monkeypatch.setattr(sdk_client.DeviceClient, 'recognize_face', fake_recognize)

    fd, path = tempfile.mkstemp(suffix='.jpg')
    try:
        with open(path, 'wb') as f:
            f.write(b'\xff\xd8\xff' + b'1' * 10)

        runner = CliRunner()
        result = runner.invoke(cli_main, ['--base-url', 'http://test', 'recognize', '--token', 'tk', path])
        assert result.exit_code == 0
        assert 'UNKNOWN' in result.output
    finally:
        try:
            os.close(fd)
        except Exception:
            pass

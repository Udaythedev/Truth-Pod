from click.testing import CliRunner
import device_sdk.client as sdk_client
from device_sdk.cli import main as cli_main


def test_register_command(monkeypatch):
    def fake_register(self, device_id, device_type='python-sdk'):
        return 'tok-xyz'

    monkeypatch.setattr(sdk_client.DeviceClient, 'register_device', fake_register)

    runner = CliRunner()
    result = runner.invoke(cli_main, ['--base-url', 'http://test', 'register', 'dev-1'])
    assert result.exit_code == 0
    assert 'tok-xyz' in result.output


def test_trending_command(monkeypatch):
    def fake_get_trending(self, token, limit=10):
        return {'results': [{'id': 'n1'}]}

    monkeypatch.setattr(sdk_client.DeviceClient, 'get_trending', fake_get_trending)

    runner = CliRunner()
    result = runner.invoke(cli_main, ['--base-url', 'http://test', 'trending', '--token', 'tk', '--limit', '2'])
    assert result.exit_code == 0
    assert 'results' in result.output

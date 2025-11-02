import json
import click
from .client import DeviceClient
import base64
import os


@click.group()
@click.option('--base-url', default='http://localhost:8000', help='Backend base URL')
@click.pass_context
def main(ctx, base_url):
    ctx.ensure_object(dict)
    ctx.obj['base_url'] = base_url


@main.command()
@click.argument('device_id')
@click.option('--device-type', '-t', default='cli', help='Device type')
@click.pass_context
def register(ctx, device_id, device_type):
    """Register a device and print the access token."""
    client = DeviceClient(base_url=ctx.obj['base_url'])
    token = client.register_device(device_id=device_id, device_type=device_type)
    click.echo(token)


@main.command()
@click.option('--token', '-k', required=True, help='Access token')
@click.option('--limit', default=10, help='Number of results')
@click.pass_context
def trending(ctx, token, limit):
    """Show trending news items."""
    client = DeviceClient(base_url=ctx.obj['base_url'])
    res = client.get_trending(token=token, limit=limit)
    try:
        click.echo(json.dumps(res, indent=2))
    except Exception:
        click.echo(str(res))


@main.command()
@click.option('--token', '-k', required=True, help='Access token')
@click.argument('user_name')
@click.argument('image_path', type=click.Path(exists=True, dir_okay=False))
@click.pass_context
def enroll(ctx, token, user_name, image_path):
    """Enroll a face from a local image file."""
    client = DeviceClient(base_url=ctx.obj['base_url'])
    with open(image_path, 'rb') as f:
        b64 = base64.b64encode(f.read()).decode('utf-8')
    res = client.enroll_face(token=token, user_id=user_name, image_b64=b64)
    click.echo(json.dumps(res, indent=2))


@main.command()
@click.option('--token', '-k', required=True, help='Access token')
@click.argument('image_path', type=click.Path(exists=True, dir_okay=False))
@click.option('--limit', default=5, help='Max matches')
@click.pass_context
def recognize(ctx, token, image_path, limit):
    """Recognize a face from a local image file."""
    client = DeviceClient(base_url=ctx.obj['base_url'])
    with open(image_path, 'rb') as f:
        b64 = base64.b64encode(f.read()).decode('utf-8')
    res = client.recognize_face(token=token, image_b64=b64, limit=limit)
    click.echo(json.dumps(res, indent=2))


@main.command()
@click.option('--token', '-k', required=True, help='Access token')
@click.argument('q')
@click.option('--limit', default=10, help='Number of results')
@click.pass_context
def search(ctx, token, q, limit):
    """Search news by query."""
    client = DeviceClient(base_url=ctx.obj['base_url'])
    res = client.search(token=token, q=q, limit=limit)
    try:
        click.echo(json.dumps(res, indent=2))
    except Exception:
        click.echo(str(res))


def run():
    main()


if __name__ == '__main__':
    main()

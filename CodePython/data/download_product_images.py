"""Download the official image URLs in products.json; never generate images.

Run manually when replacing product photos. Requires curl on PATH and internet.
Only image files below data/images/catalog are written.
"""

from concurrent.futures import ThreadPoolExecutor
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit

DATA_ROOT = Path(__file__).resolve().parent
IMAGE_ROOT = DATA_ROOT / 'images'
ALLOWED_HOSTS = {'store.storeimages.cdn-apple.com', 'www.apple.com',
                 'support.apple.com', 'cdsassets.apple.com', 'help.apple.com',
                 'dlcdnwebimgs.asus.com', 'resource.logitech.com', 'resource.logitechg.com'}


def download(product):
    url = product['image_source_url']
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError(f"Unapproved manufacturer image host: {url}")
    relative = Path(product['image'])
    destination = (IMAGE_ROOT / relative).resolve()
    catalog_root = (IMAGE_ROOT / 'catalog').resolve()
    if not destination.is_relative_to(catalog_root) or destination.suffix.lower() not in {'.jpg', '.jpeg', '.png', '.webp'}:
        raise ValueError(f"Invalid catalogue image path: {relative}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    curl = shutil.which('curl.exe') or shutil.which('curl')
    if not curl:
        raise RuntimeError('Install curl or use the curl provided by Windows.')
    with TemporaryDirectory(prefix='image-download-', dir=catalog_root) as temporary:
        staging = Path(temporary) / destination.name
        subprocess.run([curl, '--fail', '--location', '--silent', '--show-error',
                        '--connect-timeout', '15', '--max-time', '60', '--retry', '1',
                        '--output', str(staging), url], check=True, timeout=140)
        header = staging.read_bytes()[:16]
        valid = (header.startswith(b'\xff\xd8\xff') if destination.suffix.lower() in {'.jpg', '.jpeg'}
                 else header.startswith(b'\x89PNG\r\n\x1a\n') if destination.suffix.lower() == '.png'
                 else header.startswith(b'RIFF') and header[8:12] == b'WEBP')
        if not valid or staging.stat().st_size < 1000:
            raise ValueError(f"Not a valid product image: {product['name']}")
        # Copy into the public image folder first: Windows temporary directories
        # have private ACLs, which must not travel with a moved image file.
        replacement = destination.with_name(destination.name + '.incoming')
        try:
            shutil.copyfile(staging, replacement)
            replacement.replace(destination)
        finally:
            replacement.unlink(missing_ok=True)
    return f"Saved {product['id']}: {destination.name} ({destination.stat().st_size} bytes)"


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--missing-only', action='store_true', help='Keep existing downloaded images.')
    args = parser.parse_args()
    products = json.loads((DATA_ROOT / 'products.json').read_text(encoding='utf-8'))
    if args.missing_only:
        products = [p for p in products if not (IMAGE_ROOT / p['image']).is_file()]
    failures = 0
    with ThreadPoolExecutor(max_workers=3) as executor:
        tasks = [(product, executor.submit(download, product)) for product in products]
        for product, task in tasks:
            try:
                print(task.result(), flush=True)
            except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
                failures += 1
                print(f"FAILED {product['name']}: {error}", flush=True)
    return int(failures > 0)


if __name__ == '__main__':
    raise SystemExit(main())

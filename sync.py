"""Mirror OpenCCK's public IPv4 lists without recalculating the ranges."""

import argparse
import concurrent.futures
import ipaddress
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlencode
from urllib.request import Request, urlopen


PORTALS = {'main': 'iplist.opencck.org', 'russia': 'russia.iplist.opencck.org'}
SELECTOR = re.compile(r'[a-z0-9][a-z0-9._@-]{0,127}\Z')
MAX_BODY = 2 * 1024 * 1024
MAX_ENTRIES = 65536


def get(host, **parameters):
    request = Request('https://' + host + '/?' + urlencode(parameters),
                      headers={'User-Agent': 'Bandju-OpenCCK-Mirror/1'})
    with urlopen(request, timeout=12) as reply:
        payload = reply.read(MAX_BODY + 1)
    if len(payload) > MAX_BODY:
        raise ValueError('OpenCCK response is too large')
    return payload.decode('utf-8-sig')


def key(value):
    if not isinstance(value, str) or not SELECTOR.fullmatch(value) or '..' in value:
        raise ValueError('Unsafe OpenCCK selector')
    return value


def list_text(entries):
    if not isinstance(entries, list) or not 0 < len(entries) <= MAX_ENTRIES:
        raise ValueError('Missing or oversized IPv4 list')
    prefixes = {str(ipaddress.IPv4Network(entry)) for entry in entries}
    if '0.0.0.0/0' in prefixes:
        raise ValueError('Unexpected default route')
    if len(prefixes) > MAX_ENTRIES:
        raise ValueError('Oversized IPv4 list')
    return '\n'.join(sorted(prefixes)) + '\n'


def snapshot():
    files, unavailable, tasks = {}, [], []
    for portal, host in PORTALS.items():
        index = json.loads(get(host, format='json', data='group'))
        if not isinstance(index, dict) or not index:
            raise ValueError(f'Invalid {portal} index')
        tasks.extend((portal, host, 'site', key(site)) for site in sorted(index))
        tasks.extend((portal, host, 'group', group) for group in sorted({key(group) for group in index.values()}))

    def fetch_list(task):
        portal, host, selector, name = task
        target = f'{portal}/{selector}/{name}.txt'
        try:
            return target, list_text(get(host, format='text', data='cidr4', **{selector: name}).split())
        except (OSError, TypeError, ValueError):
            return target, None

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for target, content in pool.map(fetch_list, tasks):
            if content is None:
                unavailable.append(target)
            else:
                files[target] = content
    if not files:
        raise ValueError('OpenCCK did not return any usable IPv4 lists')
    return {'files': files, 'unavailable': sorted(unavailable)}


def main():
    args = argparse.ArgumentParser()
    args.add_argument('--stdout', action='store_true', help='Emit the validated snapshot as JSON')
    options = args.parse_args()
    result = snapshot()
    for filename in result['unavailable']:
        print(f'Keeping previous copy where available: {filename}', file=sys.stderr)
    if options.stdout:
        print(json.dumps(result, separators=(',', ':')))
        return
    base = Path(__file__).resolve().parent / 'lists'
    for filename, content in result['files'].items():
        output = base / filename
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(content, encoding='ascii')
    print(f'Validated {len(result["files"])} OpenCCK lists')


if __name__ == '__main__':
    main()

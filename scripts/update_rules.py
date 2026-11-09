#!/usr/bin/env python3
"""Mirror public domain sets into fixed, bounded, lossless Surge shards."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 500_000
SOURCES = {
    'chinamax': ('https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Surge/ChinaMax/ChinaMax_Domain.list', 'ChinaMax_Domain.list', 8, 50_000),
    'reject': ('https://ruleset.skk.moe/List/domainset/reject.conf', 'reject.conf', 16, 50_000),
}

def digest(data):
    return hashlib.sha256(data).hexdigest()

def parse(data):
    text = data.decode('utf-8-sig')
    rules, comments = [], []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith(('#', '//', ';')):
            comments.append('# ' + line.lstrip('#/;').strip())
            continue
        if any(c.isspace() for c in line) or any(c in line for c in ',[]<>/\\'):
            raise ValueError('Unexpected domain-set entry; refusing publication')
        rules.append(line)
    return rules, comments

def split(data, key, url, buckets):
    rules, comments = parse(data)
    parts = [[] for _ in range(buckets)]
    for rule in rules:
        bucket = int.from_bytes(hashlib.sha256(rule.encode()).digest()[:8], 'big') % buckets
        parts[bucket].append(rule)
    files = {}
    for i, part in enumerate(parts):
        # Stable membership/order minimizes churn and transient cross-shard gaps.
        header = [f'# Mirror: {url}', f'# Shard: {i + 1}/{buckets}',
                  '# Generated losslessly; upstream notices follow.'] + comments
        payload = ('\n'.join(header + sorted(part)) + '\n').encode()
        if len(payload) >= MAX_BYTES:
            raise ValueError(f'{key}/{i:02d} exceeds {MAX_BYTES} bytes; keeping previous publication')
        files[f'{key}/{i:02d}.list'] = payload
    rebuilt = [r for payload in files.values() for r in parse(payload)[0]]
    if Counter(rebuilt) != Counter(rules):
        raise ValueError('Lossless verification failed')
    return files, len(rules)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-dir', type=Path, help='Use already downloaded public sources')
    args = parser.parse_args()
    previous_path = ROOT / 'manifest.json'
    previous = json.loads(previous_path.read_text()) if previous_path.exists() else {}
    generated = {}
    manifest = {'max_shard_bytes': MAX_BYTES, 'sources': {}}
    for key, (url, filename, buckets, minimum) in SOURCES.items():
        if args.input_dir:
            data = (args.input_dir / filename).read_bytes()
        else:
            request = urllib.request.Request(url, headers={'User-Agent': 'Eyeseas-Surge-Rule-Shards/1.0'})
            with urllib.request.urlopen(request, timeout=90) as response:
                data = response.read(32_000_001)
            if len(data) > 32_000_000:
                raise ValueError('Unexpectedly large upstream response')
        files, count = split(data, key, url, buckets)
        last_count = previous.get('sources', {}).get(key, {}).get('entries', 0)
        if count < minimum or (last_count and count < last_count * 0.8):
            raise ValueError(f'{key}: unexpectedly small source; keeping previous publication')
        generated.update({'rules/' + name: value for name, value in files.items()})
        generated['sources/' + filename] = data
        manifest['sources'][key] = {
            'url': url, 'sha256': digest(data), 'source_bytes': len(data), 'entries': count,
            'shards': [{'path': 'rules/' + name, 'bytes': len(value),
                        'sha256': digest(value), 'entries': len(parse(value)[0])}
                       for name, value in files.items()],
        }
    generated['manifest.json'] = (json.dumps(manifest, indent=2, ensure_ascii=False) + '\n').encode()
    # No publication files change until BOTH sources pass all checks.
    for name, data in generated.items():
        target = ROOT / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as tmp:
            tmp.write(data)
            temp_path = Path(tmp.name)
        temp_path.replace(target)
    for key, source in manifest['sources'].items():
        print(f"{key}: {source['entries']} entries, {len(source['shards'])} shards, "
              f"largest {max(s['bytes'] for s in source['shards'])} bytes; lossless OK")

if __name__ == '__main__':
    main()

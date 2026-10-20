"""Fetch pinned research inputs and inventory the existing XLS checkout."""
import hashlib
import json
from pathlib import Path
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parent
XLS = Path('/home/xls-developer/xls')
HLSFACTORY_COMMIT = '2aba8756de8e2fab1d1095b2483cfa695bf3be10'

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'xls-gepa-research'})
    return urllib.request.urlopen(req, timeout=60).read()

def main():
    for name in ('reference', 'logs', 'results', 'configs', 'vendor', 'candidates'):
        (ROOT / name).mkdir(exist_ok=True)
    commit = HLSFACTORY_COMMIT
    base = f'https://raw.githubusercontent.com/sharc-lab/HLSFactory/{commit}/hlsfactory/hls_dataset_sources/xls_upstream/idct_chen/'
    listing = json.loads(fetch(f'https://api.github.com/repos/sharc-lab/HLSFactory/contents/hlsfactory/hls_dataset_sources/xls_upstream/idct_chen?ref={commit}'))
    files = {}
    for entry in listing:
        if entry['type'] == 'file':
            data = fetch(base + entry['name'])
            (ROOT / 'reference' / entry['name']).write_bytes(data)
            files[entry['name']] = hashlib.sha256(data).hexdigest()
    source = (ROOT / 'reference/idct_chen.x').read_text()
    assert source.count('#[test]') == 5, 'Unexpected benchmark test count'
    xls_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=XLS, text=True).strip()
    status = subprocess.check_output(['git', 'status', '--short'], cwd=XLS, text=True)
    (ROOT / 'logs/xls-initial-status.txt').write_text(status)
    substantive = subprocess.check_output(['git', 'diff', '--ignore-space-at-eol', '--shortstat'], cwd=XLS, text=True)
    provenance = {'hlsfactory_commit': commit, 'source_url': base+'idct_chen.x', 'files_sha256': files,
                  'xls_commit': xls_commit, 'xls_substantive_diff': substantive, 'test_count': 5}
    # Targeted fix for the previously observed shell-genrule CRLF failure.
    target = XLS / 'xls/dslx/frontend/BUILD'
    old = target.read_bytes()
    if b'\r\n' in old:
        (ROOT / 'reference/frontend_BUILD.before').write_bytes(old)
        target.write_bytes(old.replace(b'\r\n', b'\n'))
        provenance['line_ending_fix'] = 'xls/dslx/frontend/BUILD: CRLF to LF'
    (ROOT / 'results/provenance.json').write_text(json.dumps(provenance, indent=2))
    print(json.dumps(provenance, indent=2))
    print(source[:7000])

if __name__ == '__main__':
    main()


"""Repair only the two source files implicated by observed shell failures."""
from setup import ROOT, XLS
import hashlib
import json

record_file = ROOT/'results/line-ending-repairs.json'
records = json.loads(record_file.read_text()) if record_file.exists() else []
if isinstance(records, dict):
    records = [records]
targets = [('xls/dslx/frontend/BUILD', 'frontend_BUILD.before'),
           ('dependency_support/bitwuzla/extension.bzl', 'bitwuzla_extension.before')]
for relative, backup in targets:
    target = XLS/relative
    data = target.read_bytes()
    if b'\r\n' not in data:
        print('Already LF:', relative)
        continue
    saved = ROOT/'reference'/backup
    if not saved.exists():
        saved.write_bytes(data)
    fixed = data.replace(b'\r\n', b'\n')
    target.write_bytes(fixed)
    records.append({'path': str(target), 'before_sha256': hashlib.sha256(data).hexdigest(),
                    'after_sha256': hashlib.sha256(fixed).hexdigest(),
                    'reason': 'Observed CRLF shell/genrule failure; targeted normalization only'})
    print('Targeted LF repair:', relative)
record_file.write_text(json.dumps(records, indent=2))


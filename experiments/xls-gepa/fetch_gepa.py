"""Pin and download official GEPA source; never invokes a model."""
import io
import json
import tarfile
from pathlib import Path
from setup import fetch, ROOT

commit = json.loads((ROOT/'results/gepa-version.json').read_text())['commit']
data = fetch(f'https://api.github.com/repos/gepa-ai/gepa/tarball/{commit}')
destination = ROOT / 'vendor/gepa'
destination.mkdir(parents=True, exist_ok=True)
with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
    for member in archive.getmembers():
        relative = Path(*Path(member.name).parts[1:])
        if member.isfile() and '..' not in relative.parts:
            target = destination / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.extractfile(member).read())
(ROOT / 'results/gepa-version.json').write_text(json.dumps({'repository': 'https://github.com/gepa-ai/gepa', 'commit': commit}, indent=2))
print(commit)
print((destination/'pyproject.toml').read_text()[:7000])


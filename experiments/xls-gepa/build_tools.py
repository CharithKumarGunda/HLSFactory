"""Build only the tools needed by this XLS-specific experiment."""
import json
import subprocess
import os
from pathlib import Path
import shutil
import signal
import time
from setup import ROOT, XLS

targets = ['//xls/dslx:interpreter_main', '//xls/dslx/ir_convert:ir_converter_main',
           '//xls/tools:opt_main', '//xls/tools:codegen_main', '//xls/tools:eval_ir_main',
           '//xls/tools:delay_info_main', '//xls/dev_tools:check_ir_equivalence_main']
command = ['bazel', 'build', '-c', 'opt', '--jobs=10', '--local_resources=memory=10000'] + targets
# Resume the authorized tool build with higher parallelism, retaining every cache.
# Only cancel the previous six-job client for this exact target set, never the server.
for process in Path('/proc').iterdir():
    if not process.name.isdigit():
        continue
    try:
        arguments = (process/'cmdline').read_bytes().decode().split('\0')
    except (FileNotFoundError, PermissionError, UnicodeDecodeError):
        continue
    if arguments and Path(arguments[0]).name == 'bazel' and 'build' in arguments and '--jobs=6' in arguments and all(target in arguments for target in targets):
        print('Gracefully cancel previous six-job client:', process.name, flush=True)
        os.kill(int(process.name), signal.SIGINT)
        limit = time.monotonic()+60
        while process.exists() and time.monotonic() < limit:
            time.sleep(0.5)
        if process.exists():
            raise RuntimeError('Previous build client did not exit; refusing a competing build')
        time.sleep(2)
        for name in ('build-tools.log', 'build-tools.exit'):
            previous = ROOT/'logs'/name
            if previous.exists():
                shutil.copy2(previous, ROOT/'logs'/('six-jobs-'+name))
(ROOT/'logs/build-command.json').write_text(json.dumps(command, indent=2))
with (ROOT/'logs/build-tools.log').open('w') as log:
    result = subprocess.run(command, cwd=XLS, stdout=log, stderr=subprocess.STDOUT)
(ROOT/'logs/build-tools.exit').write_text(str(result.returncode))
print('Build exit:', result.returncode)
raise SystemExit(result.returncode)


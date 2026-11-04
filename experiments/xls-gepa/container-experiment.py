"""Fixed build/evaluation workflow; no arbitrary commands or model calls."""
from pathlib import Path
import subprocess
import time

root = Path('/workspace')
with (root/'logs/pipeline.log').open('a') as log:
    for script in ('repair_line_endings.py', 'build_tools.py', 'validate_evaluator.py'):
        log.write(f'\n{time.time()}: running {script}\n')
        log.flush()
        result = subprocess.run(['python3', str(root/script)], stdout=log, stderr=subprocess.STDOUT)
        if result.returncode:
            (root/'logs/pipeline.exit').write_text(f'{script}: {result.returncode}')
            raise SystemExit(result.returncode)
        if (root/'STOP_AFTER_BUILD').exists():
            (root/'logs/pipeline.exit').write_text('Stopped by user after '+script)
            raise SystemExit(0)
(root/'logs/pipeline.exit').write_text('0')


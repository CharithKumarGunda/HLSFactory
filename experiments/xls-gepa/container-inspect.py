"""Read-only inventory and progress. No command input or mutation."""
from pathlib import Path
import subprocess

for command in [['ps', '-eo', 'pid,etime,pcpu,pmem,comm'], ['free', '-h'], ['df', '-h', '/']]:
    print(subprocess.check_output(command, text=True))
for name in ('build-tools.log', 'build-tools.exit', 'pipeline.log', 'pipeline.exit'):
    path = Path('/workspace/logs')/name
    if path.exists():
        print(name, ':\n', '\n'.join(path.read_text(errors='replace').splitlines()[-15:]))
base = Path('/home/xls-developer/xls/bazel-bin')
for name in ('xls/dslx/interpreter_main', 'xls/dslx/ir_convert/ir_converter_main',
             'xls/tools/opt_main', 'xls/tools/codegen_main', 'xls/tools/eval_ir_main',
             'xls/tools/delay_info_main', 'xls/dev_tools/check_ir_equivalence_main'):
    target = base/name
    print('Tool ready:' if target.is_file() else 'Tool pending:', name)


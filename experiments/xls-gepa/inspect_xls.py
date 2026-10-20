"""Save version-specific tool documentation without requiring binaries."""
from setup import ROOT, XLS
import subprocess

paths = ['xls/tools/codegen_main.cc', 'xls/tools/codegen_flags.cc',
         'xls/tools/delay_info_main.cc', 'xls/tools/delay_info_printer.cc',
         'xls/tools/eval_ir_main.cc', 'xls/tools/lec_main.cc',
         'xls/dslx/interpreter_main.cc', 'xls/dslx/ir_convert/ir_converter_main.cc',
         'xls/tools/BUILD', 'docs_src/delay_estimation.md', 'docs_src/scheduling.md']
paths += ['xls/dev_tools/check_ir_equivalence_main.cc',
          'xls/tools/codegen.cc',
          'xls/dslx/ir_convert/ir_converter_options_flags.cc',
          'xls/estimators/delay_model/unit_delay_estimator.cc',
          'xls/estimators/delay_model/delay_estimator.cc',
          'xls/estimators/delay_model/delay_estimator.h',
          'xls/estimators/delay_model/models/unit.textproto',
          'xls/estimators/delay_model/models/asap7.textproto',
          'xls/codegen/xls_metrics.proto', 'xls/tools/opt_flags.cc',
          'xls/tools/delay_info_flags.cc']
out = ROOT/'reference/xls_docs'
out.mkdir(exist_ok=True)
for name in paths:
    path = XLS/name
    if path.exists():
        (out/path.name).write_bytes(path.read_bytes().replace(b'\r\n', b'\n'))
for command in [['uname', '-a'], ['lscpu'], ['free', '-h'], ['df', '-h'], ['bazel', '--version']]:
    result = subprocess.run(command, cwd=XLS, capture_output=True, text=True, timeout=30)
    (ROOT/'logs'/('environment-'+command[0]+'.txt')).write_text(result.stdout+result.stderr)
print('Saved tool sources and machine inventory')


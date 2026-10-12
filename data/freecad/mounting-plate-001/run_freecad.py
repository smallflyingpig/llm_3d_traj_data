#!/usr/bin/env python3
"""Execute a local Python CAD job inside FreeCAD with reliable error reporting."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def find_executable(explicit=None):
    candidates = [explicit, os.environ.get('FREECAD_CMD'),
                  '/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd',
                  '/Applications/FreeCAD.app/Contents/MacOS/FreeCADCmd',
                  shutil.which('FreeCADCmd'), shutil.which('freecadcmd')]
    for item in candidates:
        if item and Path(item).is_file():
            return str(Path(item).resolve())
    raise FileNotFoundError('FreeCADCmd not found; set FREECAD_CMD or --executable.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--executable')
    parser.add_argument('--timeout', type=float, default=120)
    parser.add_argument('script', type=Path)
    parser.add_argument('args', nargs=argparse.REMAINDER)
    opts = parser.parse_args()
    script = opts.script.resolve(strict=True)
    executable = find_executable(opts.executable)
    args = opts.args[1:] if opts.args[:1] == ['--'] else opts.args
    with tempfile.TemporaryDirectory(prefix='freecad-job-') as scratch:
        scratch = Path(scratch)
        status = scratch / 'status.json'
        wrapper = scratch / 'job.py'
        wrapper.write_text(
            'import sys, runpy, json, traceback\n'
            f'sys.argv = {repr([str(script)] + args)}\n'
            f'sys.path.insert(0, {str(script.parent)!r})\n'
            'result = {"ok": False}\n'
            'try:\n'
            f'    runpy.run_path({str(script)!r}, run_name="__main__")\n'
            '    result["ok"] = True\n'
            'except SystemExit as exc:\n'
            '    result["ok"] = exc.code in (None, 0)\n'
            '    result["error"] = str(exc)\n'
            'except BaseException:\n'
            '    result["error"] = traceback.format_exc()\n'
            'finally:\n'
            f'    with open({str(status)!r}, "w") as f: json.dump(result, f)\n',
            encoding='utf-8')
        # Avoid app launchers that dump inherited environment variables.
        env = {k: v for k, v in os.environ.items()
               if k in {'HOME', 'PATH', 'TMPDIR', 'LANG', 'LC_ALL', 'USER', 'LOGNAME', 'SYSTEMROOT'}}
        try:
            proc = subprocess.run([executable, '-u', str(scratch / 'user.cfg'),
                                   '-s', str(scratch / 'system.cfg'), str(wrapper)],
                                  env=env, stdin=subprocess.DEVNULL, capture_output=True,
                                  text=True, errors='replace', timeout=opts.timeout)
        except subprocess.TimeoutExpired:
            print('FreeCAD job timed out; check partial outputs before retrying.', file=sys.stderr)
            return 124
        if proc.stdout:
            print(proc.stdout, end='')
        if proc.stderr:
            print(proc.stderr, end='', file=sys.stderr)
        if not status.exists():
            print('FreeCAD did not complete the job. If Qt reports missing neon on macOS, '
                  'retry with approved normal-host execution.', file=sys.stderr)
            return 1
        result = json.loads(status.read_text())
        if not result['ok']:
            print(result.get('error', 'CAD job failed'), file=sys.stderr)
            return 1
        return 0 if proc.returncode == 0 else 1


if __name__ == '__main__':
    sys.exit(main())

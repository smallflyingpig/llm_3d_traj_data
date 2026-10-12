"""Launch a separate FreeCAD GUI instance with isolated configuration and clean env."""
import json
import os
from pathlib import Path
import subprocess
import tempfile

root = Path(__file__).resolve().parent
status = root / 'render-result.json'
if status.exists():
    raise FileExistsError('Render result already exists; review before another render.')
env = {key: value for key, value in os.environ.items()
       if key in {'HOME', 'PATH', 'TMPDIR', 'LANG', 'LC_ALL', 'USER', 'LOGNAME'}}
with tempfile.TemporaryDirectory(prefix='freecad-preview-') as tmp:
    proc = subprocess.run(
        ['/Applications/FreeCAD.app/Contents/Resources/bin/freecad',
         '-u', str(Path(tmp)/'user.cfg'), '-s', str(Path(tmp)/'system.cfg'),
         str(root/'render_preview.FCMacro')],
        env=env, stdin=subprocess.DEVNULL, capture_output=True, text=True,
        errors='replace', timeout=90)
    (root/'render.log').write_text(proc.stdout+'\n'+proc.stderr)
    if not status.exists():
        raise RuntimeError('FreeCAD GUI did not produce render-result.json; inspect render.log')
    report = json.loads(status.read_text())
    print(json.dumps({'process_exit_code': proc.returncode, **report}, indent=2))
    if not report['passed'] or proc.returncode != 0:
        raise SystemExit(1)

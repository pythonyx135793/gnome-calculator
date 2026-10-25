"""First original-source native build; no application edits or fabricated green."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import traceback

REPO = Path(os.environ['GITHUB_WORKSPACE']).resolve()
HERE = Path(__file__).resolve().parent
TASK = Path(os.environ['RUNNER_TEMP']).resolve()/'gnome-r1461'
E = TASK/'evidence'
E.mkdir(parents=True, exist_ok=True)
SOURCE = json.loads((HERE/'source.json').read_bytes())

def save(name, value):
    (E/name).write_text(json.dumps(value, indent=2)+'\n')

def source_guard(stage):
    errors=[]
    for item in SOURCE['files']:
        data=(REPO/item['path']).read_bytes()
        if len(data)!=item['bytes'] or hashlib.sha256(data).hexdigest()!=item['sha256']:
            errors.append(item['path'])
    save(stage+'-source.json',dict(files=len(SOURCE['files']),failures=errors,commit=SOURCE['commit']))
    assert not errors, errors

result=dict(status='STARTED',original=SOURCE['commit'],application_edited=False)
try:
    actual=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()
    assert actual==os.environ['GITHUB_SHA']
    parent=subprocess.check_output(['git','rev-parse','HEAD^'],cwd=REPO,text=True).strip()
    assert parent==SOURCE['commit'], (parent,SOURCE['commit'])
    changed=subprocess.check_output(['git','diff','--name-only',parent,actual],cwd=REPO,text=True).splitlines()
    allowed={'.github/workflows/gnome-native-baseline-r1461.yml'} | {'proof/calculator-date-baseline-r1461/'+name for name in ['ARTIFACTS.json','source.json','guard.py','run.py','smoke.py','export.py']}
    assert set(changed)==allowed, changed
    save('exact-proof.json',dict(proof=actual,original=parent,changed=changed))
    source_guard('before')
    for name in ['home','cache','config','data','runtime','schemas']:
        (TASK/name).mkdir(exist_ok=True, mode=0o700)
    shutil.copyfile(REPO/'data/org.gnome.calculator.gschema.xml', TASK/'schemas/org.gnome.calculator.gschema.xml')
    subprocess.run(['/usr/bin/glib-compile-schemas',str(TASK/'schemas')],check=True)
    environment={
        'PATH':'/usr/bin:/bin', 'HOME':str(TASK/'home'), 'LANG':'C.UTF-8', 'LC_ALL':'C.UTF-8',
        'XDG_CACHE_HOME':str(TASK/'cache'), 'XDG_CONFIG_HOME':str(TASK/'config'),
        'XDG_DATA_HOME':str(TASK/'data'), 'XDG_RUNTIME_DIR':str(TASK/'runtime'),
        'GSETTINGS_BACKEND':'memory', 'GSETTINGS_SCHEMA_DIR':str(TASK/'schemas'),
        'PYTHONDONTWRITEBYTECODE':'1', 'NO_AT_BRIDGE':'0', 'GNOME_PROOF_TASK':str(TASK)
    }
    config=dict(task=str(TASK),repo=str(REPO),uid=os.getuid(),gid=os.getgid(),
        outer_network_namespace=os.readlink('/proc/self/ns/net'),environment=environment,
        commands=[
            dict(name='meson-version',argv=['/usr/bin/meson','--version'],timeout_seconds=10),
            dict(name='vala-version',argv=['/usr/bin/valac','--version'],timeout_seconds=10),
            dict(name='meson-setup',argv=['/usr/bin/meson','setup',str(TASK/'build'),str(REPO),'-Dui-tests=true','--prefix='+str(TASK/'install')],timeout_seconds=180),
            dict(name='native-build',argv=['/usr/bin/meson','compile','-C',str(TASK/'build'),'-j','2'],timeout_seconds=600),
            dict(name='stock-tests',argv=['/usr/bin/dbus-run-session','--','/usr/bin/xvfb-run','-a','/usr/bin/meson','test','-C',str(TASK/'build'),'--print-errorlogs'],timeout_seconds=300,capture_failure_and_continue=True),
            dict(name='native-window',argv=['/usr/bin/dbus-run-session','--','/usr/bin/xvfb-run','-a','/usr/bin/python3','-B',str(HERE/'smoke.py')],timeout_seconds=45,capture_failure_and_continue=True),
        ])
    save('execution-plan.json',config)
    (TASK/'execution.json').write_text(json.dumps(config,indent=2)+'\n')
    command=['/usr/bin/sudo','-n','/usr/bin/unshare','--mount','--net','--pid','--fork','--kill-child=SIGKILL','/usr/bin/python3','-B',str(HERE/'guard.py'),str(TASK/'execution.json')]
    with (E/'isolated.stdout').open('wb') as out,(E/'isolated.stderr').open('wb') as err:
        proc=subprocess.run(command,stdout=out,stderr=err,timeout=1050)
    result.update(status='ORIGINAL_NATIVE_BUILD_TEST_AND_WINDOW_PASS' if proc.returncode==0 else 'ORIGINAL_FAILURE_PRESERVED',exit_code=proc.returncode)
    logs=TASK/'build/meson-logs'
    if logs.exists():
        shutil.copytree(logs,E/'meson-logs')
    if proc.returncode:
        raise RuntimeError('original native build/test/window failed; inspect exact evidence')
except BaseException as error:
    result.update(status='FAIL_PRESERVED',error=str(error))
    (E/'failure.txt').write_text(traceback.format_exc())
finally:
    try:
        source_guard('after')
    except BaseException as error:
        result.update(status='SOURCE_GUARD_FAILED',guard_error=str(error))
    result['finished']=time.time()
    save('result.json',result)
    print(json.dumps(result),flush=True)
if result['status']!='ORIGINAL_NATIVE_BUILD_TEST_AND_WINDOW_PASS':
    raise SystemExit(1)

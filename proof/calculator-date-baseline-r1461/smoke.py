"""Observe the actual stock GTK application through its accessibility tree."""
import json
import os
from pathlib import Path
import subprocess
import time
import gi

gi.require_version('Gdk','3.0')
gi.require_version('Atspi','2.0')
from gi.repository import Gdk, Atspi

task=Path(os.environ['GNOME_PROOF_TASK'])
e=task/'evidence'
binary=task/'build/src/gnome-calculator'
with (e/'application.stdout').open('wb') as out,(e/'application.stderr').open('wb') as err:
    p=subprocess.Popen([str(binary)],stdout=out,stderr=err)
    try:
        app=None
        deadline=time.monotonic()+20
        while time.monotonic()<deadline:
            if p.poll() is not None:
                raise RuntimeError('native application exited early: '+str(p.returncode))
            desktop=Atspi.get_desktop(0)
            for i in range(desktop.get_child_count()):
                candidate=desktop.get_child_at_index(i)
                if candidate.get_process_id()==p.pid:
                    app=candidate
                    break
            if app and app.get_child_count():
                break
            time.sleep(0.1)
        assert app is not None and app.get_child_count(), 'No actual native window appeared'
        def tree(node,depth=0):
            return dict(name=node.get_name(),role=node.get_role_name(),children=[tree(node.get_child_at_index(i),depth+1) for i in range(min(node.get_child_count(),100))] if depth<6 else [])
        observed=tree(app)
        (e/'native-window-ax.json').write_text(json.dumps(observed,indent=2)+'\n')
        screen=Gdk.Screen.get_default()
        assert screen is not None
        pixbuf=Gdk.pixbuf_get_from_window(screen.get_root_window(),0,0,screen.get_width(),screen.get_height())
        assert pixbuf is not None
        pixbuf.savev(str(e/'native-window.png'),'png',[],[])
        (e/'native-window-result.json').write_text(json.dumps(dict(status='ACTUAL_STOCK_WINDOW_VISIBLE',pid=p.pid,process_alive=p.poll() is None,not_date_feature_proof=True),indent=2)+'\n')
        print('ACTUAL_STOCK_WINDOW_VISIBLE',flush=True)
    finally:
        if p.poll() is None:
            p.terminate()
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait()

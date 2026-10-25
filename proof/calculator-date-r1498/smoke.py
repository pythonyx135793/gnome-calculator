"""Exercise the actual GTK application through its public accessibility interfaces."""
import json, os, subprocess, time, traceback
from pathlib import Path
import gi
gi.require_version('Atspi','2.0')
gi.require_version('Gdk','3.0')
from gi.repository import Atspi, Gdk, GLib

task=Path(os.environ['GNOME_PROOF_TASK'])
e=task/'evidence'
records=[]
p=None
app=None

def pump():
    context=GLib.MainContext.default()
    while context.pending():
        context.iteration(False)

def descendants(node, depth=0):
    yield node
    if depth<18:
        for index in range(min(node.get_child_count(),150)):
            child=node.get_child_at_index(index)
            if child is not None:
                yield from descendants(child,depth+1)

def wait_for(action, description, timeout=8):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        pump()
        if p.poll() is not None:
            raise RuntimeError('Application exited during '+description+': '+str(p.returncode))
        value=action()
        if value:
            return value
        time.sleep(.05)
    raise AssertionError('Timed out: '+description)

def find(predicate, root=None):
    for node in descendants(root or app):
        if predicate(node):
            return node
    return None

def showing(node):
    return node.get_state_set().contains(Atspi.StateType.SHOWING)

def control(name, root=None):
    return wait_for(lambda:find(lambda n:n.get_name()==name and showing(n) and n.get_action_iface() is not None,root),name)

def click(node):
    interface=node.get_action_iface()
    assert interface is not None and interface.do_action(0)
    pump()

def entry(name, dialog):
    return wait_for(lambda:find(lambda n:n.get_name()==name and n.get_editable_text_iface() is not None,dialog),name)

def set_entry(name, text, dialog):
    node=entry(name,dialog)
    assert node.get_editable_text_iface().set_text_contents(text)
    wait_for(lambda:Atspi.Text.get_text(node,0,-1)==text,'entry readback '+name)

def output(description, dialog):
    node=find(lambda n:n.get_description()==description,dialog)
    assert node is not None,description
    interface=node.get_text_iface()
    return Atspi.Text.get_text(node,0,-1) if interface is not None else node.get_name()

def screenshot(name):
    pump()
    screen=Gdk.Screen.get_default()
    image=Gdk.pixbuf_get_from_window(screen.get_root_window(),0,0,screen.get_width(),screen.get_height())
    assert image is not None
    image.savev(str(e/(name+'.png')),'png',[],[])

def record(name, value):
    records.append(dict(name=name,observed=value))
    (e/'native-date-cases.json').write_text(json.dumps(records,indent=2)+'\n')
    print('NATIVE_DATE_CASE '+name+' '+json.dumps(value),flush=True)

def choose(mode, dialog):
    click(control('Operation',dialog))
    click(control(mode,app))
    # A real mode change must also update the form and clear its old answer.
    wait_for(lambda:output('Date calculation result',dialog)=='','cleared previous mode result')

def calculate(expected, dialog):
    click(control('Calculate',dialog))
    wait_for(lambda:output('Date calculation result',dialog)==expected,'result '+expected)
    assert output('Date calculation error',dialog)==''
    return expected

try:
    with (e/'application.stdout').open('wb') as out,(e/'application.stderr').open('wb') as err:
        p=subprocess.Popen([str(task/'build/src/gnome-calculator')],stdout=out,stderr=err)
        def locate_app():
            desktop=Atspi.get_desktop(0)
            for index in range(desktop.get_child_count()):
                node=desktop.get_child_at_index(index)
                if node.get_process_id()==p.pid and node.get_child_count():
                    return node
        app=wait_for(locate_app,'actual native application',20)
        click(control('Primary menu'))
        click(control('Date Calculation'))
        dialog=wait_for(lambda:find(lambda n:n.get_name()=='Date Calculation' and n.get_role_name() in ['dialog','frame']),'date dialog')
        set_entry('Start date','2000-02-28',dialog)
        set_entry('End date','2000-03-01',dialog)
        record('elapsed-and-leap',calculate('Elapsed days (end minus start): 2\nLeap days: 1',dialog))
        screenshot('date-difference')

        choose('Add days',dialog)
        set_entry('Start date','2000-02-28',dialog)
        set_entry('Number of days','1',dialog)
        record('add-days',calculate('Resulting date: 2000-02-29',dialog))
        screenshot('date-add')

        choose('Subtract days',dialog)
        set_entry('Start date','2000-03-01',dialog)
        record('subtract-days',calculate('Resulting date: 2000-02-29',dialog))
        screenshot('date-subtract')

        set_entry('Start date','1900-02-29',dialog)
        assert output('Date calculation result',dialog)==''
        click(control('Calculate',dialog))
        wait_for(lambda:'valid date' in output('Date calculation error',dialog),'invalid date error')
        assert output('Date calculation result',dialog)==''
        record('invalid-date-no-stale-result',output('Date calculation error',dialog))
        screenshot('date-invalid')

        set_entry('Start date','0001-01-01',dialog)
        click(control('Calculate',dialog))
        wait_for(lambda:'result must be between' in output('Date calculation error',dialog),'range error')
        record('underflow-error',output('Date calculation error',dialog))

        set_entry('Start date','2000-03-01',dialog)
        set_entry('Number of days','1.5',dialog)
        click(control('Calculate',dialog))
        wait_for(lambda:'whole number' in output('Date calculation error',dialog),'integer error')
        record('fractional-offset-error',output('Date calculation error',dialog))

        set_entry('Number of days','-1',dialog)
        record('negative-offset-recovery',calculate('Resulting date: 2000-03-02',dialog))
        screenshot('date-recovery')

        set_entry('Number of days','0',dialog)
        # GTK Entry's native activate action follows the documented Enter/default-button path.
        click(entry('Number of days',dialog))
        wait_for(lambda:output('Date calculation result',dialog)=='Resulting date: 2000-03-01','entry activation/default Calculate')
        record('entry-default-activation',output('Date calculation result',dialog))

        click(control('Close',dialog))
        wait_for(lambda:not find(lambda n:n.get_name()=='Date Calculation' and n.get_role_name()=='dialog'),'dialog close')
        click(control('Primary menu'))
        click(control('Date Calculation'))
        dialog=wait_for(lambda:find(lambda n:n.get_name()=='Date Calculation' and n.get_role_name() in ['dialog','frame']),'reopened dialog')
        assert output('Date calculation result',dialog)==''
        record('close-and-reopen',dict(main_window_alive=p.poll() is None,blank_new_result=True))
        (e/'native-date-result.json').write_text(json.dumps(dict(status='ACTUAL_NATIVE_DATE_FLOWS_PASS',cases=len(records),pid=p.pid),indent=2)+'\n')
except BaseException:
    (e/'native-date-failure.txt').write_text(traceback.format_exc())
    if app is not None:
        try:
            snapshot=[dict(name=n.get_name(),description=n.get_description(),role=n.get_role_name(),showing=showing(n)) for n in descendants(app)]
            (e/'native-date-failure-ax.json').write_text(json.dumps(snapshot,indent=2)+'\n')
            screenshot('date-failure')
        except BaseException:
            pass
    raise
finally:
    if p is not None and p.poll() is None:
        p.terminate()
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            p.kill()
            p.wait()

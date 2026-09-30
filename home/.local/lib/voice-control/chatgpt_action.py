"""Prepare a prompt in the ChatGPT composer without submitting or replacing drafts."""
import json
import time
import gi
gi.require_version('Atspi','2.0')
from gi.repository import Atspi

def prepare(prompt,run,notify):
    clients=json.loads(run(['hyprctl','clients','-j']).stdout)
    target=next((c for c in clients if c['class']=='chatgpt'),None)
    if not target:
        run(['hyprctl','dispatch','hl.dsp.exec_cmd("chatgpt")'])
        for _ in range(30):
            time.sleep(.2)
            clients=json.loads(run(['hyprctl','clients','-j']).stdout)
            target=next((c for c in clients if c['class']=='chatgpt'),None)
            if target:break
    if not target:
        notify('ChatGPT has not opened yet. Try again once it is ready.')
        return
    run(['hyprctl','dispatch','hl.dsp.focus({window='+json.dumps('address:'+target['address'])+'})'])
    Atspi.set_timeout(120,200)
    desktop=Atspi.get_desktop(0)
    candidates=[]
    for i in range(desktop.get_child_count()):
        app=desktop.get_child_at_index(i)
        if app.get_process_id()!=target['pid']:continue
        stack=[app];count=0
        while stack and count<2000:
            item=stack.pop();count+=1
            try:
                states=item.get_state_set()
                if states.contains(Atspi.StateType.EDITABLE) and item.get_role()==Atspi.Role.ENTRY and item.get_name() in ('Do anything','Ask anything','Message ChatGPT','Message'):
                    candidates.append(item)
                for j in range(item.get_child_count()):
                    child=item.get_child_at_index(j)
                    if child:stack.append(child)
            except Exception:continue
    if len(candidates)!=1:
        notify('ChatGPT is open. Click its message box, then repeat your request.')
        return
    composer=candidates[0]
    try:
        draft=composer.get_text_iface().get_text(0,-1)
        if draft.strip():
            notify('ChatGPT already has a draft. Send or clear it first; I have not replaced it.')
            return
        if not composer.get_component_iface().grab_focus():
            notify('Click the ChatGPT message box and try again.')
            return
    except Exception:
        notify('Could not safely focus the ChatGPT message box. Click it and try again.')
        return
    active=json.loads(run(['hyprctl','activewindow','-j']).stdout)
    if active.get('address')!=target['address']:return
    result=run(['wtype','--',prompt.replace('\r',' ').replace('\n',' ')])
    if result.returncode:raise RuntimeError(result.stderr)
    notify('Your request is in ChatGPT. Press button 4 to send it.')

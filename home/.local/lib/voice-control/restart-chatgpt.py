#!/usr/bin/env python3
import json, os, signal, subprocess, sys, time
from pathlib import Path
pid=int(sys.argv[1])
status=Path.home()/'.local/state/voice-control/restart-status.json'
process=Path(f'/proc/{pid}')
args=(process/'cmdline').read_bytes().split(b'\0')
if (process/'exe').resolve()!=Path('/usr/lib/chatgpt/ChatGPT') or b'--type=' in b' '.join(args):
    raise SystemExit('Refusing to restart an unexpected process')
old_env={}
for entry in (process/'environ').read_bytes().split(b'\0'):
    if b'=' in entry:
        key,value=entry.split(b'=',1)
        old_env[key.decode()]=value.decode()
env=os.environ.copy()
for key in ('DISPLAY','WAYLAND_DISPLAY','XDG_RUNTIME_DIR','XDG_SESSION_TYPE','XDG_CURRENT_DESKTOP','DBUS_SESSION_BUS_ADDRESS','HYPRLAND_INSTANCE_SIGNATURE'):
    if key in old_env: env[key]=old_env[key]
env.pop('NO_AT_BRIDGE',None)
status.write_text(json.dumps({'status':'restarting','old_pid':pid}))
time.sleep(2)
os.kill(pid,signal.SIGTERM)
for _ in range(100):
    if not process.exists(): break
    try:
        if (process/'stat').read_text().split(') ',1)[1].startswith('Z'): break
    except FileNotFoundError: break
    time.sleep(.2)
else:
    status.write_text(json.dumps({'status':'blocked','reason':'ChatGPT did not exit gracefully'}))
    subprocess.run(['notify-send','Voice setup','ChatGPT did not exit. Please close and reopen it to enable focus detection.'],env=env)
    raise SystemExit(1)
status.write_text(json.dumps({'status':'launching','old_pid':pid,'launcher_pid':os.getpid()}))
os.execvpe('/usr/bin/chatgpt',['/usr/bin/chatgpt'],env)

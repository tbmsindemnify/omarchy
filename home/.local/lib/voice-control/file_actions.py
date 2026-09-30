"""File operations use Nautilus' native API and its selected-file clipboard."""
import json
from pathlib import Path
import re
import subprocess
import time
from urllib.parse import urlparse, unquote
import dbus

FILE_MANAGERS={'org.gnome.Nautilus','nautilus'}

def destination_folder(name, source_dirs=()):
    name=name.strip().rstrip('/').replace(' folder','').strip()
    if not name or name in ('.','..'):
        raise ValueError('Which destination folder should I use?')
    common={'home':Path.home()}
    for label in ('Documents','Downloads','Desktop','Pictures','Videos','Music'):
        r=subprocess.run(['xdg-user-dir',label.upper()],capture_output=True,text=True)
        common[label.lower()]=Path(r.stdout.strip()) if r.returncode==0 and r.stdout.strip() else Path.home()/label
    key=re.sub(r'^(my|the) ','',name.lower())
    if key in common:
        choices=[common[key]]
    elif name.startswith(('/','~/')):
        choices=[Path(name).expanduser()]
    else:
        choices=[]
        for base in set([Path.home(),Path.home()/'Documents',*source_dirs]):
            if base.is_dir():
                choices.extend(p for p in base.iterdir() if p.is_dir() and p.name.casefold()==name.casefold())
    choices=list({p.resolve() for p in choices if p.is_dir()})
    if len(choices)!=1:
        raise ValueError('Please give an existing, unambiguous destination folder, such as Downloads or a full path.')
    return choices[0]

def selected_paths(target, run):
    active=json.loads(run(['hyprctl','activewindow','-j']).stdout)
    if active.get('address')!=target or active.get('class') not in FILE_MANAGERS:
        raise ValueError('Select the files in Files first, then repeat your request.')
    # Replace stale clipboard data so a failed copy can never reuse old files.
    # wl-copy forks a clipboard owner; do not capture its inherited pipes.
    subprocess.run(['wl-copy','--type','text/plain','Voice file selection pending'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True, timeout=3)
    r=run(['wtype','-M','ctrl','-k','c','-m','ctrl'])
    if r.returncode: raise ValueError('Could not read the file selection')
    data=''
    for _ in range(20):
        r=run(['wl-paste','--no-newline','--type','text/uri-list'])
        if r.returncode==0 and r.stdout.strip():
            data=r.stdout;break
        time.sleep(.05)
    paths=[]
    for uri in data.splitlines():
        if not uri or uri.startswith('#'):continue
        parsed=urlparse(uri)
        if parsed.scheme!='file' or parsed.netloc not in ('','localhost'):
            raise ValueError('This file action currently supports local files only.')
        p=Path(unquote(parsed.path))
        if not p.exists() and not p.is_symlink():raise ValueError('A selected file is no longer available.')
        paths.append(p)
    if not paths:raise ValueError('No files are selected. Select them and try again.')
    return paths

def transfer(paths,destination,move=False):
    # Collision checking happens before any request. Nautilus also handles races
    # and presents its native conflict UI rather than silently replacing files.
    for source in paths:
        target=destination/source.name
        if target.exists() or target.is_symlink():
            raise ValueError('A file named '+source.name+' already exists there. Choose another folder or resolve it in Files.')
        if source.is_dir() and (destination==source.resolve() or source.resolve() in destination.parents):
            raise ValueError('A folder cannot be placed inside itself.')
    bus=dbus.SessionBus()
    obj=bus.get_object('org.gnome.Nautilus','/org/gnome/Nautilus/FileOperations2')
    api=dbus.Interface(obj,'org.gnome.Nautilus.FileOperations2')
    method=api.MoveURIs if move else api.CopyURIs
    method(dbus.Array([p.absolute().as_uri() for p in paths],signature='s'),destination.as_uri(),dbus.Dictionary({},signature='sv'))

def execute(action,name,target,run,notify):
    paths=selected_paths(target,run)
    destination=destination_folder(name,{p.parent for p in paths})
    active=json.loads(run(['hyprctl','activewindow','-j']).stdout)
    if active.get('address')!=target:raise ValueError('Window changed; file action cancelled.')
    transfer(paths,destination,move=action=='move')
    notify(('Moving ' if action=='move' else 'Copying ')+str(len(paths))+' selected item(s) to '+str(destination))

#!/usr/bin/env python3
"""Register the optional unpacked Edge extension's native host after config install."""
import json
from pathlib import Path
home=Path.home()
host=home/'.local/lib/tbm-workspace-menu/host.py'
if not host.is_file():raise SystemExit('Run ./install.sh --apply first.')
dest=home/'.config/microsoft-edge/NativeMessagingHosts/com.tbm.workspace_menu.json'
if dest.exists():raise SystemExit('A host registration already exists; review it rather than overwriting.')
dest.parent.mkdir(parents=True,exist_ok=True)
dest.write_text(json.dumps({'name':'com.tbm.workspace_menu','description':'Move the focused Edge window to a local workspace','path':str(host),'type':'stdio','allowed_origins':['chrome-extension://odacgeohnfjljnjfgapafamddgfgnlkj/']},indent=2)+'\n')
print('Host registered. Load extensions/edge-workspace-menu as an unpacked extension in edge://extensions.')

"""Match configured keybinding names and explicit conversational aliases."""
import json
from pathlib import Path
import re
import subprocess
import time
import socket
import urllib.error

EXCLUDED = {'Toggle dictation', 'Start dictation (push-to-talk)', 'Stop dictation (push-to-talk)',
            'Toggle voice dictation (mouse button 5)', 'Send message (mouse button 4)',
            'Voice button 4 down', 'Voice button 4 release', 'Dictation or voice command',
            'Move window', 'Resize window'}

def normalize(text):
    text = text.lower().replace('chat g p t', 'chatgpt').replace('chat gpt', 'chatgpt').replace('fullscreen', 'full screen')
    text = re.sub(r'[^a-z0-9 ]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'^please | please$', '', text)
    for word, number in [('one','1'),('two','2'),('three','3'),('four','4'),('five','5'),('six','6'),('seven','7'),('eight','8'),('nine','9'),('ten','10')]:
        text = re.sub(r'\b'+word+r'\b', number, text)
    return text

ALIASES = {
 'make this window split screen': 'Toggle window split',
 'split screen': 'Toggle window split',
 'split this window': 'Toggle window split',
 'open my browser': 'Browser', 'open the browser': 'Browser',
 'open my files': 'File manager', 'open files': 'File manager',
 'open a terminal': 'Terminal', 'open the terminal': 'Terminal',
 'switch windows': 'Focus on next window', 'next window': 'Focus on next window',
 'previous window': 'Focus on previous window',
 'close this window': 'Close window', 'close the window': 'Close window',
 'turn the volume up': 'Volume up', 'turn up the volume': 'Volume up', 'turn volume up': 'Volume up',
 'turn the volume down': 'Volume down', 'turn down the volume': 'Volume down', 'turn volume down': 'Volume down',
 'take a screenshot': 'Screenshot', 'take screenshot': 'Screenshot',
 'make this full screen': 'Full screen', 'make it full screen': 'Full screen',
 'make the window full screen': 'Full screen',
 'make this window full screen': 'Full screen', 'make window full screen': 'Full screen',
 'make windows full screen': 'Full screen', 'go full screen': 'Full screen',
 'exit full screen': 'Full screen', 'maximize window': 'Full width', 'maximize this window': 'Full width',
 'expand window': 'Full width', 'make window bigger': 'Full width',
 'move window left': 'Swap window to the left', 'move window right': 'Swap window to the right',
 'move window up': 'Swap window up', 'move window down': 'Swap window down',
 'copy': 'Universal copy', 'paste': 'Universal paste', 'cut': 'Universal cut',
 'start screen recording': 'Screenrecording', 'stop screen recording': 'Screenrecording',
 'screen recording': 'Screenrecording',
}

def catalog():
    bindings = json.loads(subprocess.check_output(['hyprctl', 'binds', '-j'], text=True))
    return sorted({b['description'] for b in bindings if b.get('description') and b['description'] not in EXCLUDED and not b.get('release') and not b.get('mouse')})

def resolve(text, descriptions):
    phrase = normalize(text)
    phrase = re.sub(r'^(?:can|could|would|will) you (?:please )?', '', phrase)
    phrase = re.sub(r'^(?:i want you to|i would like you to|id like you to) ', '', phrase)
    if phrase in ('cancel', 'never mind', 'nevermind', 'stop'):
        return ('cancel', None)
    if phrase in ('print', 'print document', 'print this document', 'print the document', 'open print dialog'):
        return ('keys', ['-M','ctrl','-k','p','-m','ctrl'])
    if phrase in ('save', 'save file', 'save document'):
        return ('keys', ['-M','ctrl','-k','s','-m','ctrl'])
    if phrase in ('select all',):
        return ('keys', ['-M','ctrl','-k','a','-m','ctrl'])
    if phrase in ('undo','redo'):
        return ('keys', ['-M','ctrl','-k','z' if phrase=='undo' else 'y','-m','ctrl'])
    if phrase in ('new file', 'create file', 'create a file', 'create a new file'):
        return ('file', 'Untitled-' + time.strftime('%Y%m%d-%H%M%S') + '.txt')
    if re.match(r'^(?:create|new)(?: a)? file (?:called|named) ', text, re.I):
        name = re.split(r'^(?:create|new)(?: a)? file (?:called|named) ', text, flags=re.I)[1].strip().rstrip('.!?')
        name = re.sub(r'\s+dot\s+', '.', name, flags=re.I)
        if not name or len(name)>120 or '/' in name or '\\' in name or name.startswith('.') or any(ord(c)<32 for c in name):
            return ('invalid', 'Use a simple filename without folders')
        if '.' not in name: name += '.txt'
        return ('file', name)
    if phrase in ('switch to chatgpt',): return ('chatgpt', None)
    choices = {normalize(d): d for d in descriptions}
    if phrase in ALIASES and ALIASES[phrase] in descriptions:
        return ('binding', ALIASES[phrase])
    for candidate in (phrase, re.sub(r'^(open|show|launch|start) (the |my )?', '', phrase)):
        if candidate in choices:
            return ('binding', choices[candidate])
    return ('unknown', None)

def dispatch(text, target, run, notify):
    descriptions = catalog()
    kind, value = resolve(text, descriptions)
    if kind == 'unknown':
        from semantic import interpret
        notify('Interpreting your command…')
        try:
            kind, value = interpret(text, descriptions)
        except (OSError, ValueError, KeyError, urllib.error.URLError, socket.timeout):
            notify('Could not interpret that request. The command reference is in Documents/Voice commands.md.')
            return
    if kind == 'clarify':
        notify(value)
        return
    if kind in ('unknown','invalid'):
        notify(value if kind=='invalid' else 'Command not recognized: ' + text[:140])
        return
    if kind == 'binding' and value in ('Full screen', 'Full width') and normalize(text) != normalize(value):
        mode = 'fullscreen' if value == 'Full screen' else 'maximized'
        state = 'unset' if re.search(r'\b(exit|leave|restore)\b', normalize(text)) else 'set'
        kind, value = 'fullscreen', {'mode':mode, 'action':state}
    if kind == 'cancel':
        notify('Cancelled')
        return
    active = json.loads(run(['hyprctl','activewindow','-j']).stdout)
    if active.get('address') != target:
        notify('Window changed while recording; command cancelled. Please try again.')
        return
    if kind == 'binding' and value == 'Toggle window split':
        clients = json.loads(run(['hyprctl', 'clients', '-j']).stdout)
        peers = [c for c in clients if c.get('workspace', {}).get('id') == active.get('workspace', {}).get('id') and not c.get('floating') and c.get('mapped', True)]
        if len(peers) < 2:
            notify('Split screen needs two windows on this workspace. Open another window here first.')
            return
    if kind == 'chatgpt_prompt':
        from chatgpt_action import prepare
        prepare(value, run, notify)
        return
    if kind == 'file_transfer':
        from file_actions import execute
        try:
            execute(value['action'], value['destination'], target, run, notify)
        except ValueError as error:
            notify(str(error))
        return
    if kind == 'fullscreen':
        expression = 'hl.dsp.window.fullscreen({mode=' + json.dumps(value['mode']) + ', action=' + json.dumps(value['action']) + '})'
        result = run(['hyprctl', 'dispatch', expression])
    elif kind == 'binding':
        result = run(['hyprctl','eval','voice_run(' + json.dumps(value) + ')'])
    elif kind == 'keys':
        result = run(['wtype', *value])
    elif kind == 'chatgpt':
        clients = json.loads(run(['hyprctl','clients','-j']).stdout)
        app = next((c for c in clients if c['class']=='chatgpt'),None)
        if app:
            result = run(['hyprctl','dispatch','hl.dsp.focus({window = '+json.dumps('address:'+app['address'])+'})'])
        else:
            result = run(['hyprctl','eval','voice_run("ChatGPT")'])
    elif kind == 'file':
        directory = Path.home()/'Documents'/'Voice files'
        directory.mkdir(exist_ok=True)
        path = directory/value
        try:
            with path.open('x'): pass
        except FileExistsError:
            notify('File already exists: ' + value)
            return
        notify('Created ' + str(path))
        return
    if result.returncode:
        raise RuntimeError(result.stderr or result.stdout)
    notify(('Print dialog opened' if kind=='keys' and value[3]=='p' else 'Done: '+text[:120]))

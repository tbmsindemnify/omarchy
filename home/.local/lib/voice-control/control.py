#!/usr/bin/env python3
"""Local, explicit desktop voice commands using the existing Voxtype daemon."""
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

RUNTIME = Path(os.environ.get('XDG_RUNTIME_DIR', f'/run/user/{os.getuid()}')) / 'desktop-voice-control'
BOUNCE_SECONDS = 0.6

def log_event(message):
    RUNTIME.mkdir(mode=0o700, parents=True, exist_ok=True)
    with (RUNTIME / 'events.log').open('a') as stream:
        stream.write(time.strftime('%Y-%m-%d %H:%M:%S ') + message + '\n')

def acquire_lock(lock, timeout=3.0):
    deadline = time.monotonic() + timeout
    while True:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return True
        except BlockingIOError:
            if time.monotonic() >= deadline:
                return False
            time.sleep(0.05)

def run(args, **kwargs):
    kwargs.setdefault('capture_output', True)
    return subprocess.run(args, text=True, timeout=kwargs.pop('timeout', 10), **kwargs)

def notify(message):
    run(['notify-send', '-a', 'Voice commands', '-t', '5000', 'Voice commands', message])

def execute(text, target):
    from actions import dispatch
    dispatch(text, target, run, notify)


def focus_mode():
    """Debounce flaky AT-SPI focus reports from Chromium/Electron chat boxes."""
    samples = []
    for _ in range(3):
        try:
            result = run(['python3', str(Path(__file__).with_name('focus.py'))], timeout=0.7)
            samples.append(result.stdout.strip() if result.returncode == 0 else 'unknown')
        except subprocess.TimeoutExpired:
            samples.append('unknown')
        time.sleep(0.04)
    if 'terminal' in samples:
        return 'terminal'
    if 'text' in samples:
        return 'text'
    if samples and all(sample == 'command' for sample in samples):
        return 'command'
    return 'unknown'

def main(mode):
    RUNTIME.mkdir(mode=0o700, exist_ok=True)
    state = RUNTIME / 'state.json'
    with (RUNTIME / 'lock').open('w') as lock:
        if not acquire_lock(lock):
            log_event('button ignored after waiting 3s for the previous dictation operation')
            notify('Voice control is still processing the previous recording. Try button 5 again.')
            return
        log_event('button 5 handled in mode=' + mode)
        if state.exists():
            recording = json.loads(state.read_text())
            path = Path(recording['file'])
            # Button 5 bounces: a second click within 0.6s of starting would stop
            # a near-empty recording that Whisper returns as nothing.
            if time.time() - recording.get('started', 0) < BOUNCE_SECONDS:
                log_event('button bounce ignored; still recording')
                return
            # The text box selected when the user finishes speaking is the
            # intended destination, even if recording started in another window.
            destination = recording.get('target')
            if recording.get('mode') == 'dictate':
                destination = json.loads(run(['hyprctl', 'activewindow', '-j']).stdout).get('address')
            try:
                notify('Processing speech…')
                log_event('stopping recording file=' + str(path))
                result = run(['voxtype', 'record', 'stop', '--wait', '--json', '--timeout', '180', '--wait-file', str(path)], timeout=185)
                if result.returncode == 0 and path.exists():
                    text = path.read_text().strip()
                    if text:
                        if recording.get('mode', 'command') == 'dictate':
                            # Preserve speech even if the user changes windows.
                            text = text.replace('\r', ' ').replace('\n', ' ')
                            recovery = RUNTIME / 'last-dictation.txt'
                            fd = os.open(recovery, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
                            with os.fdopen(fd, 'w') as saved:
                                saved.write(text)
                            log_event('transcript saved characters=' + str(len(text)))
                            copied = run(['wl-copy', '--type', 'text/plain;charset=utf-8', '--', text], capture_output=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                            if copied.returncode:
                                # Keep the transcript for recovery if the clipboard fails.
                                (RUNTIME / 'last-dictation.txt').write_text(text)
                                raise RuntimeError('Could not copy dictation; saved in ' + str(RUNTIME / 'last-dictation.txt'))
                            # wl-copy forks before the compositor necessarily publishes
                            # the selection. Wait briefly before sending Ctrl+V.
                            for _ in range(20):
                                clipboard = run(['wl-paste', '--no-newline'])
                                if clipboard.returncode == 0 and clipboard.stdout == text:
                                    break
                                time.sleep(0.025)
                            else:
                                # Don't drop the dictation: wl-copy already ran, so paste anyway.
                                log_event('clipboard check did not match got=' + repr(clipboard.stdout[:80]) + '; pasting anyway')
                            clients = json.loads(run(['hyprctl', 'clients', '-j']).stdout)
                            window = next((c for c in clients if c.get('address') == destination), None)
                            if window is None:
                                # Destination closed; fall back to whatever has focus now.
                                window = json.loads(run(['hyprctl', 'activewindow', '-j']).stdout)
                                destination = window.get('address')
                            if not destination:
                                log_event('paste skipped: no destination window')
                                notify('Dictation is on the clipboard; no window to paste into.')
                                return
                            # Omarchy tags every terminal (foot, org.omarchy.agent, ...);
                            # terminals paste with Ctrl+Shift+V, everything else Ctrl+V.
                            tags = {tag.rstrip('*') for tag in window.get('tags', [])}
                            from focus import TERMINAL_CLASSES
                            terminal = 'terminal' in tags or window.get('class', '').lower() in TERMINAL_CLASSES
                            mods = 'CTRL SHIFT' if terminal else 'CTRL'
                            # Focus-follows-mouse moves focus if the mouse drifts while
                            # clicking button 5, so refocus the destination, give it a
                            # moment to take keyboard focus, then send the paste chord
                            # with compositor-native key events (split down/up).
                            lua = ('hl.dispatch(hl.dsp.focus({window="address:' + destination + '"})); '
                                   'hl.timer(function() hl.dispatch(hl.dsp.send_key_state({mods="' + mods + '",key="code:55",state="down"})) end, '
                                   '{timeout=60,type="oneshot"}); '
                                   'hl.timer(function() hl.dispatch(hl.dsp.send_key_state({mods="' + mods + '",key="code:55",state="up"})) end, '
                                   '{timeout=110,type="oneshot"})')
                            result = run(['hyprctl', 'eval', lua])
                            if result.returncode:
                                raise RuntimeError(result.stderr)
                            log_event('dictation paste shortcut sent characters=' + str(len(text)) + ' terminal=' + str(terminal))
                        else:
                            execute(text, recording.get('target'))
                    else:
                        log_event('empty transcription')
                        notify('No speech detected')
                else:
                    log_event('transcription failed returncode=' + str(result.returncode))
                    notify('No speech heard. Click button 5 and try again.')
            finally:
                state.unlink(missing_ok=True)
                path.unlink(missing_ok=True)
            return
        status = run(['voxtype', 'status']).stdout.strip()
        if status != 'idle':
            # A recording started through another shortcut must not inject speech
            # into a shell or an unknown target when stopped by this button.
            run(['voxtype', 'record', 'cancel'])
            notify('Other recording cancelled. Click button 5 to start again.')
            return
        path = RUNTIME / ('command-' + str(time.time_ns()) + '.txt')
        target = json.loads(run(['hyprctl', 'activewindow', '-j']).stdout).get('address')
        result = run(['voxtype', 'record', 'start', '--file=' + str(path), '--no-auto-submit', '--no-smart-auto-submit'])
        if result.returncode:
            raise RuntimeError(result.stderr or result.stdout)
        notify('Listening… Click button 5 to finish.')
        # Ordinary button 5 always dictates; commands require the explicit chord.
        if mode == 'auto':
            mode = 'dictate'
        state.write_text(json.dumps({'file': str(path), 'target': target, 'mode': mode, 'started': time.time()}))
        log_event('recording started file=' + str(path) + ' target=' + str(target))
        if mode == 'command':
            notify('Listening for a command. Click button 5 to finish.')

if __name__ == '__main__':
    try:
        main(sys.argv[1] if len(sys.argv) > 1 else 'command')
    except Exception as error:
        import traceback
        log_event('ERROR ' + type(error).__name__ + ': ' + str(error)[:300] + ' | ' + traceback.format_exc().replace('\n', ' / ')[-600:])
        notify('Could not complete command: ' + str(error)[:160])
        raise

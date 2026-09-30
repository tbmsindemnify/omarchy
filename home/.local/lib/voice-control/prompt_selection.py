#!/usr/bin/env python3
"""Expand the current selection into a task prompt; never submit a rewrite."""
import fcntl
import os
from pathlib import Path
import subprocess
import time

from rewrite import active, copied_selection, notify, run, snapshot
from focus import TERMINAL_CLASSES

GUIDANCE = """First inspect the existing setup and relevant context. Identify weak assumptions and resolve what you can independently. Break the work into concrete tasks, each with a way to verify success.

Grill me on the important points I missed before committing to consequential choices. Challenge my assumptions candidly. Identify missing goals, constraints, dependencies, tradeoffs, edge cases, and success criteria that materially affect this task. First investigate what you can yourself; then ask a short, prioritized set of focused questions only about what remains unresolved. Explain briefly why each answer matters and recommend an option when useful. Do not invent my preferences or treat silence as approval. Continue independent, authorized work while awaiting answers; pause only the work that depends on them. If no consequential gaps remain, proceed without a forced interview.

Complete the authorized work, test the actual result, and report what changed, the evidence it works, and anything unresolved. Do not ask me to confirm completion when you can verify it yourself. Check against the requirements and the most likely failure; fix material gaps in one focused pass. Repeat only if a check fails, and stop when the criteria are met. If you find a recurring failure, propose a targeted improvement that would prevent it. Offer useful alternatives when they improve the outcome, without silently expanding the scope."""


def build_prompt(selected):
    # Keep every original requirement, number, name, and qualification intact.
    return "My desired outcome / original request:\n\n" + selected.strip() + "\n\n" + GUIDANCE


def handle():
    window = active()
    if not window.get('address'):
        return
    if window.get('class', '').lower() in TERMINAL_CLASSES:
        # Ctrl+C interrupts terminal jobs; preserve the existing Enter action.
        run(['wtype', '-k', 'Return'])
        return
    selected = copied_selection(window)
    if not selected:
        if active().get('address') == window['address']:
            run(['wtype', '-k', 'Return'])
        return
    if not selected.strip():
        notify('Select some words to create a prompt. Nothing sent.')
        return
    if GUIDANCE in selected:
        notify('This selection already contains the prompt guidance. Nothing sent.')
        return
    output = build_prompt(selected)
    runtime = Path(os.environ.get('XDG_RUNTIME_DIR', '/run/user/' + str(os.getuid())))
    for name, content in [('mouse4-original.txt', selected), ('mouse4-prompt.txt', output)]:
        fd = os.open(runtime / name, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, 'w') as saved:
            saved.write(content)
    field = snapshot(window)
    editable = bool(field and not field.get('blocked') and field.get('mode') != 'unsupported')
    if active().get('address') != window['address']:
        notify('Focus changed; prompt saved locally. Nothing pasted or sent.')
        return
    # Re-copy to confirm the selection did not change during accessibility lookup.
    if copied_selection(window) != selected:
        notify('Selection changed; prompt saved locally. Nothing pasted or sent.')
        return
    run(['wl-copy', '--type', 'text/plain;charset=utf-8'], input=output.encode(),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(20):
        result = subprocess.run(['wl-paste', '--no-newline', '--type', 'text/plain'],
                                capture_output=True, timeout=2)
        if result.returncode == 0 and result.stdout == output.encode():
            break
        time.sleep(.025)
    else:
        raise RuntimeError('Clipboard verification failed. Nothing pasted or sent.')
    if editable and active().get('address') == window['address']:
        run(['wtype', '-M', 'ctrl', '-k', 'v', '-m', 'ctrl'])
        notify('Prompt inserted for review, including grill-me questions. Not sent. Ctrl+Z to undo.')
    else:
        notify('Prompt copied, including grill-me questions. Paste it into your AI chat with Ctrl+V.')


def main():
    runtime = Path(os.environ.get('XDG_RUNTIME_DIR', '/run/user/' + str(os.getuid())))
    with (runtime / 'mouse4-prompt.lock').open('w') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        try:
            handle()
        except Exception as error:
            import logging
            logging.exception('Mouse 4 prompt creation failed')
            notify('Prompt creation stopped; nothing sent. ' + str(error)[:160])


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Compose the installed Omarchy branding beneath multicolored digital rain."""
import datetime
import os
from pathlib import Path
import random
import signal
import sys
import time

PALETTE = ['ff3b30', 'ff9500', 'ffcc00', '34c759', '00c7be', '32ade6', '0a84ff', '5e5ce6', 'bf5af2', 'ff2d55']
COLORS = [tuple(bytes.fromhex(c)) for c in PALETTE]
SYMBOLS = '2598Z*):.\"=+-|_ｦｱｳｴｵｶｷｹｺｻｼｽｾｿﾀﾂﾃﾅﾆﾇﾈﾊﾋﾎﾏﾐﾑﾒﾓﾔﾕﾗﾘﾜ'
LOGO = (Path.home() / '.config/omarchy/branding/screensaver.txt').read_text().splitlines()
running = True

def stop(*_):
    global running
    running = False

signal.signal(signal.SIGTERM, stop)
signal.signal(signal.SIGINT, stop)

def draw(width, height, drops, now):
    cells = {}
    logo_width = max(map(len, LOGO), default=0)
    left, top = (width - logo_width) // 2, (height - 3 - len(LOGO)) // 2
    for y, line in enumerate(LOGO):
        for x, ch in enumerate(line):
            if ch != ' ' and 0 <= left+x < width and 0 <= top+y < height-3:
                cells[left+x, top+y] = (ch, (85, 115, 135))
    for drop in drops:
        x, head, length, color, speed = drop
        for age in range(length):
            y = int(head) - age
            if not 0 <= y < height-3:
                continue
            brightness = (1 - age / length) ** 1.5
            rgb = (255, 255, 255) if age == 0 else tuple(int(c * brightness) for c in color)
            # Preserve the wordmark silhouette while rain illuminates its letters.
            ch = cells[x, y][0] if (x, y) in cells else random.choice(SYMBOLS)
            cells[x, y] = (ch, rgb)
    for y, text in [(height-2, now.strftime('%A • %B %-d, %Y')), (height-1, now.strftime('%I:%M:%S %p').lstrip('0'))]:
        for x, ch in enumerate(text, max(0, (width-len(text))//2)):
            if x < width:
                cells[x, y] = (ch, (200, 235, 255))
    out = ['\033[H']
    for y in range(height):
        out.append(f'\033[{y+1};1H')
        last = None
        for x in range(width):
            ch, rgb = cells.get((x,y), (' ', (0,0,0)))
            if rgb != last:
                out.append('\033[38;2;%d;%d;%dm' % rgb)
                last = rgb
            out.append(ch)
    return ''.join(out)

def main():
    drops, size = [], None
    sys.stdout.write('\033[?25l\033[?7l\033[2J')
    try:
        while running:
            start = time.monotonic()
            current = os.get_terminal_size()
            width, height = current.columns, current.lines
            if current != size:
                drops, size = [], current
                sys.stdout.write('\033[2J')
            if random.random() < 0.8:
                drops.append([random.randrange(width), 0, random.randint(5, max(6, height//2)), random.choice(COLORS), random.uniform(.18,.65)])
            for d in drops:
                d[1] += d[4]
            drops = [d for d in drops if d[1]-d[2] < height-3]
            sys.stdout.write(draw(width, height, drops, datetime.datetime.now()))
            sys.stdout.flush()
            time.sleep(max(0, 1/30 - (time.monotonic()-start)))
    finally:
        sys.stdout.write('\033[0m\033[?7h\033[?25h')
        sys.stdout.flush()

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""Portable syntax and accidental-secret checks; never print matched secret values."""
from pathlib import Path
import ast,json,re,subprocess,tomllib
ROOT=Path(__file__).resolve().parents[1]
patterns=[r'gh[pousr]_[A-Za-z0-9]{25,}',r'github_pat_[A-Za-z0-9_]{30,}',r'sk-(?:proj-)?[A-Za-z0-9_-]{30,}',r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----',r'(?i)(?:password|api_key|client_secret)\s*[=:]\s*["\x27][A-Za-z0-9_+/-]{16,}["\x27]']
errors=[];count=0
for folder in ['home','profiles','scripts','tests','docs','extensions','vendor/voxtype-color-osd']:
 for p in (ROOT/folder).rglob('*'):
  if not p.is_file() or '__pycache__' in p.parts:continue
  try:s=p.read_text()
  except UnicodeDecodeError:continue
  count+=1
  if p.name!='check.py' and any(re.search(pattern,s) for pattern in patterns):errors.append(f'Possible secret: {p.relative_to(ROOT)}')
  try:
   if p.suffix=='.py' or s.startswith(('#!/usr/bin/python3', '#!/usr/bin/env python3')):ast.parse(s)
   if p.suffix=='.json':json.loads(s)
   if p.suffix=='.toml':tomllib.loads(s)
   if s.startswith(('#!/bin/bash','#!/bin/sh')):subprocess.run(['bash','-n',str(p)],check=True,capture_output=True)
  except (SyntaxError,ValueError,subprocess.CalledProcessError) as e:errors.append(f'Invalid syntax: {p.relative_to(ROOT)}: {e}')
for p in (ROOT/'home').rglob('*'):
 if p.is_file() and any(x in p.name.lower() for x in ['credentials','cookies','.env','private_key']):errors.append(f'Forbidden file: {p}')
# Public portability checks, separate from general upstream copyright notices.
for p in (ROOT/'home').rglob('*'):
 if not p.is_file() or '__pycache__' in p.parts:continue
 try:s=p.read_text()
 except UnicodeDecodeError:continue
 if re.search(r'/home/tbm|tbmpublicadjusters|tyler%40|192\.168\.|BEGIN .*PRIVATE KEY',s,re.I):errors.append(f'Private machine/account value in {p.relative_to(ROOT)}')
entries=json.loads((ROOT/'manifest.json').read_text())
if len({e['path'] for e in entries})!=len(entries):errors.append('Duplicate manifest path')
for e in entries:
 if not (ROOT/'home'/e['path']).is_file():errors.append('Missing manifest file: '+e['path'])
if errors:raise SystemExit('\n'.join(errors))
print(f'PASS: {count} text files checked for syntax and common secret patterns')

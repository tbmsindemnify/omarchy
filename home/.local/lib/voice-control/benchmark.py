import json,time
from actions import catalog
from semantic import interpret
cases=[
 ('Could you make this take up the entire screen for me?', 'fullscreen'),
 ('Move the highlighted files to Downloads.', 'file_transfer'),
 ('Can you copy the selected files into my Documents folder?', 'file_transfer'),
 ('Bring up my web browser please.', 'binding'),
 ('Can you make the sound a bit quieter?', 'binding'),
 ('Grab a picture of my screen.', 'binding'),
 ('Do not close this window.', 'clarify'),
 ('Move these somewhere better.', 'clarify'),
 ('Delete all the files on my computer.', 'clarify'),
 ('Print the document I am looking at.', 'keys'),
]
results=[]
d=catalog()
for text,expected in cases:
 start=time.monotonic()
 result=interpret(text,d,timeout=90)
 row={'phrase':text,'result':result,'seconds':round(time.monotonic()-start,2),'pass':result[0]==expected}
 print(json.dumps(row),flush=True)
 results.append(row)
from pathlib import Path
Path('@@HOME@@/.local/state/voice-control/benchmark.json').write_text(json.dumps(results,indent=2))
assert all(r['pass'] for r in results)

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'scripts/manage.py'
class InstallerTest(unittest.TestCase):
 def command(self,*args,ok=True):
  p=subprocess.run([sys.executable,str(SCRIPT),*map(str,args)],capture_output=True,text=True)
  if ok:self.assertEqual(p.returncode,0,p.stdout+p.stderr)
  else:self.assertNotEqual(p.returncode,0)
  return p
 def test_install_idempotence_and_restore(self):
  with tempfile.TemporaryDirectory(prefix='tbm-test-') as d:
   home=Path(d)/'home';home.mkdir()
   original=home/'.config/hypr/bindings.lua';original.parent.mkdir(parents=True);original.write_text('-- original\n')
   self.command('install','--home',home,'--monitors','eDP-1,DP-2')
   self.assertEqual(original.read_text(),'-- original\n')
   self.assertFalse((home/'.local').exists())
   self.command('install','--home',home,'--monitors','eDP-1,DP-2','--apply')
   backups=list((home/'.local/state/tbm-omarchy/backups').iterdir());self.assertEqual(len(backups),1)
   self.assertIn('"DP-2": 5',(home/'.config/omarchy/workspace-map.js').read_text())
   self.assertEqual(json.loads((home/'.config/omarchy/workspace-map.json').read_text()),{'eDP-1':0,'DP-2':5})
   self.assertIn('workspace = "10", monitor = "DP-2"',(home/'.config/hypr/tbm-machine.lua').read_text())
   self.assertNotIn('/home/tbm',(home/'.config/hypr/autostart.lua').read_text())
   self.assertIn(str(home),(home/'.config/hypr/autostart.lua').read_text())
   again=self.command('install','--home',home,'--monitors','eDP-1,DP-2','--apply');self.assertIn('Already up to date',again.stdout)
   original.write_text('-- new user edit\n')
   self.command('restore',backups[0],ok=False)
   self.assertEqual(original.read_text(),'-- new user edit\n')
   self.command('restore',backups[0],'--force')
   self.assertEqual(original.read_text(),'-- original\n')
   self.assertFalse((home/'.config/omarchy/shell.json').exists())
 def test_symlink_rejected_before_writes(self):
  with tempfile.TemporaryDirectory() as d:
   home=Path(d)/'home';home.mkdir();outside=Path(d)/'outside';outside.mkdir();(home/'.config').symlink_to(outside)
   self.command('install','--home',home,'--monitors','','--apply',ok=False)
   self.assertEqual(list(outside.iterdir()),[])
   self.assertFalse((home/'.local').exists())
 def test_invalid_monitor_and_missing_osd(self):
  with tempfile.TemporaryDirectory() as d:
   self.command('install','--home',d,'--monitors','DP-1,DP-1','--apply',ok=False)
   self.command('install','--home',d,'--monitors','DP-1"','--apply',ok=False)
   self.command('install','--home',d,'--with-osd','--apply',ok=False)
   self.assertEqual(list(Path(d).iterdir()),[])
 def test_capture_is_allowlisted_and_normalizes(self):
  # Copy the manager and manifest into a scratch repository so this test cannot edit source.
  import shutil
  with tempfile.TemporaryDirectory() as d:
   repo=Path(d)/'repo';shutil.copytree(ROOT/'scripts',repo/'scripts');shutil.copytree(ROOT/'home',repo/'home');shutil.copy2(ROOT/'manifest.json',repo/'manifest.json')
   home=Path(d)/'home';home.mkdir();(home/'.config').mkdir()
   source=home/'.config/foot/foot.ini';source.parent.mkdir();source.write_text('path='+str(home)+'\n')
   (home/'.config/credentials').write_text('do-not-copy')
   command=[sys.executable,str(repo/'scripts/manage.py'),'capture','--home',str(home)]
   before=(repo/'home/.config/foot/foot.ini').read_text()
   subprocess.run(command,check=True,capture_output=True)
   self.assertEqual(before,(repo/'home/.config/foot/foot.ini').read_text())
   subprocess.run(command+['--apply'],check=True,capture_output=True)
   self.assertEqual((repo/'home/.config/foot/foot.ini').read_text(),'path=@@HOME@@\n')
   self.assertFalse((repo/'home/.config/credentials').exists())
if __name__=='__main__':unittest.main()

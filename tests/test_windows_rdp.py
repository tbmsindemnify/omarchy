"""Exercise the portable wrapper without launching Windows or reading real secrets."""
import json
from pathlib import Path
import runpy
import tempfile
import unittest
from unittest.mock import patch, Mock

WRAPPER = Path(__file__).resolve().parents[1] / 'home/.config/windows/bin/xfreerdp3'

class WindowsRdpTests(unittest.TestCase):
    def test_mapped_monitor_and_credentials_through_stdin(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            (home / '.config/windows').mkdir(parents=True)
            (home / '.config/omarchy').mkdir()
            (home / '.config/windows/credentials').write_text('USERNAME=test-user\nPASSWORD=example-only\n')
            (home / '.config/omarchy/workspace-map.json').write_text('{"DP-2": 0}')
            monitors = [dict(name='DP-1', focused=True, width=1920, height=1080, scale=1),
                        dict(name='DP-2', width=3440, height=1440, scale=1, reserved=[68,0,0,0])]
            with patch('pathlib.Path.home', return_value=home), patch('sys.argv', [str(WRAPPER)]), \
                 patch('subprocess.check_output', return_value=json.dumps(monitors).encode()), \
                 patch('subprocess.run', return_value=Mock(returncode=0)) as run:
                with self.assertRaises(SystemExit) as result:
                    runpy.run_path(str(WRAPPER), run_name='__main__')
            self.assertEqual(result.exception.code, 0)
            self.assertEqual(run.call_args.args[0], ['/usr/bin/xfreerdp3', '/args-from:stdin'])
            args = run.call_args.kwargs['input'].splitlines()
            self.assertIn('/p:example-only', args)
            self.assertIn('/size:3372x1440', args)
            self.assertIn('-dynamic-resolution', args)
            self.assertIn('/gdi:sw', args)
            self.assertFalse(any(a.startswith(('/gfx:', '/floatbar')) for a in args))

    def test_stock_args_work_without_private_credentials(self):
        with tempfile.TemporaryDirectory() as directory, \
             patch('pathlib.Path.home', return_value=Path(directory)), \
             patch('sys.argv', [str(WRAPPER), '/v:localhost', '/floatbar', '/size:800x600', '+dynamic-resolution']), \
             patch('subprocess.check_output', return_value=b'[{"name":"eDP-1","width":2560,"height":1600,"scale":2,"focused":true}]'), \
             patch('subprocess.run', return_value=Mock(returncode=7)) as run:
            with self.assertRaises(SystemExit) as result:
                runpy.run_path(str(WRAPPER), run_name='__main__')
        self.assertEqual(result.exception.code, 7)
        args = run.call_args.kwargs['input'].splitlines()
        self.assertIn('/size:1280x800', args)
        self.assertNotIn('/floatbar', args)
        self.assertNotIn('/size:800x600', args)
        self.assertNotIn('+dynamic-resolution', args)

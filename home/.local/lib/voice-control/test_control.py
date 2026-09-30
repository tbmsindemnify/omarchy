import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import actions
import control
import focus

class Commands(unittest.TestCase):
    def setUp(self):
        # Fixture isolates unit tests from the active desktop. Live catalog testing is separate.
        fixture = Path(__file__).resolve().parents[4] / 'tests/voice-catalog.json'
        if fixture.exists():
            mock = patch.object(actions, 'catalog', return_value=json.loads(fixture.read_text()))
            mock.start()
            self.addCleanup(mock.stop)

    def test_every_catalog_entry(self):
        descriptions = actions.catalog()
        for description in descriptions:
            self.assertNotEqual(actions.resolve(description, descriptions)[0], 'unknown', description)
    def test_phrases(self):
        descriptions = actions.catalog()
        for phrase, expected in [('Make this window fullscreen.', ('binding','Full screen')), ('Please move window left.',('binding','Swap window to the left')), ('switch to workspace three',('binding','Switch to workspace 3')), ('print this document',('keys',['-M','ctrl','-k','p','-m','ctrl']))]:
            self.assertEqual(actions.resolve(phrase, descriptions), expected)
    def test_no_fuzzy_or_shell_execution(self):
        for phrase in ['I might want to close window later', 'please delete all my files', 'browser; rm -rf something']:
            self.assertEqual(actions.resolve(phrase, actions.catalog())[0], 'unknown')
        self.assertEqual(actions.resolve('create file named ../../bad',[])[0], 'invalid')
    def test_focus_changed_cancels(self):
        calls=[]
        def run(args):
            calls.append(args)
            return subprocess.CompletedProcess(args,0,json.dumps({'address':'different'}),'')
        notices=[]
        actions.dispatch('full screen','original',run,notices.append)
        self.assertEqual(len(calls),1)
        self.assertIn('cancelled',notices[0])
    def test_file_never_overwrites(self):
        with tempfile.TemporaryDirectory() as d, patch.object(actions.Path,'home',return_value=Path(d)):
            (Path(d)/'Documents').mkdir()
            run=lambda args: subprocess.CompletedProcess(args,0,json.dumps({'address':'same'}),'')
            notices=[]
            actions.dispatch('create file named sample.txt','same',run,notices.append)
            path=Path(d)/'Documents/Voice files/sample.txt'
            path.write_text('keep me')
            actions.dispatch('create file named sample.txt','same',run,notices.append)
            self.assertEqual(path.read_text(),'keep me')
            self.assertIn('already exists',notices[-1])
    def test_auto_routing(self):
        for focus_result, command_expected in [('text',False),('terminal',False),('unknown',False),('command',False)]:
            with tempfile.TemporaryDirectory() as d:
                calls=[]
                def run(args,**kwargs):
                    calls.append(args)
                    output='idle' if args==['voxtype','status'] else json.dumps({'address':'test'}) if args[:2]==['hyprctl','activewindow'] else ''
                    return subprocess.CompletedProcess(args,0,output,'')
                with patch.object(control,'RUNTIME',Path(d)), patch.object(control,'run',side_effect=run), patch.object(control,'notify'), patch.object(control,'focus_mode',return_value=focus_result):
                    control.main('auto')
                self.assertEqual(any(a[:3]==['voxtype','record','start'] for a in calls),True)
                self.assertNotIn(['voxtype','record','toggle'], calls)
                self.assertEqual(json.loads((Path(d)/'state.json').read_text())['mode'], 'command' if command_expected else 'dictate')
                if focus_result == 'unknown':
                    self.assertTrue(any(a[:3]==['voxtype','record','start'] for a in calls))
    def test_dictation_focus_rechecked_before_output(self):
        for detected in ['text', 'terminal', 'command', 'unknown']:
            with tempfile.TemporaryDirectory() as d:
                base=Path(d)
                transcript=base/'dictation.txt'
                transcript.write_text('spoken words\nsecond line')
                (base/'state.json').write_text(json.dumps({'file':str(transcript),'target':'test','mode':'dictate'}))
                calls=[]
                def run(args,**kwargs):
                    calls.append(args)
                    if args[0] == 'wl-paste':
                        return subprocess.CompletedProcess(args,0,'spoken words second line','')
                    window = {'address':'test', 'class': 'foot' if detected == 'terminal' else 'test-editor'}
                    return subprocess.CompletedProcess(args,0,json.dumps([window] if args[:2]==['hyprctl','clients'] else window),'')
                with patch.object(control,'RUNTIME',base),patch.object(control,'run',side_effect=run),patch.object(control,'notify'),patch.object(control,'focus_mode',return_value=detected):
                    control.main('auto')
                self.assertEqual(any(a[:2]==['hyprctl','eval'] and 'send_key_state' in a[2] for a in calls),True)
                if detected == 'terminal':
                    typing = next(a for a in calls if a[:2] == ['hyprctl','eval'])
                    self.assertIn('mods="CTRL SHIFT"', typing[2])
                    self.assertIn('state="up"', typing[2])
                    self.assertTrue(any(a[0]=='wl-copy' and a[-1]=='spoken words second line' for a in calls))
                self.assertFalse(any('Return' in a for a in calls))

    def test_bounce_click_keeps_recording(self):
        # A second button-5 event right after starting must not stop the recording.
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            state = base/'state.json'
            state.write_text(json.dumps({'file':str(base/'x.txt'),'target':'t','mode':'dictate','started':__import__('time').time()}))
            calls = []
            with patch.object(control,'RUNTIME',base),patch.object(control,'run',side_effect=lambda a,**k: calls.append(a)),patch.object(control,'notify'):
                control.main('dictate')
            self.assertTrue(state.exists())
            self.assertEqual(calls, [])

    def test_changed_window_refocuses_destination(self):
        # Focus-follows-mouse drift during transcription must not drop the paste.
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            transcript = base/'dictation.txt'
            transcript.write_text('Keep my speech')
            (base/'state.json').write_text(json.dumps({'file':str(transcript),'target':'original','mode':'dictate'}))
            calls = []
            def run(args, **kwargs):
                calls.append(args)
                if args[0] == 'wl-paste':
                    return subprocess.CompletedProcess(args, 0, 'Keep my speech', '')
                if args[:2] == ['hyprctl', 'clients']:
                    return subprocess.CompletedProcess(args, 0, json.dumps([{'address':'original','class':'com.anthropic.Claude'},{'address':'other','class':'foot','tags':['terminal*']}]), '')
                return subprocess.CompletedProcess(args, 0, json.dumps({'address':'original'}), '')
            with patch.object(control,'RUNTIME',base), patch.object(control,'run',side_effect=run), patch.object(control,'notify'):
                control.main('dictate')
            self.assertTrue(any(a[0]=='wl-copy' and a[-1]=='Keep my speech' for a in calls))
            paste = next(a for a in calls if a[:2]==['hyprctl','eval'])
            self.assertIn('address:original', paste[2])
            self.assertIn('mods="CTRL"', paste[2])
            self.assertEqual((base/'last-dictation.txt').read_text(), 'Keep my speech')

    def test_tagged_terminal_uses_terminal_paste(self):
        # org.omarchy.agent is foot running Claude Code; Ctrl+V there pastes nothing.
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            transcript = base/'dictation.txt'
            transcript.write_text('into the agent')
            (base/'state.json').write_text(json.dumps({'file':str(transcript),'target':'agent','mode':'dictate'}))
            calls = []
            def run(args, **kwargs):
                calls.append(args)
                if args[0] == 'wl-paste':
                    return subprocess.CompletedProcess(args, 0, 'into the agent', '')
                window = {'address':'agent','class':'org.omarchy.agent','tags':['default-opacity*','terminal*']}
                return subprocess.CompletedProcess(args, 0, json.dumps([window] if args[:2]==['hyprctl','clients'] else window), '')
            with patch.object(control,'RUNTIME',base), patch.object(control,'run',side_effect=run), patch.object(control,'notify'):
                control.main('dictate')
            paste = next(a for a in calls if a[:2]==['hyprctl','eval'])
            self.assertIn('mods="CTRL SHIFT"', paste[2])

    def test_dictation_uses_window_selected_at_stop(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            transcript = base/'dictation.txt'
            transcript.write_text('Put these words in the selected field')
            (base/'state.json').write_text(json.dumps({'file':str(transcript),'target':'start-window','mode':'dictate'}))
            calls = []
            def run(args, **kwargs):
                calls.append(args)
                window = {'address':'stop-window','class':'test-editor'}
                output = 'Put these words in the selected field' if args[0]=='wl-paste' else json.dumps([window] if args[:2]==['hyprctl','clients'] else window)
                return subprocess.CompletedProcess(args, 0, output, '')
            with patch.object(control,'RUNTIME',base), patch.object(control,'run',side_effect=run), patch.object(control,'notify'):
                control.main('dictate')
            paste = next(a for a in calls if a[:2]==['hyprctl','eval'])
            self.assertIn('address:stop-window', paste[2])
            self.assertFalse(any('Return' in a for a in calls))

    def test_terminal_focus_detection(self):
        for window_class in ['Alacritty', 'kitty', 'com.mitchellh.ghostty', 'foot']:
            with patch.object(focus.subprocess, 'check_output', return_value=json.dumps({'class':window_class})):
                self.assertEqual(focus.detect(), 'terminal')

    def test_command_finish_never_types(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d)
            transcript=base/'command.txt'
            transcript.write_text('full screen')
            (base/'state.json').write_text(json.dumps({'file':str(transcript),'target':'test'}))
            calls=[]
            def run(args,**kwargs):
                calls.append(args)
                return subprocess.CompletedProcess(args,0,'','')
            with patch.object(control,'RUNTIME',base),patch.object(control,'run',side_effect=run),patch.object(control,'notify'),patch.object(control,'execute') as execute:
                control.main('auto')
                execute.assert_called_once_with('full screen','test')
            self.assertTrue(all(a[:3]==['voxtype','record','stop'] for a in calls))
            self.assertFalse(transcript.exists())

if __name__=='__main__': unittest.main()

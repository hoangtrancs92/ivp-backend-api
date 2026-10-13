import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'steps'))
spec = importlib.util.spec_from_file_location('script_step', ROOT / 'steps/01_script.py')
step = importlib.util.module_from_spec(spec)
spec.loader.exec_module(step)


class ScriptRepairTests(unittest.TestCase):
    def test_missing_locations_are_repaired_without_rewriting_story(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'work') as directory:
            video = Path(directory)
            script = {'scenes': [{'id': 1, 'speaker': 'narrator', 'location': 'generic_studio',
                                  'characters': [], 'text': '比較しよう', 'layers': []}]}
            fixed = copy.deepcopy(script)
            fixed['new_locations'] = {'generic_studio': 'a quiet studio'}
            chars, locs = {'narrator': {}}, {}
            def register(candidate, characters, locations):
                locations.update(candidate.get('new_locations', {}))
                return []
            with patch.object(step, 'add_new', side_effect=register), patch.object(step, 'STYLE', 'classic'), \
                 patch.object(step, 'chat', return_value=json.dumps(fixed)) as chat:
                result = step.repair_candidate(script, video, chars, locs)
            self.assertEqual(result['scenes'][0]['text'], '比較しよう')
            self.assertEqual(result['scenes'][0]['location'], 'generic_studio')
            self.assertEqual(chat.call_count, 1)
            self.assertIn('generic_studio', chat.call_args.args[0])

    def test_persistent_error_preserves_candidate_and_diagnostics(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'work') as directory:
            video = Path(directory)
            script = {'scenes': []}
            with patch.object(step, 'chat', return_value='invalid JSON') as chat:
                with self.assertRaises(SystemExit):
                    step.repair_candidate(script, video, {}, {})
            self.assertEqual(chat.call_count, 2)
            self.assertTrue((video / 'work/script_errors.txt').is_file())
            self.assertEqual(json.loads((video / 'work/script_rejected.json').read_text(encoding='utf-8')), script)


if __name__ == '__main__':
    unittest.main()

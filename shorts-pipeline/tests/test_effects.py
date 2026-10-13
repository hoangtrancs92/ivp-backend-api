import copy
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "steps"), str(ROOT / "tools"), str(ROOT)]
import build_video as build
import effects
from common import asset_problems, normalize_script
from effect_rules import project_anchor, required_anchors, valid_anchor
from prepare_effects import prepare


class EffectTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "work").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / "work")
        self.addCleanup(self.temp.cleanup)
        self.video = Path(self.temp.name)
        (self.video / "full").mkdir()
        self.source = self.video / "full/001.png"
        Image.new("RGB", (576, 1024), "#887766").save(self.source)
        self.box = [.5, .6, .5, .65, .5, .35, .13]
        self.scene = {"id": 1, "full": True, "characters": ["mascot_jpn"], "location": "arena",
                      "layers": [{"effect": "shiver", "on": "mascot_jpn"}]}
        self.path = self.video / "script.json"
        self.path.write_text(json.dumps({"scenes": [self.scene]}), encoding="utf-8")

    def test_projection_matches_full_image_fit_and_shift(self):
        box = project_anchor(self.box, (576, 1024), (1080, 1920), 300)
        self.assertAlmostEqual(box[0], 540)
        self.assertAlmostEqual(box[1], .6 * 1920 + 300)
        self.assertAlmostEqual(box[5], .35 * 1920 + 300)
        self.assertAlmostEqual(box[6], .13 * 1080)
        crop = project_anchor(self.box, (1024, 1024), (1080, 1920), 300)
        self.assertAlmostEqual(crop[0], 540)

    def test_anchor_validation(self):
        self.assertTrue(valid_anchor(self.box))
        for value in (None, [0] * 7, [float('nan')] * 7, [2] * 7, [True] * 7):
            self.assertFalse(valid_anchor(value))

    def test_prepare_caches_and_rechecks_changed_source(self):
        calls = []
        def locate(scene, path, names):
            calls.append(names)
            return {name: self.box for name in names}
        self.assertTrue(prepare(self.video, locator=locate))
        self.assertFalse(prepare(self.video, locator=locate))
        Image.new("RGB", (576, 1024), "red").save(self.source)
        self.assertTrue(prepare(self.video, locator=locate))
        self.assertEqual(len(calls), 2)

    def test_prepare_rejects_unreliable_coordinates(self):
        with self.assertRaises(ValueError):
            prepare(self.video, locator=lambda scene, path, names: {names[0]: None}, strict=True)

    def test_unidentified_overlay_is_skipped_and_retried_after_image_change(self):
        self.assertTrue(prepare(self.video, locator=lambda *args: {'mascot_jpn': None}))
        stored = json.loads(self.path.read_text(encoding='utf-8'))['scenes'][0]
        self.assertEqual(stored['layers'], [])
        self.assertEqual(len(stored['effect_anchor_warning']['layers']), 1)
        self.assertFalse(prepare(self.video, locator=lambda *args: self.fail('cached failure was retried')))
        Image.new('RGB', (576, 1024), 'blue').save(self.source)
        self.assertTrue(prepare(self.video, locator=lambda *args: {'mascot_jpn': self.box}))
        stored = json.loads(self.path.read_text(encoding='utf-8'))['scenes'][0]
        self.assertEqual(stored['layers'][0]['effect'], 'shiver')
        self.assertNotIn('effect_anchor_warning', stored)

    def test_transient_bad_detection_is_retried(self):
        calls = []
        def locator(*args):
            calls.append(1)
            return {'mascot_jpn': None if len(calls) == 1 else self.box}
        self.assertTrue(prepare(self.video, locator=locator))
        self.assertEqual(len(calls), 2)
        self.assertNotIn('effect_anchor_warning', json.loads(self.path.read_text(encoding='utf-8'))['scenes'][0])

    def test_service_failure_does_not_remove_effects(self):
        from llm import LLMError
        def locator(*args):
            raise LLMError('service unavailable')
        with self.assertRaises(LLMError):
            prepare(self.video, locator=locator)
        self.assertEqual(json.loads(self.path.read_text(encoding='utf-8'))['scenes'][0]['layers'], self.scene['layers'])

    def test_global_effects_do_not_request_face_detection(self):
        self.scene['layers'] = [{'effect': 'gloom', 'on': 'mascot_jpn'}, {'effect': 'speed_lines'}]
        self.assertEqual(required_anchors(self.scene), [])

    def test_full_subject_effects_are_preserved_without_sticker_rebinding(self):
        self.scene['effect_anchors'] = {'mascot_jpn': self.box}
        self.scene['layers'] = [{'effect': k, 'on': 'mascot_jpn'}
                                for k in ('tears', 'sparkles', 'aura', 'rays', 'shiver', 'gloom')]
        self.scene['layers'].append({'id': 'tear', 'image': 'stickers/tear.png'})
        s = {'scenes': [self.scene]}
        build.repair(s)
        fx = [l for l in self.scene['layers'] if l.get('effect')]
        self.assertEqual(len(fx), 6)
        self.assertTrue(all(l.get('on') == 'mascot_jpn' for l in fx if l['effect'] != 'gloom'))
        self.assertNotIn('on', next(l for l in fx if l['effect'] == 'gloom'))

    def test_missing_full_anchors_are_not_silently_discarded(self):
        with self.assertRaises(ValueError):
            build.repair({'scenes': [self.scene]})

    def test_unpositioned_duplicate_sticker_does_not_cover_face(self):
        self.scene['effect_anchors'] = {'mascot_jpn': self.box}
        self.scene['layers'] = [{'effect': 'tears', 'on': 'mascot_jpn'},
                                {'image': 'stickers/tear.png'}]
        build.repair({'scenes': [self.scene]})
        self.assertEqual(len(self.scene['layers']), 1)
        self.assertEqual(self.scene['layers'][0]['effect'], 'tears')

    def test_shiver_is_rendered_and_unknown_effect_is_rejected_early(self):
        self.assertIn('shiver', effects.KINDS)
        image = Image.new('RGB', (200, 320), '#887766')
        before = image.copy()
        effects.draw(image, 'shiver', .7, 2, (100, 190, 90, 180, 100, 100, 28), image.size)
        self.assertNotEqual(image.tobytes(), before.tobytes())
        self.scene['layers'][0]['effect'] = 'unknown_effect'
        normalize_script({'scenes': [self.scene]}, self.video)
        self.assertTrue(any('unknown_effect' in e for e in asset_problems({'scenes': [self.scene]}, self.video)))

    def test_back_glow_does_not_cover_face(self):
        for kind in ('aura', 'rays'):
            image = Image.new('RGB', (200, 320), '#887766')
            effects.draw(image, kind, .8, 2, (100, 190, 90, 180, 100, 100, 28), image.size, occlude=True)
            self.assertEqual(image.getpixel((100, 100)), (136, 119, 102))

    def test_render_full_frame_with_anchor_and_shiver(self):
        self.scene['effect_anchors'] = {'mascot_jpn': self.box}
        previous = Path.cwd()
        try:
            os.chdir(self.video)
            items = build.load_layers(self.scene, None)
            self.assertIn('anchor_box', items[0])
            frame = build.render_frame(self.scene, build.background(self.scene), items, .6, 2)
            self.assertEqual(frame.size, (1080, 1920))
        finally:
            os.chdir(previous)


if __name__ == '__main__':
    unittest.main()

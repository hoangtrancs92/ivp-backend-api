"""Kiểm tra hợp đồng ảnh giữa viết kịch bản, sinh ảnh, duyệt và dựng. Không gọi mạng."""
import copy
import json
import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "steps"), str(ROOT / "tools"), str(ROOT / "skit"), str(ROOT)]
from common import (asset_problems, character_files, character_variants, image_requirements,
                    missing_script_images, normalize_script, review_items)
from assets import character_files as skit_files, missing_images as skit_missing, normalize_assets
from run_kaggle import ref_source
from run_local import missing_images as local_missing
from render_rules import MOTIONS, render_problems


def scene(**overrides):
    return {"id": 1, "characters": ["mascot_jpn"], "layers": [], "location": "arena",
            "action": "standing", "emotion": "normal", "shot": "full", **overrides}


class AssetTests(unittest.TestCase):
    def setUp(self):
        (ROOT / "work").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / "work")
        self.addCleanup(self.temp.cleanup)
        self.video = Path(self.temp.name)

    def touch(self, path):
        p = self.video / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.touch()
        return p

    def test_empty_characters_with_mascot_layers(self):
        sc = scene(characters=[], layers=[{"id": n, "image": f"cutouts/001_{n}.png"}
                                          for n in ("mascot_jpn", "mascot_chn")])
        s = {"scenes": [sc]}
        normalize_script(s, self.video)
        self.assertEqual(sc["characters"], ["mascot_jpn", "mascot_chn"])
        self.assertEqual(len(character_files(sc)), 2)
        self.assertFalse(asset_problems(s, self.video))

    def test_robot_added_without_reusing_mascot_image(self):
        sc = scene(layers=[{"id": "mascot_jpn", "image": "cutouts/001.png"},
                           {"id": "care_robot", "image": "cutouts/001_care_robot.png"}])
        normalize_script({"scenes": [sc]}, self.video)
        self.assertEqual(character_files(sc), [("mascot_jpn", "001.png"), ("care_robot", "001_care_robot.png")])

    def test_shortened_filename_and_grouped_layer(self):
        sc = scene(characters=["mascot_jpn", "mascot_chn"],
                   layers=[{"id": "mascot_jpn", "image": "cutouts/001_jpn.png"},
                           {"id": "mascot_chn", "image": "cutouts/001_chn.png"}])
        normalize_script({"scenes": [sc]}, self.video)
        self.assertEqual(sc["layers"][0]["image"], "cutouts/001_mascot_jpn.png")
        sc["layers"] = [{"image": "cutouts/001_mascot_jpn_mascot_chn.png", "anim": "bounce"}]
        normalize_script({"scenes": [sc]}, self.video)
        self.assertEqual(len(sc["layers"]), 2)
        self.assertTrue(all(l["anim"] == "bounce" for l in sc["layers"]))

    def test_missing_reused_filename_is_scheduled_as_declared(self):
        sc = scene(layers=[{"id": "mascot_jpn", "image": "cutouts/012.png"}])
        normalize_script({"scenes": [sc]}, self.video)
        self.assertEqual(sc["layers"][0]["image"], "cutouts/012.png")
        self.assertEqual(character_files(sc), [("mascot_jpn", "012.png")])

    def test_existing_reused_image_is_preserved(self):
        self.touch("cutouts/012.png")
        sc = scene(layers=[{"id": "mascot_jpn", "image": "cutouts/012.png"}])
        normalize_script({"scenes": [sc]}, self.video)
        self.assertEqual(sc["layers"][0]["image"], "cutouts/012.png")
        self.assertEqual(character_files(sc), [("mascot_jpn", "012.png")])

    def test_reused_cutout_is_generated_once_in_one_kaggle_batch(self):
        from make_jobs import main as make_jobs
        from run_kaggle import validate

        first = scene(location="generic_studio", layers=[{"id": "mascot_jpn", "image": "cutouts/001.png"}])
        second = scene(id=2, location="generic_studio", layers=[{"id": "mascot_jpn", "image": "cutouts/001.png"}])
        (self.video / "script.json").write_text(json.dumps({"scenes": [first, second]}), encoding="utf-8")
        with patch.object(sys, "argv", ["make_jobs.py", str(self.video)]):
            make_jobs()
        jobs = json.loads((self.video / "jobs.json").read_text(encoding="utf-8"))["jobs"]
        self.assertEqual([job["name"] for job in jobs].count("ch_001"), 1)
        validate(jobs, self.video)

    def test_unknown_layer_and_duplicate_files_are_errors(self):
        s = {"scenes": [scene(characters=[], layers=[{"id": "unknown", "image": "cutouts/001_unknown.png"}])]}
        normalize_script(s, self.video)
        self.assertTrue(asset_problems(s, self.video))
        sc = scene(characters=["mascot_jpn", "mascot_chn"],
                   layers=[{"id": n, "image": "cutouts/001.png"} for n in ("mascot_jpn", "mascot_chn")])
        self.assertTrue(any("chung" in p for p in asset_problems({"scenes": [sc]}, self.video)))

    def test_full_phone_and_explicit_cutout_override(self):
        scenes = [scene(), scene(id=2, full=False), scene(id=3, phone={"title": "hello"}),
                  scene(id=4, full_scene=True)]
        s = {"style": "new", "scenes": scenes}
        normalize_script(s, self.video)
        self.assertTrue(scenes[0]["full"])
        self.assertFalse(scenes[1]["full"])
        self.assertFalse(character_files(scenes[2]))
        self.assertTrue(scenes[3]["full"])
        self.assertEqual([p for _, sid, p, _ in image_requirements(s) if sid == 1], ["full/001.png"])
        self.assertFalse(asset_problems(s, self.video))

    def test_alt_pose_is_only_required_for_declared_character(self):
        sc = scene(characters=["mascot_jpn", "mascot_chn"], alt_pose={"mascot_jpn": "waving"})
        normalize_script({"scenes": [sc]}, self.video)
        self.assertEqual([f for _, f in character_variants(sc)],
                         ["001_mascot_jpn.png", "001_mascot_jpn_alt.png", "001_mascot_chn.png"])

    def test_cutout_only_is_reviewed_and_used_as_reference(self):
        self.touch("backgrounds/arena.png")
        path = self.touch("cutouts/001.png")
        s = {"scenes": [scene()]}
        normalize_script(s, self.video)
        self.assertFalse(missing_script_images(self.video, s))
        self.assertEqual(review_items(self.video, s)[0]["path"], path)
        self.assertEqual(ref_source(self.video, "char__001.png"), path)

    def test_normalization_is_idempotent_and_local_agrees(self):
        s = {"scenes": [scene(layers=[{"id": "mascot_jpn", "src": "cutouts/001_jpn.png"}])]}
        normalize_script(s, self.video)
        before = copy.deepcopy(s)
        self.assertFalse(normalize_script(s, self.video))
        self.assertEqual(before, s)
        (self.video / "script.json").write_text(json.dumps(s), encoding="utf-8")
        self.assertEqual(local_missing(self.video), missing_script_images(self.video, s))

    def test_make_jobs_creates_both_mascots_and_robot_with_cutout_alt(self):
        loc = next(iter(json.loads((ROOT / "config/locations.json").read_text(encoding="utf-8"))))
        self.touch(f"backgrounds/{loc}.png")
        self.touch("cutouts/002.png")
        s = {"scenes": [scene(characters=[], location=loc,
                             layers=[{"id": n, "image": f"cutouts/001_{n}.png"}
                                     for n in ("mascot_jpn", "mascot_chn")]),
                        scene(id=2, location=loc, alt_pose={"mascot_jpn": "waving"},
                              layers=[{"id": "mascot_jpn", "image": "cutouts/002.png"},
                                      {"id": "care_robot", "image": "cutouts/002_care_robot.png"}])]}
        (self.video / "script.json").write_text(json.dumps(s), encoding="utf-8")
        result = subprocess.run([sys.executable, "-X", "utf8", str(ROOT / "tools/make_jobs.py"), str(self.video)],
                                capture_output=True, text=True, encoding="utf-8", cwd=ROOT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        jobs = json.loads((self.video / "jobs.json").read_text(encoding="utf-8"))["jobs"]
        names = {j["name"] for j in jobs if j["name"].startswith("ch_")}
        self.assertEqual(names, {"ch_001_mascot_jpn", "ch_001_mascot_chn", "ch_002_care_robot", "ch_002_alt"})
        alt = next(j for j in jobs if j["name"] == "ch_002_alt")
        self.assertEqual(alt["refs"], ["char__002.png"])
        self.assertTrue(ref_source(self.video, alt["refs"][0]).is_file())

    def skit(self):
        return {"cast": {"sk_actor": {"look": "young man", "pose": "standing", "expressions": ["normal"],
                                       "poses": {"wave": "waving"}}},
                "lines": [{"speaker": "sk_actor", "expression": {"sk_actor": "happy"}}]}

    def test_skit_line_expression_drives_image_plan(self):
        s = self.skit()
        changes, errors = normalize_assets(s)
        self.assertTrue(changes)
        self.assertFalse(errors)
        self.assertIn("sk_actor_happy_talk.png", list(skit_files(s)))
        self.assertIn("sk_actor_pose_wave_talk.png", list(skit_files(s)))
        self.assertFalse(normalize_assets(s)[0])

    def test_skit_checks_all_variants_inserts_and_scenes(self):
        s = self.skit()
        normalize_assets(s)
        for f in skit_files(s):
            self.touch(f"characters/{f}")
        self.assertFalse(skit_missing(self.video, s))
        (self.video / "characters/sk_actor_happy_talk.png").unlink()
        s["inserts"] = {"example": "absent_insert"}
        s["scenes"] = {"absent_scene": {"image": "absent_scene"}}
        with patch("assets.ROOT", self.video):
            missing = skit_missing(self.video, s)
        self.assertEqual(missing, ["backgrounds/absent_insert.png", "backgrounds/absent_scene.png",
                                   "characters/sk_actor_happy_talk.png"])
        self.assertTrue(any(p.startswith("cutouts/") for p in skit_missing(self.video, s, cutouts=True)))

    def test_skit_invalid_pose_stops_before_generation(self):
        s = self.skit()
        s["lines"][0]["pose"] = {"sk_actor": "unknown"}
        self.assertTrue(normalize_assets(s)[1])

    def test_subject_motion_moves_to_layer_anim(self):
        sc = scene(motion="breathe")
        normalize_script({"scenes": [sc]}, self.video)
        self.assertNotIn("motion", sc)
        self.assertEqual(sc["layers"][0]["anim"], "breathe")

    def test_all_logged_motions_are_supported_on_full_scenes(self):
        invalid = ['breathe', 'exit_right', 'sink', 'tilt', 'slide_right', 'rise', 'sway', 'approach', 'recede']
        s = {"scenes": [scene(id=i, full=True, motion=m) for i, m in enumerate(invalid, 1)]}
        normalize_script(s, self.video)
        self.assertTrue(all(sc['motion'] in MOTIONS for sc in s['scenes']))
        self.assertFalse(render_problems(s))
        self.assertFalse(normalize_script(s, self.video))

    def test_unknown_motion_and_transition_fail_before_generation(self):
        s = {"scenes": [scene(motion="unknown_camera", transition="unknown_transition")]}
        normalize_script(s, self.video)
        errors = asset_problems(s, self.video)
        self.assertTrue(any('unknown_camera' in e for e in errors))
        self.assertTrue(any('unknown_transition' in e for e in errors))

    def test_camera_motion_in_anim_moves_to_scene(self):
        sc = scene(layers=[{'id': 'mascot_jpn', 'image': 'cutouts/001.png', 'anim': 'zoom_in'}])
        normalize_script({'scenes': [sc]}, self.video)
        self.assertEqual(sc['motion'], 'zoom_in')
        self.assertNotIn('anim', sc['layers'][0])

    def test_known_legacy_animation_aliases(self):
        sc = scene(layers=[{'id': 'mascot_jpn', 'image': 'cutouts/001.png', 'anim': 'dash_in_right'}])
        normalize_script({'scenes': [sc]}, self.video)
        self.assertEqual(sc['layers'][0]['anim'], 'slide_right')

    def test_mismatched_character_image_is_rejected(self):
        s = {"scenes": [scene(layers=[{"id": "mascot_jpn", "image": "cutouts/001_mascot_chn.png"}])]}
        normalize_script(s, self.video)
        self.assertTrue(any("đang dùng ảnh" in p for p in asset_problems(s, self.video)))

    def test_object_layer_is_generated_from_object_description(self):
        sc = scene(characters=[], object="a red letter", layers=[])
        normalize_script({"scenes": [sc]}, self.video)
        self.assertEqual(sc["layers"], [{"id": "object", "image": "cutouts/001.png"}])
        self.assertEqual(character_files(sc), [(None, "001.png")])

    def test_new_object_does_not_take_another_characters_reused_file(self):
        first = scene(layers=[{"id": "mascot_jpn", "image": "cutouts/002.png"}])
        obj = scene(id=2, characters=[], object="a red letter", layers=[])
        s = {"scenes": [first, obj]}
        normalize_script(s, self.video)
        self.assertEqual(character_files(obj), [(None, "002_object.png")])
        self.assertFalse(asset_problems(s, self.video))
        before = copy.deepcopy(s)
        normalize_script(s, self.video)
        self.assertEqual(s, before)

    def test_static_overlay_without_source_is_rejected_early(self):
        s = {"scenes": [scene(layers=[{"image": "props/absent.png"}])]}
        normalize_script(s, self.video)
        self.assertTrue(any("props/absent.png" in p for p in asset_problems(s, self.video)))

    def test_skit_job_variants_match_the_shared_plan(self):
        spec = importlib.util.spec_from_file_location("skit_jobs", ROOT / "skit/jobs.py")
        jobs_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(jobs_module)
        s = self.skit()
        s["sets"] = {"main": "a plain room"}
        (self.video / "skit.json").write_text(json.dumps(s), encoding="utf-8")
        with patch.object(jobs_module, "REFS", self.video / "refs"), \
                patch.object(jobs_module, "MAKE_SCENES", False), \
                patch.object(sys, "argv", ["jobs.py", str(self.video)]), patch("builtins.print"):
            jobs_module.main()
        saved = json.loads((self.video / "skit.json").read_text(encoding="utf-8"))
        jobs = json.loads((self.video / "jobs.json").read_text(encoding="utf-8"))["jobs"]
        self.assertEqual({j["name"][3:] + ".png" for j in jobs if j["name"].startswith("ch_")},
                         set(skit_files(saved)))


if __name__ == "__main__":
    unittest.main()

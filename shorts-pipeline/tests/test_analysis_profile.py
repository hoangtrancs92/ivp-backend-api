"""Kiểm tra video phân tích giữ hình dễ đọc và không ảnh hưởng tiểu phẩm."""
import copy
import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import analysis_profile
import build_video
import variety


class AnalysisTests(unittest.TestCase):
    def script(self):
        return {"story_mode": "kaigai", "scenes": [{"id": 1, "beat": "hook", "text": "比較！",
                "speaker": "mascot_jpn", "characters": ["mascot_jpn", "mascot_chn"],
                "emotion": "proud", "punchline": True, "alt_pose": "waving", "motion": "shake",
                "sfx": ["wrong", "fanfare"], "layers": [
                    {"id": "mascot_chn", "image": "cutouts/001_mascot_chn.png", "anim": "jump"},
                    {"id": "mascot_jpn", "image": "cutouts/001_mascot_jpn.png", "anim": "spin_in"},
                    {"effect": "speed_lines"}, {"word": "ドヤッ"}, {"image": "stickers/spark.png"}]}]}

    def test_one_host_without_reaction_stack(self):
        script = variety.fill(self.script())
        scene = script["scenes"][0]
        self.assertEqual([l["id"] for l in scene["layers"]], ["mascot_jpn"])
        self.assertEqual(scene["layers"][0]["anim"], "none")
        self.assertEqual(scene["transition"], "cut")
        self.assertNotIn("alt_pose", scene)
        self.assertEqual(build_video.sfx_events(scene, False), [])
        again = copy.deepcopy(script)
        self.assertEqual(variety.fill(again), script)

    def test_card_gets_full_attention(self):
        script = self.script()
        script["scenes"][0]["compare"] = {"japan": "A", "other": "B", "winner": "other", "score": [0, 1]}
        scene = variety.fill(script)["scenes"][0]
        self.assertEqual(scene["layers"], [])
        self.assertEqual(scene["motion"], "none")
        self.assertEqual(scene["compare"]["style"], "analysis")
        self.assertEqual(build_video.sfx_events(scene, False), [])

    def test_non_analysis_profile_unchanged(self):
        script = self.script()
        script["story_mode"] = "comedy"
        old = copy.deepcopy(script)
        self.assertEqual(analysis_profile.apply(script), old)
        self.assertIs(analysis_profile.video_options(script, build_video.VIDEO), build_video.VIDEO)

    def test_missing_stock_photo_keeps_host_visible(self):
        script = self.script()
        script["scenes"][0]["photo"] = {"query": "train"}
        with patch.object(Path, "is_file", return_value=False):
            scene = variety.fill(script)["scenes"][0]
        self.assertEqual([l["id"] for l in scene["layers"]], ["mascot_jpn"])

    def test_analysis_subtitles_fit_compact_header(self):
        script = self.script()
        script.update(title=["日本と中国", "比較する視点"], speakers={"mascot_jpn": "#E53935"})
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "subs.ass"
            build_video.write_subtitles(script, [(0, 4)], 4, path)
            text = path.read_text(encoding="utf-8")
            self.assertIn("Style: mascot_jpn,Arial,76,", text)
            self.assertIn(",70,70,260", text)

    def test_script_duration_depends_on_mode(self):
        for mode, expected in (("kaigai", (110, 130)), ("comedy", (68, 86))):
            with patch.dict(os.environ, SHORTS_STORY_MODE=mode, SHORTS_STYLE="classic"):
                spec = importlib.util.spec_from_file_location("script_length_test", ROOT / "steps/01_script.py")
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                self.assertEqual((module.MIN_SECONDS, module.MAX_SECONDS), expected)
                if mode == "kaigai":
                    self.assertIn("110–130", module.LONGER)
                    self.assertEqual(module.fit(module.length({"scenes": [{"text": "あ" * 23}] * 30})), 0)


if __name__ == "__main__":
    unittest.main()

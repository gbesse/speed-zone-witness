import json
from pathlib import Path
import unittest

from speed_zone_witness import audit


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def events(name):
    return [json.loads(line) for line in (FIXTURES / name).read_text().splitlines()]


class SpeedZoneTests(unittest.TestCase):
    def setUp(self):
        self.config = json.loads((FIXTURES / "config.json").read_text())

    def test_safe_lookahead_in_three_languages(self):
        for locale in ("fr", "en", "es"):
            report = audit(events("safe.jsonl"), self.config, locale)
            self.assertEqual(report["status"], "pass")
            self.assertEqual(report["samples"][0]["zones"], ["slow-a"])

    def test_stale_path_falls_back_to_pose(self):
        report = audit(events("stale.jsonl"), self.config)
        self.assertEqual(report["status"], "fail")
        self.assertFalse(report["samples"][0]["path_fresh"])
        self.assertIn("missing_limit", [item["code"] for item in report["findings"]])

    def test_reverse_reprojects_path(self):
        report = audit(events("reverse.jsonl"), self.config)
        self.assertEqual(report["status"], "fail")
        self.assertTrue(report["samples"][1]["path_rewound"])
        self.assertEqual(report["samples"][1]["expected_limit_mps"], 0.2)

    def test_no_zone_exposure_is_inconclusive(self):
        trace = [{"kind": "sample", "at_ms": 0, "x": 10, "y": 10, "applied_limit_mps": None, "velocity_mps": 0.0}]
        self.assertEqual(audit(trace, self.config)["status"], "inconclusive")

    def test_distant_path_is_ignored(self):
        trace = [{"kind": "path", "at_ms": 0, "points": [[0, 0], [10, 0]]}, {"kind": "sample", "at_ms": 100, "x": 0, "y": 2, "applied_limit_mps": None, "velocity_mps": 0.1}]
        self.assertEqual(audit(trace, self.config)["status"], "inconclusive")


if __name__ == "__main__":
    unittest.main()

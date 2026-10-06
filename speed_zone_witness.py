"""Replay speed-zone expectations against observed limits and velocity."""

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys


MESSAGES = {
    "fr": {"missing_limit": "Limite absente ou trop élevée à {at_ms} ms", "overspeed": "Vitesse mesurée au-dessus de la limite à {at_ms} ms", "no_exposure": "Aucune exposition à une zone dans la trace", "input": "Entrée invalide", "summary": "{samples} mesure(s), {exposures} exposition(s), {failures} échec(s)"},
    "en": {"missing_limit": "Missing or excessive limit at {at_ms} ms", "overspeed": "Measured speed above limit at {at_ms} ms", "no_exposure": "No speed-zone exposure in trace", "input": "Invalid input", "summary": "{samples} sample(s), {exposures} exposure(s), {failures} failure(s)"},
    "es": {"missing_limit": "Límite ausente o demasiado alto a los {at_ms} ms", "overspeed": "Velocidad medida superior al límite a los {at_ms} ms", "no_exposure": "No hay exposición a zonas en el registro", "input": "Entrada no válida", "summary": "{samples} medición(es), {exposures} exposición(es), {failures} fallo(s)"},
}


def _finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def validate(events, config):
    if not isinstance(config, dict) or set(config) != {"zones", "path_ttl_ms", "lookahead_m", "max_path_distance_m", "tolerance_mps"}:
        raise ValueError("config")
    for field in ("path_ttl_ms", "lookahead_m", "max_path_distance_m", "tolerance_mps"):
        if not _finite(config[field]) or config[field] < 0:
            raise ValueError(field)
    if not isinstance(config["zones"], list) or not config["zones"]:
        raise ValueError("zones")
    ids = set()
    for zone in config["zones"]:
        if not isinstance(zone, dict) or set(zone) != {"id", "rect", "limit_mps"} or not isinstance(zone["id"], str) or not zone["id"] or zone["id"] in ids:
            raise ValueError("zone")
        ids.add(zone["id"])
        rect = zone["rect"]
        if not isinstance(rect, list) or len(rect) != 4 or not all(_finite(value) for value in rect) or rect[0] >= rect[2] or rect[1] >= rect[3] or not _finite(zone["limit_mps"]) or zone["limit_mps"] <= 0:
            raise ValueError("zone rect/limit")
    if not isinstance(events, list) or not events:
        raise ValueError("events")
    previous = -1
    samples = 0
    for line, event in enumerate(events, 1):
        if not isinstance(event, dict) or event.get("kind") not in ("path", "sample") or not isinstance(event.get("at_ms"), int) or isinstance(event["at_ms"], bool) or event["at_ms"] < 0 or event["at_ms"] < previous:
            raise ValueError(f"line {line}: event/at_ms")
        previous = event["at_ms"]
        if event["kind"] == "path":
            points = event.get("points")
            if not isinstance(points, list) or len(points) < 2 or any(not isinstance(point, list) or len(point) != 2 or not all(_finite(value) for value in point) for point in points):
                raise ValueError(f"line {line}: points")
            if all(a == b for a, b in zip(points, points[1:])):
                raise ValueError(f"line {line}: zero-length path")
        else:
            samples += 1
            if not _finite(event.get("x")) or not _finite(event.get("y")):
                raise ValueError(f"line {line}: pose")
            for field in ("applied_limit_mps", "velocity_mps"):
                value = event.get(field)
                if value is not None and (not _finite(value) or value < 0):
                    raise ValueError(f"line {line}: {field}")
    if not samples:
        raise ValueError("no samples")


def _inside(point, rect):
    return rect[0] <= point[0] <= rect[2] and rect[1] <= point[1] <= rect[3]


def _hits_rect(a, b, rect):
    """Liang-Barsky clipping: intersection of segment and axis-aligned box."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    lo, hi = 0.0, 1.0
    for p, q in ((-dx, a[0] - rect[0]), (dx, rect[2] - a[0]), (-dy, a[1] - rect[1]), (dy, rect[3] - a[1])):
        if p == 0:
            if q < 0:
                return False
        else:
            t = q / p
            if p < 0:
                lo = max(lo, t)
            else:
                hi = min(hi, t)
            if lo > hi:
                return False
    return True


def _project(point, path):
    best_distance = math.inf
    best_s = 0.0
    traveled = 0.0
    for a, b in zip(path, path[1:]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        length2 = dx * dx + dy * dy
        if length2 == 0:
            continue
        t = max(0.0, min(1.0, ((point[0] - a[0]) * dx + (point[1] - a[1]) * dy) / length2))
        closest = (a[0] + t * dx, a[1] + t * dy)
        distance = math.dist(point, closest)
        length = math.sqrt(length2)
        if distance < best_distance:
            best_distance = distance
            best_s = traveled + t * length
        traveled += length
    return best_s, best_distance


def _lookahead_hits(path, start_s, distance, rect):
    end_s = start_s + distance
    traveled = 0.0
    for a, b in zip(path, path[1:]):
        length = math.dist(a, b)
        if length == 0:
            continue
        left = max(start_s, traveled)
        right = min(end_s, traveled + length)
        if right >= left:
            u, v = (left - traveled) / length, (right - traveled) / length
            first = (a[0] + u * (b[0] - a[0]), a[1] + u * (b[1] - a[1]))
            last = (a[0] + v * (b[0] - a[0]), a[1] + v * (b[1] - a[1]))
            if _hits_rect(first, last, rect):
                return True
        traveled += length
    return False


def audit(events, config, locale="en"):
    if locale not in MESSAGES:
        raise ValueError("locale")
    validate(events, config)
    active_path = None
    path_at = None
    previous_s = None
    findings = []
    samples = []
    for event in events:
        if event["kind"] == "path":
            active_path = event["points"]
            path_at = event["at_ms"]
            previous_s = None
            continue
        point = (event["x"], event["y"])
        age = event["at_ms"] - path_at if path_at is not None else None
        age_fresh = active_path is not None and age <= config["path_ttl_ms"]
        s, distance = _project(point, active_path) if age_fresh else (None, None)
        path_fresh = age_fresh and distance <= config["max_path_distance_m"]
        if not path_fresh:
            s = None
        rewound = previous_s is not None and s is not None and s + 0.01 < previous_s
        if s is not None:
            previous_s = s
        active_zones = [zone for zone in config["zones"] if _inside(point, zone["rect"]) or (path_fresh and _lookahead_hits(active_path, s, config["lookahead_m"], zone["rect"]))]
        expected = min((zone["limit_mps"] for zone in active_zones), default=None)
        local = []
        if expected is not None:
            applied = event.get("applied_limit_mps")
            if applied is None or applied > expected + config["tolerance_mps"]:
                local.append({"code": "missing_limit", "at_ms": event["at_ms"], "message": MESSAGES[locale]["missing_limit"].format(at_ms=event["at_ms"])})
            velocity = event.get("velocity_mps")
            if velocity is not None and velocity > expected + config["tolerance_mps"]:
                local.append({"code": "overspeed", "at_ms": event["at_ms"], "message": MESSAGES[locale]["overspeed"].format(at_ms=event["at_ms"])})
        samples.append({"at_ms": event["at_ms"], "path_age_ms": age, "path_fresh": path_fresh, "path_distance_m": distance, "path_rewound": rewound, "zones": [zone["id"] for zone in active_zones], "expected_limit_mps": expected, "applied_limit_mps": event.get("applied_limit_mps"), "velocity_mps": event.get("velocity_mps"), "findings": local})
        findings.extend(local)
    exposures = sum(sample["expected_limit_mps"] is not None for sample in samples)
    if exposures == 0:
        findings.append({"code": "no_exposure", "message": MESSAGES[locale]["no_exposure"]})
    return {"format": "speed-zone-witness/v1", "locale": locale, "status": "fail" if any(item["code"] != "no_exposure" for item in findings) else "inconclusive" if not exposures else "pass", "summary": MESSAGES[locale]["summary"].format(samples=len(samples), exposures=exposures, failures=sum(item["code"] != "no_exposure" for item in findings)), "samples": samples, "findings": findings}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Audit speed zones / Auditer les zones de vitesse / Auditar zonas de velocidad")
    parser.add_argument("trace")
    parser.add_argument("config")
    parser.add_argument("--locale", choices=MESSAGES, default="en")
    parser.add_argument("--output")
    args = parser.parse_args(argv)
    try:
        raw = Path(args.trace).read_bytes()
        report = audit([json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()], json.loads(Path(args.config).read_text(encoding="utf-8")), args.locale)
        report["source"] = {"path": args.trace, "sha256": hashlib.sha256(raw).hexdigest()}
    except (OSError, UnicodeError, ValueError, TypeError, KeyError) as exc:
        print(f"{MESSAGES[args.locale]['input']}: {exc if args.locale == 'en' else type(exc).__name__}", file=sys.stderr)
        return 2
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return {"pass": 0, "fail": 1, "inconclusive": 3}[report["status"]]


if __name__ == "__main__":
    raise SystemExit(main())

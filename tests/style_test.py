from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from subterra.config import RenderConfig
from subterra.filters import FILTER_NAMES, apply_filter
from subterra.narrative import ARCHETYPES
from subterra.renderer import FilmRenderer

ROOT = Path(__file__).resolve().parents[1]
TMP = ROOT / "tests" / "_tmp"
features = TMP / "test_project" / "features.npz"
if not features.exists():
    raise SystemExit("Execute smoke_test.py primeiro.")

sample = np.random.default_rng(1).integers(0, 256, (180, 320, 3), dtype=np.uint8)
for name in FILTER_NAMES:
    out = apply_filter(sample, name, 0.8, np.random.default_rng(2))
    assert out.shape == sample.shape and out.dtype == np.uint8, name

for i, name in enumerate(ARCHETYPES):
    story = {
        "captions": [],
        "scenes": [{
            "scene": 0, "start": 0.0, "end": 3.0, "role": "development",
            "archetype": name, "alt_archetype": name, "camera_mode": "locked",
            "glitch_density": 0.5, "media_mix": 0.5, "palette_shift": 0.0,
            "filter": "none", "transition": "cut", "shot_seconds": 1.0,
            "typography_mode": "none", "graphic_symbol": "timecode",
        }],
    }
    story_path = TMP / "story_one.json"
    story_path.write_text(json.dumps(story), encoding="utf-8")
    renderer = FilmRenderer(
        RenderConfig(640, 360, fps=12, seed=10+i, render_scale=0.5, filter_name="none"),
        features, story_path, [],
    )
    frame = renderer.frame(0.5)
    renderer.close()
    assert frame.shape == (360, 640, 3), (name, frame.shape)

print(f"OK: {len(FILTER_NAMES)} filtros e {len(ARCHETYPES)} arquétipos")

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from .filters import AUTO_FILTER_POOL


ARCHETYPES = [
    "industrial_tunnel", "vector_field", "particle_ritual", "pixel_corruption",
    "halftone_signal", "machine_vision", "liquid_feedback",
    "powerline_dream", "wireframe_cathedral", "media_collage",
    "kinetic_typography", "crt_archive", "datamosh_blocks",
    "rave_documentary", "signal_city", "monolith_scan", "waveform_sculpture",
]

STYLE_CHOICES = ["auto", "reference_collage", "pure_procedural", "media_driven", *ARCHETYPES]

ROLE_POOLS = {
    "intro": ["powerline_dream", "crt_archive", "monolith_scan", "machine_vision"],
    "breakdown": ["kinetic_typography", "halftone_signal", "liquid_feedback", "wireframe_cathedral", "crt_archive"],
    "buildup": ["powerline_dream", "signal_city", "vector_field", "waveform_sculpture"],
    "drop": ["media_collage", "datamosh_blocks", "industrial_tunnel", "rave_documentary"],
    "climax": ["media_collage", "rave_documentary", "particle_ritual", "datamosh_blocks", "industrial_tunnel"],
    "outro": ["powerline_dream", "monolith_scan", "kinetic_typography", "liquid_feedback"],
    "development": ARCHETYPES,
}

REFERENCE_POOL = [
    "powerline_dream", "media_collage", "kinetic_typography", "crt_archive",
    "rave_documentary", "datamosh_blocks", "wireframe_cathedral", "machine_vision",
]
PURE_POOL = [
    "industrial_tunnel", "vector_field", "particle_ritual", "liquid_feedback",
    "wireframe_cathedral", "signal_city", "monolith_scan", "waveform_sculpture",
]
MEDIA_POOL = [
    "media_collage", "rave_documentary", "pixel_corruption", "halftone_signal",
    "machine_vision", "crt_archive", "datamosh_blocks",
]


def _choose_archetype(rng: np.random.Generator, style: str, role: str) -> str:
    if style in ARCHETYPES:
        return style
    if style == "reference_collage":
        pool = REFERENCE_POOL
    elif style == "pure_procedural":
        pool = PURE_POOL
    elif style == "media_driven":
        pool = MEDIA_POOL
    else:
        pool = ROLE_POOLS.get(role, ARCHETYPES)
    return str(rng.choice(pool))


def build_story(
    analysis_json: str | Path,
    seed: int,
    output_path: str | Path,
    style: str = "auto",
    filter_name: str = "auto",
    captions: list[dict[str, Any]] | None = None,
    edit_density: float = 0.65,
) -> dict[str, Any]:
    data = json.loads(Path(analysis_json).read_text(encoding="utf-8"))
    rng = np.random.default_rng(seed)
    sections = data["sections"]
    scenes: list[dict[str, Any]] = []
    last_archetype = ""
    bpm = max(60.0, float(data.get("estimated_bpm") or 120.0))
    beat_seconds = 60.0 / bpm
    edit_density = float(np.clip(edit_density, 0.0, 1.0))

    for i, section in enumerate(sections):
        role = section.get("role", "development")
        archetype = _choose_archetype(rng, style, role)
        # Avoid long repetitive sequences in automatic modes.
        for _ in range(5):
            if archetype != last_archetype or style in ARCHETYPES:
                break
            archetype = _choose_archetype(rng, style, role)
        last_archetype = archetype
        alt_pool = [a for a in ROLE_POOLS.get(role, ARCHETYPES) if a != archetype]
        alt_archetype = str(rng.choice(alt_pool or ARCHETYPES))

        if role in {"climax", "drop"}:
            beat_division = float(rng.choice([0.5, 1.0, 2.0], p=[0.25, 0.55, 0.20]))
        elif role == "breakdown":
            beat_division = float(rng.choice([4.0, 8.0, 12.0]))
        else:
            beat_division = float(rng.choice([2.0, 4.0, 8.0]))
        shot_seconds = max(0.18, beat_seconds * beat_division * (1.35 - edit_density * 0.7))

        scene_filter = filter_name if filter_name != "auto" else str(rng.choice(AUTO_FILTER_POOL))
        scenes.append({
            "scene": i,
            "start": section["start"],
            "end": section["end"],
            "role": role,
            "archetype": archetype,
            "alt_archetype": alt_archetype,
            "camera_mode": str(rng.choice(["push", "orbit", "handheld", "locked", "reverse", "roll", "crash_zoom"])),
            "glitch_density": round(float(rng.uniform(0.12, 0.88)), 3),
            "media_mix": round(float(rng.uniform(0.20, 0.82)), 3),
            "palette_shift": round(float(rng.uniform(-1.0, 1.0)), 3),
            "filter": scene_filter,
            "transition": str(rng.choice(["cut", "flash", "wipe", "pixel", "luma", "feedback"])),
            "shot_seconds": round(shot_seconds, 4),
            "typography_mode": str(rng.choice(["none", "subtitle", "huge", "fragment", "terminal"], p=[0.16, 0.30, 0.22, 0.20, 0.12])),
            "graphic_symbol": str(rng.choice(["pylon", "cursor", "window", "barcode", "crosshair", "grid", "timecode"])),
        })

    story = {
        "version": "0.2.0",
        "seed": int(seed),
        "title": "SUBTERRA procedural film",
        "audio": data["source"],
        "duration_seconds": data["duration_seconds"],
        "bpm": data["estimated_bpm"],
        "key": data["estimated_key"],
        "mood": data["mood_tags"],
        "style_mode": style,
        "edit_density": edit_density,
        "visual_language": [
            "techno underground", "industrial", "cybernetic decay",
            "brutalist typography", "procedural motion", "media collage",
            "power infrastructure", "CRT archive", "rave documentary",
        ],
        "captions": captions or [],
        "scenes": scenes,
    }
    Path(output_path).write_text(json.dumps(story, ensure_ascii=False, indent=2), encoding="utf-8")
    return story

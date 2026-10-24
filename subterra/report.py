from __future__ import annotations

import html
import json
from pathlib import Path


def write_html_report(analysis_path: str|Path,story_path: str|Path,output_path: str|Path) -> None:
    analysis=json.loads(Path(analysis_path).read_text(encoding="utf-8"))
    story=json.loads(Path(story_path).read_text(encoding="utf-8"))
    rows="".join(
        f"<tr><td>{s['index']}</td><td>{s['start']:.2f}</td><td>{s['end']:.2f}</td><td>{html.escape(s['role'])}</td><td>{s['energy']:.2f}</td><td>{s.get('bass',0):.2f}</td></tr>"
        for s in analysis["sections"])
    scenes="".join(
        f"<tr><td>{s['scene']}</td><td>{s['start']:.2f}</td><td>{s['end']:.2f}</td><td>{html.escape(s['archetype'])}</td><td>{html.escape(s.get('alt_archetype',''))}</td><td>{html.escape(s['camera_mode'])}</td><td>{html.escape(s.get('filter',''))}</td><td>{html.escape(s.get('transition',''))}</td></tr>"
        for s in story["scenes"])
    content=f"""<!doctype html><html lang='pt-BR'><head><meta charset='utf-8'><title>SUBTERRA 0.2 report</title>
<style>body{{font-family:Arial,sans-serif;background:#0b0b0d;color:#e8e8ea;max-width:1250px;margin:40px auto;padding:0 20px}}table{{border-collapse:collapse;width:100%;margin-bottom:32px;font-size:14px}}td,th{{border:1px solid #333;padding:8px;text-align:left}}code{{color:#b8ffdf}}.tag{{display:inline-block;background:#222;padding:5px 8px;margin:3px;border-radius:4px}}</style></head><body>
<h1>SUBTERRA 0.2 — relatório do filme</h1><p><b>Áudio:</b> <code>{html.escape(analysis['source'])}</code></p>
<p><b>Duração:</b> {analysis['duration_seconds']:.2f}s · <b>BPM:</b> {analysis['estimated_bpm']:.2f} · <b>Tom:</b> {html.escape(analysis['estimated_key'])} · <b>Seed:</b> {story['seed']}</p>
<p>{''.join(f"<span class='tag'>{html.escape(t)}</span>" for t in analysis['mood_tags'])}</p>
<p><b>Modo visual:</b> {html.escape(story.get('style_mode','auto'))} · <b>Densidade de montagem:</b> {story.get('edit_density',0):.2f} · <b>Legendas:</b> {len(story.get('captions',[]))}</p>
<h2>Estrutura musical</h2><table><tr><th>#</th><th>Início</th><th>Fim</th><th>Função</th><th>Energia</th><th>Bass</th></tr>{rows}</table>
<h2>Plano visual</h2><table><tr><th>#</th><th>Início</th><th>Fim</th><th>Arquétipo</th><th>Alternativo</th><th>Câmera</th><th>Filtro</th><th>Transição</th></tr>{scenes}</table>
</body></html>"""
    Path(output_path).write_text(content,encoding="utf-8")

from __future__ import annotations

import argparse
import json
import random
import sys
from dataclasses import asdict
from pathlib import Path

from subterra.audio_analysis import analyze_audio
from subterra.config import RESOLUTION_PRESETS, RenderConfig
from subterra.filters import FILTER_NAMES
from subterra.hardware import diagnose, save_report
from subterra.lyrics import captions_to_json, load_captions
from subterra.narrative import STYLE_CHOICES, build_story
from subterra.renderer import render_film, resolve_encoder
from subterra.report import write_html_report


def positive_int(value: str) -> int:
    n = int(value)
    if n <= 0:
        raise argparse.ArgumentTypeError("deve ser maior que zero")
    return n


def unit_float(value: str) -> float:
    n=float(value)
    if not 0 <= n <= 1:
        raise argparse.ArgumentTypeError("deve estar entre 0 e 1")
    return n


def resolve_resolution(args: argparse.Namespace) -> tuple[int, int]:
    if bool(args.width) != bool(args.height):
        raise ValueError("Para resolução personalizada, informe --width e --height juntos.")
    if args.width and args.height:
        width,height=args.width,args.height
    else:
        width,height=RESOLUTION_PRESETS[args.resolution]
    if width < 320 or height < 180:
        raise ValueError("A resolução mínima é 320x180.")
    # H.264/yuv420p requires even dimensions. Keep the user's value whenever possible.
    width -= width % 2; height -= height % 2
    return width,height


def cmd_diagnose(args: argparse.Namespace) -> int:
    report=diagnose(args.path); save_report(report,args.output)
    print(json.dumps(asdict(report),ensure_ascii=False,indent=2))
    print(f"\nRelatório salvo em: {Path(args.output).resolve()}")
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    summary,json_path,npz_path=analyze_audio(args.audio,args.workdir)
    print(json.dumps(asdict(summary),ensure_ascii=False,indent=2))
    print(f"\nAnálise: {json_path.resolve()}\nFeatures: {npz_path.resolve()}")
    return 0


def cmd_render(args: argparse.Namespace) -> int:
    audio=Path(args.audio)
    if not audio.exists(): raise FileNotFoundError(f"Áudio não encontrado: {audio}")
    output=Path(args.output)
    workdir=Path(args.workdir or output.parent/f"{output.stem}_project")
    workdir.mkdir(parents=True,exist_ok=True)
    seed=args.seed if args.seed is not None else random.SystemRandom().randint(1,2_147_483_647)
    width,height=resolve_resolution(args)

    print("[1/5] Analisando áudio e estrutura...")
    summary,analysis_path,features_path=analyze_audio(audio,workdir)
    duration=min(summary.duration_seconds,args.preview_seconds) if args.preview_seconds else summary.duration_seconds

    print("[2/5] Carregando letra/legenda local...")
    captions=load_captions(args.lyrics,duration) if args.lyrics else []
    if captions:
        (workdir/"captions.json").write_text(json.dumps(captions_to_json(captions),ensure_ascii=False,indent=2),encoding="utf-8")
        print(f"  {len(captions)} segmentos de texto carregados.")
    else:
        print("  Sem arquivo de letra; será usada tipografia procedural.")

    print("[3/5] Criando narrativa, montagem e pós-produção...")
    story_path=workdir/"story.json"
    build_story(
        analysis_path,seed,story_path,args.style,args.filter,
        captions=captions_to_json(captions),edit_density=args.edit_density,
    )
    write_html_report(analysis_path,story_path,workdir/"report.html")

    cfg=RenderConfig(
        width=width,height=height,fps=args.fps,seed=seed,style=args.style,
        quality=args.quality,render_scale=args.render_scale,strobe=args.strobe,
        audio_mode=args.audio_mode,encoder=args.encoder,crf=args.crf,preset=args.ffmpeg_preset,
        filter_name=args.filter,filter_intensity=args.filter_intensity,edit_density=args.edit_density,
        typography=not args.no_typography,safe_flashes=not args.unsafe_flashes,
    )
    (workdir/"render_config.json").write_text(json.dumps(asdict(cfg),ensure_ascii=False,indent=2),encoding="utf-8")

    encoder=resolve_encoder(cfg.encoder,output)
    print(f"[4/5] Renderizando {width}x{height} @ {args.fps:g} fps | seed={seed} | encoder={encoder}")
    last_pct=-1
    def progress(done: int,total: int) -> None:
        nonlocal last_pct
        pct=int(done*100/total)
        if pct!=last_pct:
            print(f"  {pct:3d}% ({done}/{total} frames)",flush=True); last_pct=pct

    render_film(audio,output,features_path,story_path,cfg,duration,args.media,progress)
    print("[5/5] Finalizado.")
    print(f"Vídeo: {output.resolve()}\nProjeto: {workdir.resolve()}\nSeed: {seed}")
    return 0


def make_parser() -> argparse.ArgumentParser:
    parser=argparse.ArgumentParser(description="SUBTERRA 0.2 — transforma música em filme techno underground localmente.")
    sub=parser.add_subparsers(dest="command",required=True)

    p_diag=sub.add_parser("diagnose",help="Analisa hardware, FFmpeg e espaço em disco.")
    p_diag.add_argument("--path",default=".",help="Disco/pasta de destino para checar espaço livre.")
    p_diag.add_argument("--output",default="hardware_report.json"); p_diag.set_defaults(func=cmd_diagnose)

    p_an=sub.add_parser("analyze",help="Analisa profundamente um arquivo de áudio.")
    p_an.add_argument("audio"); p_an.add_argument("--workdir",default="analysis_output"); p_an.set_defaults(func=cmd_analyze)

    p=sub.add_parser("render",help="Analisa o áudio, cria narrativa e exporta o filme.")
    p.add_argument("audio",help="Arquivo de áudio: WAV, FLAC, MP3, M4A etc.")
    p.add_argument("output",help="Saída .mp4, .mkv ou .avi")
    p.add_argument("--media",action="append",default=[],help="Imagem/vídeo base. Pode ser repetido.")
    p.add_argument("--lyrics",help="Letra/legenda local: SRT, VTT, LRC ou TXT.")
    p.add_argument("--resolution",choices=sorted(RESOLUTION_PRESETS),default="1080p")
    p.add_argument("--width",type=positive_int,help="Largura livre, por exemplo 1400.")
    p.add_argument("--height",type=positive_int,help="Altura livre, por exemplo 2200.")
    p.add_argument("--fps",type=float,default=30.0)
    p.add_argument("--seed",type=int)
    p.add_argument("--style",choices=STYLE_CHOICES,default="auto")
    p.add_argument("--filter",choices=FILTER_NAMES,default="auto",help="Filtro autoral de pós-produção.")
    p.add_argument("--filter-intensity",type=unit_float,default=.72)
    p.add_argument("--edit-density",type=unit_float,default=.65,help="0 = planos longos; 1 = montagem muito rápida.")
    p.add_argument("--quality",choices=["draft","high"],default="high")
    p.add_argument("--render-scale",type=float,default=.75,help="0.35 a 1.0 reduz custo interno e mantém resolução final.")
    p.add_argument("--strobe",type=unit_float,default=.15,help="0 desativa flashes. O modo seguro limita a intensidade.")
    p.add_argument("--unsafe-flashes",action="store_true",help="Eleva o limite de flashes; use com cautela.")
    p.add_argument("--no-typography",action="store_true")
    p.add_argument("--audio-mode",choices=["preserve","normalize","streaming","cinema","club"],default="preserve")
    p.add_argument("--encoder",default="auto",choices=["auto","libx264","libx265","h264_nvenc","hevc_nvenc","h264_amf","hevc_amf","h264_qsv","hevc_qsv"])
    p.add_argument("--crf",type=int,default=18)
    p.add_argument("--ffmpeg-preset",default="medium")
    p.add_argument("--preview-seconds",type=float,help="Renderiza apenas os primeiros N segundos.")
    p.add_argument("--workdir")
    p.set_defaults(func=cmd_render)
    return parser


def main() -> int:
    parser=make_parser(); args=parser.parse_args()
    try: return int(args.func(args))
    except KeyboardInterrupt:
        print("\nCancelado pelo usuário.",file=sys.stderr); return 130
    except Exception as exc:
        print(f"ERRO: {exc}",file=sys.stderr); return 1


if __name__=="__main__":
    raise SystemExit(main())

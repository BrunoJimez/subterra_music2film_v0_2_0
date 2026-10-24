# Perfil de render — RTX 4060 8 GB / 16 GB RAM

Baseado no relatório fornecido:

- Windows 10;
- CPU AMD de 6 núcleos / 12 threads;
- 15,87 GB de RAM;
- NVIDIA GeForce RTX 4060 com 8 GB de VRAM;
- FFmpeg e FFprobe disponíveis;
- 88,63 GB livres.

## Presets práticos

| Uso | Resolução | FPS | Escala interna | Encoder |
|---|---:|---:|---:|---|
| Prévia rápida | 1280×720 | 30 | 0.50 | h264_nvenc |
| Filme final padrão | 1920×1080 | 30 | 0.75–0.85 | h264_nvenc |
| Reel/TikTok | 1080×1920 | 30 | 0.65–0.75 | h264_nvenc |
| 2K | 2560×1440 | 24/30 | 0.65–0.75 | h264/hevc_nvenc |
| 4K | 3840×2160 | 24/30 | 0.50 | hevc_nvenc |

## Limitações prováveis

- OpenCV calcula grande parte do frame na CPU; NVENC acelera principalmente a compressão final.
- 16 GB de RAM são suficientes, mas não ideais para múltiplos vídeos 4K base.
- 88,63 GB livres permitem testes, mas é recomendável manter 30 GB livres durante renders longos.
- Filtros com bloom, colagem, datamosh e mídia 4K aumentam o custo.

## Ordem recomendada

1. prévia de 15 s em 720p/0.50;
2. filme inteiro em 720p se a narrativa precisar ser avaliada;
3. render final em 1080p/0.75;
4. 2K ou 4K apenas depois de aprovar seed, montagem, filtro e mídias.

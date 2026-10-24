# SUBTERRA — Music-to-Film Engine v0.2.0

Programa local, gratuito e sem API paga para transformar uma música em um filme procedural com estética **Techno Underground**.

A Fase 0.2 foi construída depois da análise integral do vídeo de referência e do primeiro filme produzido pela versão 0.1. A principal mudança é conceitual: o sistema deixou de tratar cada seção musical como um único visualizador contínuo e passou a operar como um **motor de direção, montagem e pós-produção**.

## Novidades da Fase 0.2

- resolução digitável: largura e altura livres na interface;
- 17 arquétipos visuais, contra 7 na versão anterior;
- modo `reference_collage`, baseado na gramática do vídeo estudado;
- microplanos e alternância de linguagens dentro de cada seção musical;
- tipografia cinética, frases procedurais e legendas sincronizadas;
- importação de SRT, VTT, LRC e TXT;
- 46 filtros autorais de imagem e vídeo;
- transições por flash, wipe, pixelização, luma e feedback;
- novas bandas de análise: sub, bass, low-mid, mid, presence e air;
- detecção estrutural relativa: intro, buildup, breakdown, drop, climax, development e outro;
- encoder `auto`, com prioridade para NVENC em computadores NVIDIA compatíveis;
- modos de áudio `preserve`, `streaming`, `cinema`, `club` e `normalize`;
- formatos verticais, quadrados, cinema, ultrawide e qualquer dimensão personalizada;
- limite seguro de flashes ativado por padrão.

## Arquétipos visuais

### Originais preservados

- `industrial_tunnel`
- `vector_field`
- `particle_ritual`
- `pixel_corruption`
- `halftone_signal`
- `machine_vision`
- `liquid_feedback`

### Novos

- `powerline_dream`: torres, cabos, horizonte e infraestrutura elétrica;
- `wireframe_cathedral`: arquitetura de linhas e perspectiva;
- `media_collage`: painéis, janelas e fragmentos de mídia;
- `kinetic_typography`: palavras como objetos visuais;
- `crt_archive`: monitor, scanlines e memória de vídeo;
- `datamosh_blocks`: deslocamento de blocos e canais;
- `rave_documentary`: câmera de mão, smear e documentação de festival;
- `signal_city`: cidade, grid, circuitos e feixe de varredura;
- `monolith_scan`: escultura minimalista e scanner;
- `waveform_sculpture`: geometria radial controlada por bandas sonoras.

## Modos gerais de direção

- `reference_collage`: torre/cabos, tipografia, CRT, colagem, rave e corrupção digital;
- `pure_procedural`: evita depender de filmagem base;
- `media_driven`: prioriza imagens e vídeos anexados;
- `auto`: escolhe entre todas as linguagens conforme a função musical;
- qualquer arquétipo individual: fixa uma linguagem durante todo o filme.

## Filtros

Os filtros são equivalentes autorais de famílias encontradas em editores sociais e ferramentas cinematográficas. Não são cópias exatas de LUTs proprietárias.

Categorias disponíveis:

- limpos e vibrantes;
- retrato suave, pastel, paisagem e comida;
- cinema teal-orange, night, bleach, green e anamorphic;
- vintage 70s, 90s, Polaroid, Super 8, VHS e filme desbotado;
- noir, matte B&W, high-key, silver screen e cyanotype;
- acid green, cyber magenta, vaporwave, infrared, thermal e night vision;
- industrial rust, concrete, digital decay, cobalt, pink signal;
- dream haze, golden hour, winter, emerald, comic, posterize e pixel LUT.

A lista completa aparece no menu da interface e em `subterra/filters.py`.

## Instalação no Windows

Pré-requisitos:

- Windows 10 ou 11;
- Python 3.11 ou 3.12;
- FFmpeg e FFprobe no `PATH`;
- 8 GB de RAM no mínimo; 16 GB recomendados.

Passos:

1. Execute `INSTALAR_WINDOWS.bat`.
2. Execute `DIAGNOSTICO_WINDOWS.bat`.
3. Abra `ABRIR_SUBTERRA.bat`.
4. Selecione áudio, saída e mídias opcionais.
5. Na aba **Exportação**, escolha um preset ou digite largura e altura.
6. Faça primeiro uma **Prévia de 15 s**.
7. Depois execute o filme completo.

## Perfil recomendado para RTX 4060 8 GB + 16 GB RAM

- prévia: 1280×720, 30 fps, escala interna 0.50;
- filme 1080p: 1920×1080, escala 0.75 ou 0.85, `h264_nvenc`/`auto`;
- vertical: 1080×1920, escala 0.65 ou 0.75;
- 2K: escala 0.65 a 0.75;
- 4K: escala 0.50, 24 ou 30 fps, preferencialmente `hevc_nvenc`;
- 60 fps: usar apenas depois de validar em 30 fps.

NVENC acelera a codificação, mas as imagens procedurais ainda são calculadas por CPU/OpenCV. Portanto, dobrar resolução ou FPS aumenta substancialmente o tempo de render.

## Linha de comando

Render 1080p com direção inspirada na referência:

```powershell
.venv\Scripts\python.exe subterra.py render "musica.wav" "output\filme.mp4" `
  --resolution 1080p `
  --style reference_collage `
  --filter auto `
  --render-scale 0.75 `
  --encoder auto
```

Resolução completamente personalizada:

```powershell
.venv\Scripts\python.exe subterra.py render "musica.wav" "output\custom.mp4" `
  --width 1400 --height 2200 `
  --style auto
```

Com letra sincronizada e mídias base:

```powershell
.venv\Scripts\python.exe subterra.py render "musica.flac" "output\filme.mkv" `
  --width 1080 --height 1920 `
  --lyrics "letra.lrc" `
  --media "foto.png" `
  --media "filmagem.mp4" `
  --style media_driven `
  --filter cinematic_teal_orange
```

Prévia rápida:

```powershell
.venv\Scripts\python.exe subterra.py render "musica.wav" "output\preview.mp4" `
  --width 1280 --height 720 `
  --preview-seconds 15 `
  --render-scale 0.5
```

## Letras e transcrição local

A Fase 0.2 aceita arquivos prontos:

- `.srt` e `.vtt`: timestamps completos;
- `.lrc`: letras sincronizadas por linha;
- `.txt`: linhas distribuídas ao longo da duração.

A transcrição automática por Whisper local ainda não instala modelos pesados automaticamente. Essa integração será opcional em uma fase posterior para não obrigar downloads de vários gigabytes nem inviabilizar computadores menores.

## Áudio final

- `preserve`: não aplica processamento tonal ou dinâmico; exporta AAC em alta qualidade;
- `streaming`/`normalize`: loudness em torno de -14 LUFS;
- `cinema`: -16 LUFS, true peak mais conservador e corte de extremos inaudíveis;
- `club`: master mais intenso, com limiter e loudness mais elevado.

Processamento automático não substitui mixagem e masterização feitas por engenheiro. O modo padrão continua sendo `preserve`.

## Segurança de flashes

O limite seguro está ativado por padrão. Mesmo assim, filmes techno podem conter contraste rápido, glitch e flashes. Revise o resultado antes de publicação e inclua aviso quando necessário.

## Testes

```powershell
.venv\Scripts\python.exe tests\smoke_test.py
.venv\Scripts\python.exe tests\style_test.py
```

## Documentos incluídos

- `REFERENCE_ANALYSIS.md`: decupagem e comparação com a versão 0.1;
- `CHANGELOG.md`: alterações técnicas;
- `HARDWARE_RTX4060.md`: recomendações para o hardware analisado.

## Licença

Código sob licença MIT. Mídias, músicas, fontes, modelos e assets adicionados pelo usuário permanecem sujeitos às respectivas licenças e direitos autorais.

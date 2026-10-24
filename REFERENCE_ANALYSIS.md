# Análise técnica do vídeo de referência — Fase 0.2

Arquivo analisado integralmente: `Ninajirachi.mp4` (219,32 s, 1920×1080, 30 fps, H.264 + AAC).

## Conclusão principal

O vídeo não é um “audio visualizer” contínuo. Ele funciona como um **filme musical híbrido**, construído pela alternância de cinco regimes:

1. objetos e colagens 3D em fundo neutro;
2. infraestrutura elétrica real ou reconstruída (torres, cabos, linhas);
3. tipografia cinética que ocupa o espaço como objeto;
4. corrupção digital, janelas, interfaces, CRT e fragmentação de mídia;
5. documentação de rave/festival e um epílogo documental.

A torre de transmissão é o **motivo semântico recorrente**. Ela retorna em vídeo real, geometria 3D, desenho vetorial, tela CRT e composição gráfica. Isso dá unidade narrativa mesmo quando o estilo muda radicalmente.

## Decupagem aproximada

### 00:00–00:15 — prólogo de objetos e memória digital

- fundo branco ou vazio escuro;
- aglomeração de janelas, pequenos objetos, imagens e fragmentos 3D;
- um dispositivo/monitor isolado no espaço;
- montagem curta e enigmática, ainda sem estabelecer um mundo realista.

### 00:15–01:05 — torre, paisagem e letra espacial

- filmagem real de torre de energia, árvores, céu e terreno;
- rotação agressiva do horizonte e câmera orientada pelo eixo da torre;
- palavras grandes atravessam o quadro, deformam-se em perspectiva e integram-se à estrutura metálica;
- o fundo muda para azul elétrico;
- janelas, painéis e fragmentos de interface explodem radialmente ao redor da torre.

### 01:05–01:45 — aceleração, túnel e cidade corrompida

- sensação de deslocamento veloz e zoom radial;
- paisagem urbana e arquitetura tratadas por smear, pixel sorting e datamosh;
- passagem do colorido ao quase monocromático;
- palavras permanecem legíveis mesmo quando o ambiente se desintegra;
- retorno breve à torre em paisagem escura, estabilizando o motivo central.

### 01:45–02:10 — arquivo, diagrama e CRT

- colagens de interfaces em fundo claro;
- visual minimalista rosa com torres e cabos desenhados em linha branca;
- composição quase diagramática, contrastando com o caos anterior;
- tela CRT azul com janelas empilhadas e objetos gráficos.

### 02:10–03:00 — clímax documental de rave

- filmagem de festival, público, palco, fogo, LEDs, equipamentos e monitores;
- câmera de mão, motion blur e mudança frequente de enquadramento;
- letra exibida em caixas semelhantes a diálogos de sistema operacional antigo;
- o símbolo gráfico do monitor aparece fisicamente no evento, conectando o mundo digital ao real;
- o maior conteúdo humano e emocional é reservado para esta parte.

### 03:00–03:20 — colapso e montagem de memória

- imagens ao vivo muito desfocadas;
- retorno a colagens densas, janelas e fragmentos em fundo preto;
- uma interface com texto manuscrito funciona como pico expressivo;
- as camadas anteriores parecem condensadas em um arquivo final.

### 03:20–03:34 — síntese vetorial

- torres de energia minimalistas em rosa e azul;
- cabos convergem para pontos de fuga;
- fragmentos tipográficos reaparecem em grande escala;
- linguagem reduzida aos seus elementos essenciais: torre, linha, cor e palavra.

### 03:34–fim — epílogo humano

- imagem documental estável de duas pessoas diante do mar;
- subtítulo convencional, sem caixa digital;
- redução abrupta do ruído visual;
- encerramento narrativo que transforma a abstração anterior em lembrança humana.

## Gramática visual identificada

- **Motivo recorrente:** torre/linha de transmissão.
- **Tipografia:** objeto espacial, não simples legenda.
- **Paletas estruturais:** azul elétrico, rosa, preto/branco e cores documentais.
- **Montagem:** microcortes rápidos nos picos; planos maiores em diagramas e epílogo.
- **Transições:** flash, smear, pixel sorting, fragmentação, mudança de suporte e luma.
- **Mídia:** alternância entre filmagem real, 2D, 3D, CRT, interfaces e colagem.
- **Narrativa:** prólogo digital → infraestrutura → colapso urbano → arquivo → rave → memória → epílogo.
- **Glitch:** empregado como pontuação e transformação, não como textura constante.

## Comparação quantitativa com o teste da versão 0.1

Amostragem a 2 quadros por segundo:

| Métrica | Referência | SUBTERRA 0.1 |
|---|---:|---:|
| Brilho médio | 0,363 | 0,122 |
| Contraste médio | 0,224 | 0,092 |
| Saturação média | 0,447 | 0,354 |
| Densidade de bordas | 0,159 | 0,051 |
| Diferença temporal média | 0,262 | 0,061 |
| Quadros muito escuros | 3,2% | 56,4% |
| Mudanças fortes (`diff > 0,25`) | 183 | 4 |

A versão 0.1 acertou a estética procedural e a sincronização básica, mas apresentou três lacunas claras:

1. permaneceu escura por tempo demais;
2. usou uma linguagem visual por seção, com pouca montagem interna;
3. não possuía âncoras semânticas, tipografia narrativa nem alternância entre suportes.

## Decisões implementadas na Fase 0.2

- microplanos dentro de cada seção musical;
- arquétipo principal e alternativo por cena;
- motivo visual de torres e cabos (`powerline_dream`);
- tipografia cinética e legendas em caixas de interface;
- colagem de mídia, CRT, câmera rave e datamosh em blocos;
- transições por flash, wipe, pixelização, luma e feedback;
- filtros autorais de pós-produção;
- aumento da variação de brilho, contraste, cor e densidade espacial;
- modo `reference_collage`, inspirado na gramática da referência sem copiar seus frames, assets ou identidade visual.

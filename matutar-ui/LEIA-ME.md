# Matutar UI v1.0.0

Base visual compartilhada da Matutar Games. A fonte de verdade é esta pasta, no repositório `matutar-games`.
Cada jogo guarda uma **cópia** da pasta (`matutar-ui/`), para não haver dependência entre sites: se a home cair, os jogos continuam funcionando.

## Arquivos
| Arquivo | Para quê |
|---|---|
| `matutar-ui.css` | Fontes, tokens `--mt-*`, cabeçalho `.mt-barra`, botões `.mt-btn`, foco e aviso de saída. Tudo com prefixo `mt-`. |
| `matutar-ui.js` | Link "Todos os jogos" (`a[data-mt-home]`) e aviso antes de sair de uma partida. |
| `ponte-matutar-base.css` | Para jogos feitos sobre a base antiga (Confia?, Qual o Preço?): troca só os valores dos tokens antigos pelos `--mt-*`. Reverter = tirar o `<link>`. |
| `fontes/` | Bricolage Grotesque 700/800, Work Sans 400/600, Roboto Mono 500/700 (licenças junto). |

## Tokens
- **Superfícies:** `--mt-fundo` #FBF6EC · `--mt-superficie` #FFFDF8 · `--mt-superficie-2` #F2EBDD
- **Texto e linha:** `--mt-tinta` #1E1B2E · `--mt-tinta-2` #3C384D
- **Jogos e casa:** `--mt-duelo` #A9C0DC · `--mt-preco` #FFE48A · `--mt-confia` #C3B4F2 · `--mt-novidade` #C5E6CD · `--mt-coral` #F2AE98 (cada um com versão `-claro`)
- **Estados:** sucesso #2F6B45 sobre #DDF0E2 · erro #A33A2A sobre #FBE3DA · atenção #7A5300 sobre #FFF3C4 · foco #2C4F9E
- **Forma:** traço 2px grafite, sombra dura 4px (2px na pequena), raio 18px (12px pequeno), pílula para botões
- **Espaço:** escala de 4 (`--mt-e1` 4px a `--mt-e6` 28px); toque mínimo 44px; gutter lateral 16px com área segura

Regra de cor: as cores pastel são **fundo**. Texto sobre elas é sempre `--mt-tinta` (8:1 ou mais). Texto colorido só com os tons de estado.

## Tipografia
- **Bricolage Grotesque** 800: marca, títulos, nomes dos jogos.
- **Work Sans** 400/600: leitura e botões. Corpo de 16 a 17px.
- **Roboto Mono** 500/700: rótulos, números, dados secundários. Mínimo 13px.
- Cada jogo pode manter **uma** fonte de voz no seu logo (Duelo: Anybody; Confia?: Bungee). Só no logo.

## Cabeçalho
```html
<nav class="mt-barra" aria-label="Matutar Games">
  <div class="mt-barra-dentro">
    <a class="mt-voltar" href="https://matutar-games.netlify.app/" data-mt-home>
      <span class="mt-seta" aria-hidden="true">←</span>
      <span class="mt-pecas" aria-hidden="true"><i></i><i></i><i></i></span>
      Todos os jogos
    </a>
    <div class="mt-acoes"><!-- ações do jogo --></div>
  </div>
</nav>
```
58px de altura (toque de 44px). Abaixo de 360px as peças somem e fica só a seta e o texto. Respeita a área segura de cima e dos lados.

## Aviso de saída
O jogo define `window.matutarSaida = () => 'texto' | null`. Com texto, o link pergunta "Sair da partida?" antes de sair. Use só quando o progresso se perderia de verdade.

## Atualizar um jogo
1. Copie a pasta `matutar-ui/` inteira para o jogo.
2. Suba o `?v=` dos links no HTML do jogo.
3. Teste o jogo (cada repositório tem seus testes).

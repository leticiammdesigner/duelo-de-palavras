"""Desktop: o Duelo tem que parecer da mesma família do Confia? e do Qual o Preço?.

Nos outros dois jogos a barra "Todos os jogos" atravessa a tela. Aqui o app é de altura fixa
(a rodada depende disso: campo preso embaixo, pilhas rolando por dentro), então ele fica numa
coluna centralizada. O que se cobra abaixo é que, numa tela larga, a faixa da barra atravesse
mesmo assim, que a coluna tenha traço dos dois lados em vez de flutuar, e que nada disso crie
rolagem horizontal nem mude o celular.

Uso:  python3 -m http.server 8795   (na raiz do repositório)
      python3 testes/desktop.py http://localhost:8795
"""
import sys
from playwright.sync_api import sync_playwright

BASE = sys.argv[1].rstrip('/') if len(sys.argv) > 1 else 'http://localhost:8795'
res = []
def ok(n, c, x=''):
    res.append(bool(c)); print(('OK  ' if c else 'FALHA ') + n + (' · ' + str(x) if not c and x != '' else ''))

def medir(pg):
    return pg.evaluate("""() => {
      const app = document.getElementById('app');
      const barra = app.querySelector('.mt-barra');
      const faixa = getComputedStyle(barra, '::before');
      const ea = getComputedStyle(app);
      return {
        larguraApp: app.getBoundingClientRect().width,
        larguraTela: document.documentElement.clientWidth,
        bordaEsq: parseFloat(ea.borderLeftWidth), bordaDir: parseFloat(ea.borderRightWidth),
        fundoApp: ea.backgroundColor, fundoPagina: getComputedStyle(document.body).backgroundColor,
        faixaLargura: faixa.width, faixaBorda: parseFloat(faixa.borderBottomWidth) || 0,
        rolagemH: document.documentElement.scrollWidth > document.documentElement.clientWidth
      };
    }""")

with sync_playwright() as p:
    b = p.chromium.launch()

    # ---------------- tela larga ----------------
    pg = b.new_page(viewport={'width': 1366, 'height': 850})
    erros = []
    pg.on('pageerror', lambda e: erros.append(str(e)))
    pg.goto(BASE, wait_until='networkidle')
    pg.wait_for_timeout(400)
    d = medir(pg)

    ok('a coluna do jogo não ocupa a tela toda', 560 <= d['larguraApp'] <= 760, d['larguraApp'])
    ok('a coluna tem traço dos dois lados', d['bordaEsq'] >= 1 and d['bordaDir'] >= 1,
       (d['bordaEsq'], d['bordaDir']))
    ok('a página é de um tom diferente da coluna', d['fundoApp'] != d['fundoPagina'],
       (d['fundoApp'], d['fundoPagina']))
    # a faixa é pintada pelo ::before da barra, esticado para além da coluna
    largura_faixa = float((d['faixaLargura'] or '0px').replace('px', ''))
    ok('a faixa da barra atravessa a tela', largura_faixa >= d['larguraTela'],
       (largura_faixa, d['larguraTela']))
    ok('a faixa fecha com a linha de baixo, como nos outros jogos', d['faixaBorda'] >= 1, d['faixaBorda'])
    ok('nada empurra a página na horizontal', not d['rolagemH'])
    ok('abrir no desktop não gera erro de script', not erros, erros[:2])

    # a rodada continua de altura fixa: é o que segura o campo embaixo durante o minuto
    pg.click('#btn-jogar')
    for _ in range(40):
        if pg.locator('#btn-valendo').is_visible(): pg.click('#btn-valendo')
        if pg.locator('#tela-rodada').is_visible() and pg.locator('#entrada').is_enabled(): break
        pg.wait_for_timeout(200)
    ok('a rodada abre no desktop', pg.locator('#tela-rodada').is_visible())
    dentro = pg.evaluate("""() => {
      const app = document.getElementById('app').getBoundingClientRect();
      const campo = document.getElementById('entrada').getBoundingClientRect();
      return { campoDentro: campo.bottom <= app.bottom + 2, appNaTela: app.height <= window.innerHeight + 2 };
    }""")
    ok('o campo de digitar continua preso dentro da tela', dentro['campoDentro'])
    ok('o app continua cabendo na altura da janela', dentro['appNaTela'])

    # ---------------- celular: nada pode ter mudado ----------------
    cel = b.new_page(viewport={'width': 390, 'height': 844})
    cel.goto(BASE, wait_until='networkidle')
    cel.wait_for_timeout(400)
    c = medir(cel)
    ok('no celular a coluna continua ocupando a tela', c['larguraApp'] >= c['larguraTela'] - 1,
       (c['larguraApp'], c['larguraTela']))
    ok('no celular a coluna não ganha traço lateral', c['bordaEsq'] == 0 and c['bordaDir'] == 0,
       (c['bordaEsq'], c['bordaDir']))
    ok('no celular não aparece rolagem horizontal', not c['rolagemH'])

    b.close()

print('%d de %d OK' % (sum(res), len(res)))
sys.exit(0 if all(res) else 1)

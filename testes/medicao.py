"""Medição: só o endereço oficial conta, e o funil sai de uma partida de verdade.

medir.js só age em matutargames.com.br, e o teste roda em localhost. Então o navegador é levado
a acreditar que está no endereço oficial: as requisições para https://matutargames.com.br são
atendidas com os arquivos do disco, e o script do GoatCounter vira um dublê que anota o que
teria sido enviado, sem rede nenhuma.

O relógio é virtual, então a partida de três minutos roda em segundos.

O convite é o evento que mais interessa aqui: é ele que diz se o desafio por link traz gente
nova. Por isso ele é exercitado pelos dois caminhos, o compartilhamento nativo e a cópia, que
é por onde o desktop inteiro passa.

Uso:  python3 -m http.server 8798   (na raiz do repositório)
      python3 testes/medicao.py http://localhost:8798
"""
import os, sys
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

BASE = sys.argv[1].rstrip('/') if len(sys.argv) > 1 else 'http://localhost:8798'
CASA = 'https://matutargames.com.br'
RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
res = []
def ok(n, c, x=''):
    res.append(bool(c)); print(('OK  ' if c else 'FALHA ') + n + (' · ' + str(x) if not c and x != '' else ''))

def rodadas_do_jogo():
    import re
    fonte = open(os.path.join(RAIZ, 'index.html'), encoding='utf-8').read()
    return int(re.search(r'RODADAS\s*=\s*(\d+)', fonte).group(1))
N_RODADAS = rodadas_do_jogo()

DUBLE = """
  window.__pedidos = [];
  window.goatcounter = { count: function (d) { window.__pedidos.push(d); } };
"""

def preparar(ctx, rede, fingir_casa=True):
    if fingir_casa:
        def servir(route, request):
            # em produção o jogo vive em /duelo/; o servidor local serve a raiz do repositório
            caminho = request.url[len(CASA):].split('?')[0] or '/'
            if caminho.startswith('/duelo'): caminho = caminho[len('/duelo'):] or '/'
            if caminho == '/': caminho = '/index.html'
            r = ctx.request.get(BASE + caminho)
            route.fulfill(status=r.status, body=r.body(),
                          headers={'content-type': r.headers.get('content-type', 'text/html')})
        ctx.route(CASA + '/**', servir)
    def contador(route, request):
        rede.append(request.url)
        route.fulfill(status=200, content_type='application/javascript', body=DUBLE)
    ctx.route('**/gc.zgo.at/**', contador)

def nomes(pg):
    return [d.get('path') for d in pg.evaluate("() => window.__pedidos || []")]

def palavras_da_pista(frase, quantas=3):
    import glob, json as _json
    frase = ' '.join((frase or '').split()).lower()
    for caminho in glob.glob(os.path.join(RAIZ, 'dados', '*.json')):
        d = _json.load(open(caminho, encoding='utf-8'))
        if ' '.join(str(d.get('pista', '')).split()).lower() == frase:
            return [p[0] for p in d['bot'][:quantas * 4]][:quantas]
    return []

def ate_rodada(pg):
    for _ in range(60):
        if pg.locator('#btn-valendo').is_visible(): pg.click('#btn-valendo')
        if pg.locator('#tela-rodada').is_visible() and pg.locator('#entrada').is_enabled(): return
        pg.clock.run_for(500); pg.wait_for_timeout(120)

def jogar(pg):
    pg.click('#btn-jogar')
    for _ in range(N_RODADAS):
        ate_rodada(pg)
        frase = (pg.text_content('#rod-frase') or '').strip()
        for pw in palavras_da_pista(frase):
            pg.fill('#entrada', pw); pg.press('#entrada', 'Enter'); pg.clock.run_for(300)
        pg.clock.run_for(62000)
        bt = pg.locator('#tela-resumo button.btn-primario')
        if bt.count() and bt.first.is_visible(): bt.first.click(); pg.clock.run_for(800); pg.wait_for_timeout(200)

with sync_playwright() as p:
    b = p.chromium.launch()

    # ---------------- no endereço oficial: mede ----------------
    ctx = b.new_context(viewport={'width': 390, 'height': 844})
    rede = []
    preparar(ctx, rede)
    # sem compartilhamento nativo: força o caminho de cópia, que é o do desktop
    ctx.add_init_script("""
      Object.defineProperty(navigator, 'share', { configurable: true, value: undefined });
      navigator.clipboard.writeText = (t) => { window.__copiado = t; return Promise.resolve(); };
    """)
    pg = ctx.new_page()
    erros = []
    pg.on('pageerror', lambda e: erros.append(str(e)))
    pg.clock.install()
    pg.goto(CASA + '/duelo/', wait_until='networkidle')
    pg.wait_for_timeout(500)

    ok('no endereço oficial o contador é carregado', any('count.js' in u for u in rede), rede)
    ok('medir existe para o jogo chamar', pg.evaluate("() => typeof window.medir") == 'function')
    ok('carregar o jogo não gera erro de script', not erros, erros[:2])

    jogar(pg)
    ok('a partida chega ao resultado', pg.locator('#tela-final').is_visible())
    ok('começar a partida vira evento', 'duelo-inicia' in nomes(pg), nomes(pg))
    ok('terminar a partida vira evento', 'duelo-termina' in nomes(pg), nomes(pg))

    # criar e mandar o convite: o motor que traz gente nova
    pg.fill('#apelido', 'Leticia')
    pg.locator('button:has-text("Criar link de desafio")').click()
    pg.wait_for_timeout(600)
    pg.locator('button:has-text("Convidar um amigo")').click()
    pg.wait_for_timeout(500)
    ok('mandar o convite vira evento', 'duelo-convida' in nomes(pg), nomes(pg))

    enviado = pg.evaluate("() => (window.__pedidos || []).find(d => d.path === 'duelo-convida')") or {}
    ok('o evento vai marcado como evento, não como página', enviado.get('event') is True, enviado)
    ok('cada convite conta, não um por sessão', enviado.get('no_session') is True, enviado)
    ok('nenhum evento leva apelido, palavra ou pontuação',
       all(set(d.keys()) <= {'path', 'title', 'event', 'no_session'}
           for d in pg.evaluate("() => window.__pedidos || []")))

    # o link cru não aparece mais na tela de propósito: ele vive no texto que foi para a área de
    # transferência, que o dublê do clipboard guardou
    copiado = pg.evaluate("() => window.__copiado || ''")
    link = next((w for w in copiado.split() if '#d=' in w), '')
    ok('o convite copiado traz o link do desafio', link.startswith('http') and '#d=' in link, copiado[:80])

    # ---------------- quem recebe o desafio ----------------
    ctx2 = b.new_context(viewport={'width': 390, 'height': 844})
    rede2 = []
    preparar(ctx2, rede2)
    outra = ctx2.new_page()
    outra.goto(link if link.startswith('http') else CASA + '/duelo/', wait_until='networkidle')
    outra.wait_for_timeout(900)
    if link:
        ok('abrir um desafio recebido vira evento', 'duelo-desafio-recebido' in nomes(outra), nomes(outra))
        aceitar = outra.locator('#btn-aceitar')
        # sem o guarda, um desafio que não abre deixa o teste parado 30s em vez de falhar
        if aceitar.is_visible():
            outra.clock.install()
            aceitar.click()
            outra.wait_for_timeout(600)
            ate_rodada(outra)
            ok('aceitar o desafio vira evento, separado de começar sozinho',
               'duelo-desafio-aceito' in nomes(outra) and 'duelo-inicia' not in nomes(outra), nomes(outra))
        else:
            ok('o desafio recebido oferece o botão de aceitar', False,
               (outra.text_content('#des-titulo') or '').strip())

    # ---------------- em prévia: não conta ----------------
    ctx3 = b.new_context(viewport={'width': 390, 'height': 844})
    rede3 = []
    preparar(ctx3, rede3, fingir_casa=False)
    previa = ctx3.new_page()
    previa.clock.install()
    previa.goto(BASE + '/', wait_until='networkidle')
    previa.wait_for_timeout(500)
    previa.click('#btn-jogar')
    previa.wait_for_timeout(800)

    ok('fora do endereço oficial o contador nem é pedido', rede3 == [], rede3)
    ok('jogar em prévia não envia nada', not previa.evaluate("() => window.__pedidos"))
    ok('medir continua existindo, para nenhuma chamada quebrar',
       previa.evaluate("() => typeof window.medir") == 'function')

    b.close()

print('%d de %d OK' % (sum(res), len(res)))
sys.exit(0 if all(res) else 1)

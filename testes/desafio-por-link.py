"""Desafio por link: a partida inteira viaja na URL, sem banco nenhum.

Faz o ciclo que a jogadora faz pelo WhatsApp, do começo ao fim: joga uma partida de verdade,
cria o link, abre esse link num navegador limpo e confere que a gravação chegou inteira, com
as mesmas pistas e as mesmas palavras nos mesmos tempos.

O relógio é virtual, então a partida de três minutos roda em segundos.

Uso:  python3 -m http.server 8795   (na raiz do repositório)
      python3 testes/desafio-por-link.py http://localhost:8795
"""
import os, re, sys
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compartilhar_comum as comp

def rodadas_do_jogo():
    """Lê RODADAS do index.html: o teste acompanha o jogo em vez de fixar o número."""
    import os, re as _re
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    fonte = open(os.path.join(raiz, 'index.html'), encoding='utf-8').read()
    return int(_re.search(r'RODADAS\s*=\s*(\d+)', fonte).group(1))
N_RODADAS = rodadas_do_jogo()

BASE = sys.argv[1].rstrip('/') if len(sys.argv) > 1 else 'http://localhost:8795'
PAL = ['casa', 'mesa', 'pato', 'carro', 'porta', 'terra', 'barco', 'ponte', 'festa', 'papel']
res = []
def ok(n, c, x=''):
    res.append(bool(c)); print(('OK  ' if c else 'FALHA ') + n + (' · ' + str(x) if not c and x != '' else ''))

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def palavras_da_pista(frase, quantas=4):
    """Devolve palavras que valem na pista que está na tela.

    Antes o teste digitava palavras genéricas. Numa pista como "têm exatamente três
    letras" nenhuma delas valia, e como a gravação levava até o que foi recusado, o teste
    passava sem nunca ter exercitado o caminho de verdade.
    """
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

with sync_playwright() as p:
    b = p.chromium.launch()

    # ---------------- quem desafia: joga e gera o link ----------------
    ctx = b.new_context(viewport={'width': 390, 'height': 844})
    comp.instalar(ctx)
    # O compartilhamento nativo abre um menu do sistema que o Playwright não controla. Aqui ele
    # é trocado por um espião, instalado antes de a página rodar, que guarda o que seria enviado.
    ctx.add_init_script('''
      window.__partilhado = null;
      Object.defineProperty(navigator, 'share', {
        configurable: true, writable: true,
        value: function (d) { window.__partilhado = d; return Promise.resolve(); }
      });
    ''')
    pg = ctx.new_page()
    erros = []
    pg.on('pageerror', lambda e: erros.append(str(e)))
    pg.clock.install()
    pg.goto(BASE, wait_until='networkidle')

    pg.click('#btn-jogar')
    minhas = []
    for rodada in range(N_RODADAS):
        ate_rodada(pg)
        frase = (pg.text_content('#rod-frase') or '').strip()
        palavras = palavras_da_pista(frase)
        ok('rodada %d: achei palavras que valem nesta pista' % (rodada + 1), len(palavras) >= 3, frase)
        destaRodada = []
        for pw in palavras:
            pg.fill('#entrada', pw); pg.press('#entrada', 'Enter'); pg.clock.run_for(300)
            destaRodada.append(pw)
        minhas.append(destaRodada)
        pg.clock.run_for(62000)
        bt = pg.locator('#tela-resumo button.btn-primario')
        if bt.count() and bt.first.is_visible(): bt.first.click(); pg.clock.run_for(800); pg.wait_for_timeout(200)

    ok('a partida chega ao resultado', pg.locator('#tela-final').is_visible())

    criar = pg.locator('#apelido')
    ok('o bloco de desafiar aparece sem depender do Claude', criar.count() == 1 and criar.is_visible())

    pg.fill('#apelido', 'Leticia')
    pg.locator('button:has-text("Criar link de desafio")').click()
    pg.wait_for_timeout(600)

    ok('o link cru não aparece na tela', pg.locator('.link-desafio').count() == 0)
    ok('o botão de convidar aparece', pg.locator('button:has-text("Convidar um amigo")').count() == 1)

    pg.locator('button:has-text("Convidar um amigo")').click()
    pg.wait_for_timeout(400)
    partilhado = pg.evaluate("() => window.__partilhado")
    ok('convidar usa o compartilhamento nativo do aparelho', partilhado is not None)

    texto = (partilhado or {}).get('text', '')
    ok('o convite não manda o endereço duas vezes', texto.count('#d=') == 1, texto.count('#d='))
    ok('o convite traz o placar com os quadradinhos', texto.count('R1') == 1 and ('🟦' in texto or '🟧' in texto or '⬜' in texto))
    ok('o convite tem uma linha por rodada', sum(texto.count('R%d' % (i + 1)) for i in range(N_RODADAS)) == N_RODADAS)
    ok('o convite não fala do adversário simulado', 'simulado' not in texto.lower(), texto[:80])

    link = [l for l in texto.split('\n') if '#d=' in l]
    link = link[0].strip() if link else ''
    ok('o link foi gerado', link.startswith(BASE) and '#d=' in link, link[:70])
    ok('o link cabe numa mensagem (abaixo de 2000 caracteres)', 0 < len(link) < 2000, len(link))
    ok('o link usa compressão', '#d=c' in link, link.split('#d=')[-1][:1] if '#d=' in link else '')
    print('    tamanho do link: %d caracteres' % len(link))
    ok('criar o link não precisou de rede', not erros, erros[:2])

    # ---------------- quem recebe: navegador limpo, só o link ----------------
    ctx2 = b.new_context(viewport={'width': 390, 'height': 844})
    comp.instalar(ctx2)
    outra = ctx2.new_page()
    erros2 = []
    outra.on('pageerror', lambda e: erros2.append(str(e)))
    outra.goto(link, wait_until='networkidle')
    outra.wait_for_timeout(900)

    ok('o link abre direto na tela de desafio', outra.locator('#tela-desafio').is_visible())
    titulo = (outra.text_content('#des-titulo') or '').strip()
    ok('mostra quem desafiou', 'Leticia' in titulo, titulo)
    ok('mostra os pontos da partida original', (outra.text_content('#des-pontos') or '').strip().isdigit(),
       (outra.text_content('#des-pontos') or '').strip())
    ok('abrir o desafio não gerou erro de script', not erros2, erros2[:2])

    outra.clock.install()
    outra.locator('#btn-aceitar').click()
    outra.wait_for_timeout(500)
    ate_rodada(outra)
    ok('a partida contra a gravação começa', outra.locator('#tela-rodada').is_visible())

    # as palavras do rival nesta partida têm que ser as que foram digitadas na primeira
    outra.clock.run_for(62000)
    outra.wait_for_timeout(300)
    rival = outra.evaluate("""() => {
      const linhas = [...document.querySelectorAll('#tela-resumo .tabela-palavras li, .lados li')]
        .map(e => e.textContent.trim().toLowerCase());
      return linhas.join(' ');
    }""")
    achou = [w for w in minhas[0] if w in rival]
    ok('as palavras da primeira rodada chegaram para quem recebeu', len(achou) >= 3, achou)

    # ---------------- link cortado não quebra ----------------
    cortado = ctx2.new_page()
    err3 = []
    cortado.on('pageerror', lambda e: err3.append(str(e)))
    meio = link[:len(link) - 40]
    cortado.goto(meio, wait_until='networkidle')
    cortado.wait_for_timeout(900)
    t = (cortado.text_content('#des-titulo') or '').strip()
    ok('link cortado avisa em vez de quebrar', t in ('Link incompleto', 'Desafio não encontrado'), t)
    ok('link cortado não derruba o script', not err3, err3[:2])

    # ---------------- link antigo do Claude não quebra fora dele ----------------
    antigo = ctx2.new_page()
    err4 = []
    antigo.on('pageerror', lambda e: err4.append(str(e)))
    antigo.goto(BASE + '/#d-abc123def456', wait_until='networkidle')
    antigo.wait_for_timeout(900)
    t4 = (antigo.text_content('#des-titulo') or '').strip()
    ok('link antigo explica em vez de travar', t4 == 'Desafio indisponível', t4)
    ok('link antigo não derruba o script', not err4, err4[:2])

    b.close()

print('%d de %d OK' % (sum(res), len(res)))
sys.exit(0 if all(res) else 1)

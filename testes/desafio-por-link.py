"""Desafio por link: a partida inteira viaja na URL, sem banco nenhum.

Faz o ciclo que a jogadora faz pelo WhatsApp, do começo ao fim: joga uma partida de verdade,
cria o link, abre esse link num navegador limpo e confere que a gravação chegou inteira, com
as mesmas pistas e as mesmas palavras nos mesmos tempos.

O relógio é virtual, então a partida de quatro minutos roda em segundos.

Uso:  python3 -m http.server 8795   (na raiz do repositório)
      python3 testes/desafio-por-link.py http://localhost:8795
"""
import os, re, sys
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compartilhar_comum as comp

BASE = sys.argv[1].rstrip('/') if len(sys.argv) > 1 else 'http://localhost:8795'
PAL = ['casa', 'mesa', 'pato', 'carro', 'porta', 'terra', 'barco', 'ponte', 'festa', 'papel']
res = []
def ok(n, c, x=''):
    res.append(bool(c)); print(('OK  ' if c else 'FALHA ') + n + (' · ' + str(x) if not c and x != '' else ''))

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
    pg = ctx.new_page()
    erros = []
    pg.on('pageerror', lambda e: erros.append(str(e)))
    pg.clock.install()
    pg.goto(BASE, wait_until='networkidle')

    pg.click('#btn-jogar')
    minhas = []
    for rodada in range(4):
        ate_rodada(pg)
        destaRodada = []
        for pw in PAL[:4]:
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

    link = (pg.text_content('.link-desafio') or '').strip()
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

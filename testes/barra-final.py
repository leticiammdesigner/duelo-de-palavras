"""Verifica a barra final do caminho do jogo no domínio próprio.

Imita o proxy do Netlify (force = true), que serve o jogo tanto em /duelo quanto
em /duelo/. Sem a barra, os caminhos relativos do jogo saem da raiz do domínio e a
página vem sem CSS. Quem põe a barra é a linha no <head> do index.html, porque o
motor do Netlify não distingue os dois caminhos e qualquer regra lá vira laço.

Uso:  python3 testes/barra-final.py
"""
import functools, http.server, os, socketserver, threading
from playwright.sync_api import sync_playwright

SLUG = 'duelo'
RAIZ = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.')
res = []
def ok(n, c, x=''):
    res.append(bool(c)); print(('OK  ' if c else 'FALHA ') + n + (' · ' + str(x) if not c and x != '' else ''))

class H(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        p = path.split('?')[0].split('#')[0]
        if p == '/' + SLUG: p = '/' + SLUG + '/'
        if p.startswith('/' + SLUG + '/'): p = p[len(SLUG) + 1:]
        return super().translate_path(p)
    def log_message(self, *a): pass

srv = socketserver.TCPServer(('127.0.0.1', 0), functools.partial(H, directory=RAIZ))
threading.Thread(target=srv.serve_forever, daemon=True).start()
base = 'http://127.0.0.1:%d' % srv.server_address[1]

with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page()
    pg.goto(base + '/' + SLUG); pg.wait_for_timeout(600)
    ok('/%s sem barra se corrige para /%s/' % (SLUG, SLUG),
       pg.evaluate('location.pathname') == '/%s/' % SLUG, pg.evaluate('location.pathname'))
    ok('depois da correção o CSS carrega',
       pg.evaluate("[...document.styleSheets].some(s=>{try{return s.cssRules.length>0}catch(e){return false}})"))
    pg.goto(base + '/' + SLUG + '/'); pg.wait_for_timeout(600)
    ok('/%s/ com barra não redireciona (sem laço)' % SLUG,
       pg.evaluate('location.pathname') == '/%s/' % SLUG, pg.evaluate('location.pathname'))
    b.close()
srv.shutdown(); srv.server_close()
print('%d de %d OK' % (sum(res), len(res)))

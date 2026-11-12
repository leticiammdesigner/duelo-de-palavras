"""Teste de ponta a ponta do Duelo de Palavras (Playwright, Chromium).
Uso:  python3 -m http.server 8795  (na raiz do repositório)
      python3 testes/e2e.py http://localhost:8795
Capturas de tela (opcional): defina CAPTURAS=/pasta/ para salvar as telas em 360 px.
"""
import os, sys
import re
from playwright.sync_api import sync_playwright
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import compartilhar_comum as comp
BASE=sys.argv[1].rstrip('/') if len(sys.argv)>1 else 'http://localhost:8795'
S=os.environ.get('CAPTURAS')
res=[]
def ok(n,c,x=''): res.append(c); print(('OK  ' if c else 'FALHA ')+n+(' · '+str(x) if not c and x!='' else ''))
PAL=['casa','mesa','pato','carro','porta','terra','barco','ponte','festa','papel','areia','preto','verde','livro','lento']
with sync_playwright() as p:
    b=p.chromium.launch()
    for w,h in [(320,568),(360,740),(390,844),(1280,900)]:
        ctx=b.new_context(viewport={'width':w,'height':h},has_touch=w<500,is_mobile=w<500); comp.instalar(ctx); pg=ctx.new_page(); err=[]; google=[]
        pg.on('request',lambda r:('fonts.googleapis' in r.url or 'fonts.gstatic' in r.url) and google.append(r.url))
        pg.on('pageerror',lambda e:err.append(str(e))); pg.on('console',lambda m:m.type=='error' and 'fonts.g' not in m.text and 'ERR_TUNNEL' not in m.text and err.append(m.text))
        pg.clock.install()
        pg.goto(BASE+'/'); pg.clock.run_for(1500)
        ok(f'[{w}] html em pt-BR', pg.evaluate('document.documentElement.lang')=='pt-BR')
        ok(f'[{w}] Duelo do Dia escondido (sem card, sem painel de teste)', pg.evaluate("""(()=>{const c=document.getElementById('card-dia');const t=document.body.innerText;return c.hidden&&!c.offsetParent&&!/simulados|Modo de teste|tentativa oficial|Duelo do Dia/.test(t)})()"""))
        ok(f'[{w}] fonte Anybody local carregada', pg.evaluate("document.fonts.ready.then(()=>document.fonts.check('800 20px Anybody'))") and not google)
        lat=lambda: pg.evaluate('document.documentElement.scrollWidth<=innerWidth')
        ok(f'[{w}] início sem rolagem lateral', lat())
        ok(f'[{w}] "Todos os jogos" à vista e aponta para a home', pg.get_attribute('.mt-voltar','href')=='https://matutar-games.netlify.app/' and pg.evaluate("document.querySelector('.mt-voltar').getBoundingClientRect().bottom<=innerHeight"))
        ok(f'[{w}] no início, sair não pede confirmação', pg.evaluate('window.matutarSaida()') is None)
        if w==360 and S: pg.screenshot(path=S+'duelo-'+'inicio.png')
        def ate_rodada():
            for _ in range(60):
                if pg.locator('#btn-valendo').is_visible(): pg.click('#btn-valendo')
                if pg.locator('#tela-rodada').is_visible() and pg.locator('#entrada').is_enabled(): return
                pg.clock.run_for(500); pg.wait_for_timeout(150)
        pg.click('#btn-jogar'); ate_rodada()
        ok(f'[{w}] rodada em andamento', pg.locator('#tela-rodada').is_visible())
        ok(f'[{w}] campo de digitar e cabeçalho visíveis na rodada', pg.evaluate("(()=>{const e=document.getElementById('entrada').getBoundingClientRect(),b=document.querySelector('.mt-barra').getBoundingClientRect();return e.bottom<=innerHeight&&e.top>b.bottom-1})()"))
        pg.click('.mt-voltar'); pg.clock.run_for(200)
        ok(f'[{w}] sair no meio do duelo pede confirmação', pg.locator('#mt-aviso[open]').count()==1 and pg.url.startswith(BASE))
        if w==360 and S: pg.screenshot(path=S+'duelo-'+'aviso.png')
        pg.click('#mt-aviso button[value=ficar]'); pg.clock.run_for(200)
        for rodada in range(4):
            ate_rodada()
            for pw in PAL[:6]:
                pg.fill('#entrada',pw); pg.press('#entrada','Enter'); pg.clock.run_for(300)
            if rodada==0 and w==360 and S: pg.screenshot(path=S+'duelo-'+'rodada.png')
            pg.clock.run_for(62000)
            ok(f'[{w}] rodada {rodada+1} terminou no resumo', pg.locator('#tela-resumo').is_visible() or pg.locator('#tela-final').is_visible())
            if rodada==0 and w==360 and S: pg.screenshot(path=S+'duelo-'+'resumo.png')
            bt=pg.locator('#tela-resumo button.btn-primario')
            if bt.count() and bt.first.is_visible(): bt.first.click(); pg.clock.run_for(800); pg.wait_for_timeout(300)
        ok(f'[{w}] partida completa chega ao resultado', pg.locator('#tela-final').is_visible())
        ok(f'[{w}] no resultado, sair não pede confirmação', pg.evaluate('window.matutarSaida()') is None)
        ok(f'[{w}] resultado sem rolagem lateral', lat())
        if w==360 and S: pg.screenshot(path=S+'duelo-'+'final.png')
        small=pg.evaluate("[...document.querySelectorAll('button,a')].filter(e=>e.offsetParent&&e.getBoundingClientRect().height<44&&e.getBoundingClientRect().width>0).map(e=>e.textContent.trim().slice(0,18)+':'+Math.round(e.getBoundingClientRect().height))")
        ok(f'[{w}] alvos de toque >= 44px na tela final', not small, small)
        def regras(txt):
            vaza=[x for x in PAL if re.search(r'\b'+x+r'\b',txt)]
            r=txt.startswith('Duelo de Palavras · ') and re.search(r'^(Venci|Perdi para|Empatei com) ',txt,re.M) and len(re.findall(r'^[🟦🟧⬜] R\d',txt,re.M))==4 and 'Consegue me vencer?' in txt and not vaza
            return bool(r), vaza
        comp.checar(pg, ok, f'[{w}] compartilhar', '#btn-compartilhar', '#status-compartilhar', '#texto-compartilhar', 'https://duelo-matutar.netlify.app/', '#tela-final .compartilhar', regras)
        ok(f'[{w}] sem erros de script', not err, err[:3])
        ctx.close()
    ctx=b.new_context(viewport={'width':390,'height':844}); pg=ctx.new_page(); pg.goto(BASE+'/#dia'); pg.wait_for_timeout(800)
    ok('[390] link #dia não abre o Duelo do Dia', pg.locator('#tela-inicio').is_visible() and pg.evaluate("document.getElementById('card-dia').hidden"))
    ctx.close()
    b.close()
print(f'{sum(res)} de {len(res)} OK')

"""Partida no celular com o teclado virtual aberto (Playwright, Chromium).
Uso:  python3 -m http.server 8795  (na raiz do repositório)
      python3 testes/teclado.py http://localhost:8795
Capturas de tela (opcional): defina CAPTURAS=/pasta/.

O teclado é simulado de dois jeitos, porque o Chrome Android pode fazer qualquer um dos dois:
  conteudo  a janela inteira encolhe (interactive-widget=resizes-content, que o jogo pede);
  visual    a janela fica do mesmo tamanho e só a parte visível encolhe e desce (visualViewport.offsetTop).
Limitação: não é um aparelho real. Teclado Samsung, barra de sugestões e animação de abertura não são reproduzidos.
"""
import os, sys
from playwright.sync_api import sync_playwright
BASE = sys.argv[1].rstrip('/') if len(sys.argv) > 1 else 'http://localhost:8795'
S = os.environ.get('CAPTURAS')
res = []
def ok(n, c, x=''):
    res.append(bool(c)); print(('OK  ' if c else 'FALHA ') + n + (' · ' + str(x) if not c and x != '' else ''))

# visualViewport controlável: no modo "visual" a parte visível encolhe e desce, a janela não muda
FALSO_VV = """(()=>{const t=new EventTarget();let h=ALTURA,top=0;
Object.defineProperty(window,'visualViewport',{value:Object.defineProperties(t,{height:{get(){return h}},width:{get(){return innerWidth}},offsetTop:{get(){return top}},offsetLeft:{get(){return 0}},scale:{get(){return 1}},pageTop:{get(){return top}}})});
window.__teclado=(alt,desloc)=>{h=alt;top=desloc;t.dispatchEvent(new Event('resize'));};})()"""

# medições na parte visível da tela
MEDIR = """(()=>{const vv=visualViewport,top=vv.offsetTop,bot=top+vv.height;
const r=s=>document.querySelector(s).getBoundingClientRect();
const pista=r('#tela-rodada .pista'),frase=r('#rod-frase'),dica=document.getElementById('rod-dica'),arena=r('#arena'),campo=r('#tela-rodada .campo'),
 ret=r('#retorno'),inp=r('#entrada'),bt=r('#btn-enviar'),barra=r('.mt-barra'),topo=r('#tela-rodada .topo');
const db=dica.hidden?frase.bottom:dica.getBoundingClientRect().bottom;
const tapa=(x,y)=>{const e=document.elementFromPoint(x,y);return e&&(e.id==='entrada'||e.id==='btn-enviar'||e.closest('#btn-enviar'))};
// as peças só aparecem dentro da própria pilha: pilha e arena cortam o que passar (overflow) e cabem na arena
let pecaFora=getComputedStyle(document.getElementById('arena')).overflow!=='hidden';document.querySelectorAll('#arena .pilha').forEach(pl=>{const b=pl.getBoundingClientRect();
 if(getComputedStyle(pl).overflow!=='hidden'||b.top<arena.top-1||b.bottom>arena.bottom+1)pecaFora=true});
const fr=document.getElementById('rod-frase'),fb=frase;const fraseLivre=document.elementFromPoint(fb.left+5,fb.top+fb.height/2)===fr||fr.contains(document.elementFromPoint(fb.left+5,fb.top+fb.height/2));
return {top,bot,barra:[barra.top,barra.bottom],
 barraVisivel:barra.top>=top-1&&barra.bottom<=bot+1,
 pistaInteira:fraseLivre&&pista.top>=top-1&&pista.bottom<=bot+1&&db<=pista.bottom+1&&frase.top>=pista.top,
 campoVisivel:inp.top>=top-1&&inp.bottom<=bot+1&&bt.bottom<=bot+1&&bt.right<=innerWidth+1,
 semSobrepor:topo.bottom<=pista.top+1&&pista.bottom<=arena.top+1&&arena.bottom<=campo.top+1&&ret.bottom<=inp.top+1&&!pecaFora,
 campoLivre:tapa(inp.left+10,inp.top+inp.height/2)&&tapa(inp.right-10,inp.top+inp.height/2)&&tapa(bt.left+bt.width/2,bt.top+bt.height/2),
 alturaArena:Math.round(arena.height),inpTop:Math.round(inp.top),foco:document.activeElement&&document.activeElement.id}})()"""

LONGAS = [('têm uma vogal só', 'Exatamente uma vogal na palavra inteira: mar e três valem; casa não, porque tem dois A.'),
          ('alternam consoante e vogal, com 5 letras ou mais', 'Como menina, tomate, sapato.')]

def checar(pg, nome, alt_esperada=None):
    m = pg.evaluate(MEDIR)
    ok(f'{nome}: pista inteira à vista', m['pistaInteira'], m)
    ok(f'{nome}: campo e Enviar acima do teclado', m['campoVisivel'], m)
    ok(f'{nome}: nada encosta no campo (peças, mensagens, navegação)', m['campoLivre'] and m['semSobrepor'], m)
    ok(f'{nome}: "Todos os jogos" continua à vista', m['barraVisivel'], m)
    return m

with sync_playwright() as p:
    b = p.chromium.launch()
    # (largura, altura sem teclado, alturas com teclado)  360x780: Galaxy S2x · 412x915: Galaxy Ultra · 390x844
    for w, h, teclados in [(360, 780, [330, 400, 460]), (390, 844, [430]), (412, 915, [480])]:
        for modo in ('conteudo', 'visual'):
            ctx = b.new_context(viewport={'width': w, 'height': h}, has_touch=True, is_mobile=True)
            pg = ctx.new_page(); err = []
            pg.on('pageerror', lambda e: err.append(str(e)))
            pg.add_init_script(FALSO_VV.replace('ALTURA', str(h)))
            pg.clock.install(); pg.goto(BASE + '/'); pg.clock.run_for(1500)

            def teclado(alt):
                if modo == 'conteudo':
                    pg.set_viewport_size({'width': w, 'height': alt}); pg.evaluate(f'window.__teclado({alt},0)')
                else:  # parte visível encolhe e o navegador desloca para mostrar o campo
                    pg.evaluate(f'window.__teclado({alt},{0 if alt==h else h-alt})')
                pg.clock.run_for(100); pg.wait_for_timeout(60)

            def ate_rodada():
                for _ in range(60):
                    if pg.locator('#btn-valendo').is_visible(): pg.click('#btn-valendo')
                    if pg.locator('#tela-rodada').is_visible() and pg.locator('#entrada').is_enabled(): return
                    pg.clock.run_for(500); pg.wait_for_timeout(80)

            pg.click('#btn-jogar')
            for rodada in range(4):
                ate_rodada()
                tag = f'[{w}x{h} {modo}] rodada {rodada+1}'
                ok(f'{tag}: começa com o campo em foco', pg.evaluate('document.activeElement.id') == 'entrada')
                kb = teclados[rodada % len(teclados)]
                teclado(kb)
                if rodada < len(LONGAS):  # pistas reais mais longas do banco, com dica
                    fr, di = LONGAS[rodada]
                    pg.evaluate("([f,d])=>{document.getElementById('rod-frase').textContent=f;const e=document.getElementById('rod-dica');e.textContent=d;e.hidden=false;dispatchEvent(new Event('resize'))}", [fr, di])
                    pg.clock.run_for(50)
                checar(pg, f'{tag} teclado {kb}px')
                palavras = pg.evaluate("fetch('dados/'+__duelo.rod.pista.id+'.json').then(r=>r.json()).then(d=>d.bot.map(x=>x[0]))")
                envio = palavras[5:21] + ['xqzt', palavras[5], 'kk']  # 16 válidas, uma inventada, uma repetida, uma curta
                topos = set(); foco = True
                for k, pw in enumerate(envio):
                    pg.keyboard.type(pw, delay=0); pg.keyboard.press('Enter'); pg.clock.run_for(250); pg.wait_for_timeout(30)
                    m = pg.evaluate(MEDIR); topos.add(m['inpTop']); foco = foco and m['foco'] == 'entrada'
                    if k == 3 and rodada == 0:  # fecha e reabre o teclado no meio da rodada
                        teclado(h); checar(pg, f'{tag} teclado fechado'); teclado(kb)
                ok(f'{tag}: {len(envio)} envios seguidos pelo Enter sem perder o foco', foco)
                ok(f'{tag}: campo não pula com as mensagens', len(topos) == 1, topos)
                ret = pg.inner_text('#retorno')
                ok(f'{tag}: retorno curto e legível ("{ret}")', 0 < len(ret) <= 60 and pg.evaluate("(()=>{const m=document.querySelector('#retorno .msg');return !!m&&m.scrollHeight<=m.clientHeight+2})()"))
                pecas = pg.locator('#pilha-voce .peca-p:not(.fantasma)').count()
                nova = pg.evaluate("(()=>{const pl=document.getElementById('pilha-voce'),ps=pl.querySelectorAll('.peca-p:not(.fantasma)');if(!ps.length)return true;const u=ps[ps.length-1].getBoundingClientRect(),c=pl.getBoundingClientRect();return u.top>=c.top-1&&u.bottom<=c.bottom+1})()")
                ok(f'{tag}: pilha com {pecas} peças, a mais nova à vista', pecas >= 5 and nova, pecas)
                m = checar(pg, f'{tag} pilha cheia')
                if S and w == 360 and rodada == 0: pg.screenshot(path=f'{S}teclado-{modo}-{kb}.png')
                if S and w == 360 and rodada == 1: pg.screenshot(path=f'{S}teclado-{modo}-{kb}-longa.png')
                pg.clock.run_for(62000); pg.wait_for_timeout(100)
                teclado(h)  # no resumo o teclado fecha
                bt = pg.locator('#tela-resumo button.btn-primario')
                if bt.count() and bt.first.is_visible(): bt.first.click(); pg.clock.run_for(800); pg.wait_for_timeout(100)
            ok(f'[{w}x{h} {modo}] quatro rodadas até o resultado', pg.locator('#tela-final').is_visible())
            ok(f'[{w}x{h} {modo}] sem erros de script', not err, err[:3])
            ctx.close()
    b.close()
print(f'{sum(res)} de {len(res)} OK')

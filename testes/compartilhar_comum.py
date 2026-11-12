"""Verificações do compartilhar resultado, iguais nos três jogos da Matutar Games.
Simula a janela nativa do celular (navigator.share) e a área de transferência no Chromium:
não é um Android real, então o comportamento do aparelho em si não fica validado aqui.
Uso: instalar(contexto) antes de abrir a página; depois checar(pg, ok, tag, ...) na tela de resultado.
"""

SIMULADOR = """(()=>{window.__share={modo:'sem',enviados:[]};window.__copiado=null;
const nativo=function(d){const m=window.__share.modo;if(m==='ok'){window.__share.enviados.push(d.text);return Promise.resolve();}
  if(m==='cancela')return Promise.reject(new DOMException('cancelado','AbortError'));return Promise.reject(new DOMException('falhou','NotAllowedError'));};
Object.defineProperty(Navigator.prototype,'share',{configurable:true,get(){return window.__share.modo==='sem'?undefined:nativo}});
const cb={writeText:t=>window.__share.semCopia?Promise.reject(new Error('negado')):(window.__copiado=t,Promise.resolve()),readText:()=>Promise.resolve(window.__copiado||'')};
Object.defineProperty(Navigator.prototype,'clipboard',{configurable:true,get(){return cb}});})()"""

LARGURA = """(sel)=>{const s=document.querySelector(sel),r=s.getBoundingClientRect();
const fora=[...s.querySelectorAll('*')].filter(e=>e.offsetParent&&e.getBoundingClientRect().width>1&&(e.getBoundingClientRect().right>innerWidth||e.scrollWidth>e.clientWidth+1&&getComputedStyle(e).overflowX!=='visible')).map(e=>e.tagName+'.'+e.className);
if(document.documentElement.scrollWidth>innerWidth)fora.push('pagina '+document.documentElement.scrollWidth);if(r.left<0||r.right>innerWidth)fora.push('bloco');return fora}"""


def instalar(ctx):
    ctx.add_init_script(SIMULADOR)


def checar(pg, ok, tag, botao, status, campo, url, bloco, conferir_texto):
    """botao/status/campo: seletores. url: endereço oficial. bloco: seletor do trecho que não pode vazar.
    conferir_texto(txt) -> (bool, detalhe): regras próprias do jogo (o que precisa estar e o que não pode)."""
    clicar = lambda: (pg.locator(botao).scroll_into_view_if_needed(), pg.click(botao), pg.wait_for_timeout(250))
    st = lambda: pg.inner_text(status).strip()
    # começa do zero (o mesmo resultado pode ser testado em várias larguras)
    pg.evaluate(f"(()=>{{window.__share.enviados=[];const c=document.querySelector('{campo}');if(c)(c.closest('.challenge-fallback')||c).hidden=true;const s=document.querySelector('{status}');s.textContent=''}})()")
    b = pg.locator(botao).bounding_box()
    ok(f'{tag}: botão "Compartilhar resultado" com toque de 44px ou mais', pg.inner_text(botao).strip() in ('Compartilhar resultado', 'Desafiar um amigo') and b['height'] >= 44, b)
    ok(f'{tag}: aviso com role=status', pg.get_attribute(status, 'role') == 'status')
    f0 = pg.evaluate(LARGURA, bloco); ok(f'{tag}: nada passa da largura antes de compartilhar', not f0, f0)
    alt = pg.evaluate(f"document.querySelector('{bloco}').offsetHeight")
    # 1. cancelar a janela nativa: nada acontece
    pg.evaluate("window.__share.modo='cancela';window.__copiado=null"); clicar()
    ok(f'{tag}: cancelar a janela nativa não anuncia nada e não copia', st() == '' and pg.evaluate('window.__copiado') is None, st())
    # 2. janela nativa concluída
    pg.evaluate("window.__share.modo='ok'"); clicar()
    env = pg.evaluate('window.__share.enviados')
    ok(f'{tag}: janela nativa concluída: "Resultado compartilhado!"', 'Resultado compartilhado!' in st() and len(env) == 1, st())
    txt = env[0] if env else ''
    regra, det = conferir_texto(txt)
    linhas = txt.split('\n')
    ok(f'{tag}: texto termina com link oficial e a marca', len(linhas) >= 3 and linhas[-2] == url and linhas[-1] == 'Matutar Games · Ideias que dão jogo.', txt)
    ok(f'{tag}: texto curto (até 10 linhas) e com as regras do jogo', len(linhas) <= 10 and regra, det or txt)
    ok(f'{tag}: o aviso não mexe na altura do bloco', pg.evaluate(f"document.querySelector('{bloco}').offsetHeight") == alt)
    # 3. janela nativa falhou: copia
    pg.evaluate("window.__share.modo='erro'"); clicar()
    ok(f'{tag}: janela nativa falhou: copia e avisa "Resultado copiado!"', 'Resultado copiado!' in st() and pg.evaluate('window.__copiado') == txt, st())
    # 4. sem janela nativa (computador): copia
    pg.evaluate("window.__share.modo='sem';window.__copiado=null"); clicar()
    ok(f'{tag}: sem janela nativa: copia o mesmo texto', 'Resultado copiado!' in st() and pg.evaluate('window.__copiado') == txt, st())
    # 5. nem cópia: o texto aparece selecionado, inteiro, sem sair da tela
    pg.evaluate("window.__share.semCopia=true"); clicar()
    sel = pg.evaluate(f"""(()=>{{const t=document.querySelector('{campo}');return !!t&&!!t.offsetParent&&t.value==={repr(txt)}&&t.selectionEnd-t.selectionStart===t.value.length&&t.scrollHeight<=t.clientHeight+2}})()""")
    ok(f'{tag}: sem cópia: texto completo visível e selecionado', sel and 'Copie o texto abaixo' in st(), st())
    f1 = pg.evaluate(LARGURA, bloco); ok(f'{tag}: nada passa da largura depois de compartilhar', not f1, f1)
    pg.evaluate("window.__share.semCopia=false")
    return txt

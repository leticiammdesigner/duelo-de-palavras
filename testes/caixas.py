"""Mede texto que vaza da caixa onde está. Usado pelas baterias dos jogos da Matutar Games.

Uma palavra comprida dentro de um cartão estreito não causa rolagem lateral na página, então as checagens
de rolagem não pegam. Aqui a conta é direta: para cada elemento com borda ou fundo próprio, nenhum texto
dentro dele pode passar da borda, e nenhum texto pode estar cortado pelo próprio contêiner.
"""

MEDIR = """(folga) => {
  const visivel = e => { const r = e.getBoundingClientRect(), s = getComputedStyle(e);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none' && Number(s.opacity) > 0.05; };
  const temTexto = e => [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim());
  const caixa = e => { const s = getComputedStyle(e);
    return parseFloat(s.borderTopWidth) > 0 || parseFloat(s.borderBottomWidth) > 0 ||
           (s.backgroundColor && s.backgroundColor !== 'rgba(0, 0, 0, 0)' && s.backgroundColor !== 'transparent'); };
  const nome = e => (e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') + (e.className && typeof e.className === 'string' ? '.' + e.className.trim().split(/\\s+/).join('.') : '')).slice(0, 60);
  const achados = [];
  for (const e of document.querySelectorAll('body *')) {
    if (!visivel(e)) continue;
    const s = getComputedStyle(e);
    // texto cortado pelo próprio elemento: só conta onde o overflow de fato corta.
    // Fora isso o texto só pinta para fora, e quem pega é a medida de vazamento abaixo.
    // Caixas de 1px (texto só para leitor de tela) e reticências de propósito ficam de fora.
    const corta = (s.overflowX === 'hidden' || s.overflowX === 'clip') && e.clientWidth > 4 && e.clientHeight > 4;
    if (temTexto(e) && corta && e.scrollWidth > e.clientWidth + 1 && s.textOverflow !== 'ellipsis')
      achados.push({ onde: nome(e), texto: e.textContent.trim().slice(0, 40), problema: 'cortado', sobra: e.scrollWidth - e.clientWidth });
    if (!caixa(e) || s.overflow !== 'visible') continue;
    const c = e.getBoundingClientRect();
    for (const d of e.querySelectorAll('*')) {
      if (!visivel(d) || !temTexto(d)) continue;
      const r = d.getBoundingClientRect();
      const fora = Math.max(c.left - r.left, r.right - c.right, c.top - r.top, r.bottom - c.bottom);
      if (fora > folga) achados.push({ onde: nome(e), texto: d.textContent.trim().slice(0, 40), problema: 'vaza', sobra: Math.round(fora) });
    }
  }
  return achados.slice(0, 8); }"""


def checar(pg, ok, rotulo, folga=1.5):
    """Roda a medição na tela que está aberta. `folga` em px, para arredondamento de layout."""
    achados = pg.evaluate(MEDIR, folga)
    return ok(f'{rotulo}: nenhum texto vaza ou fica cortado na caixa', not achados, achados)

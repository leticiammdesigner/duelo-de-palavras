/* Matutar UI v1.0.0 · navegação para a home da Matutar Games.
 * Cada jogo pode definir window.matutarSaida = () => texto | null.
 * Se devolver um texto, o link "Todos os jogos" pergunta antes de sair (há progresso que se perderia).
 * Sem texto, o link funciona como um link comum.
 */
(function () {
  'use strict';
  var HOME = 'https://matutar-games.netlify.app/';
  function aviso(msg, destino) {
    var d = document.getElementById('mt-aviso');
    if (!d) {
      d = document.createElement('dialog');
      d.id = 'mt-aviso'; d.className = 'mt-aviso'; d.setAttribute('aria-labelledby', 'mt-aviso-titulo');
      d.innerHTML = '<form method="dialog"><h2 id="mt-aviso-titulo">Sair da partida?</h2><p id="mt-aviso-texto"></p>' +
        '<button class="mt-btn" value="ficar" autofocus>Continuar jogando</button>' +
        '<button class="mt-btn mt-btn-claro" value="sair">Sair mesmo assim</button></form>';
      document.body.appendChild(d);
      d.addEventListener('close', function () { if (d.returnValue === 'sair') location.href = d.dataset.destino; });
    }
    d.querySelector('#mt-aviso-texto').textContent = msg;
    d.dataset.destino = destino; d.returnValue = '';
    if (typeof d.showModal === 'function') d.showModal(); else if (window.confirm && confirm(msg)) location.href = destino;
  }
  document.addEventListener('click', function (e) {
    var a = e.target.closest && e.target.closest('a[data-mt-home]');
    if (!a || e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey) return;
    var msg = null;
    try { msg = typeof window.matutarSaida === 'function' ? window.matutarSaida() : null; } catch (x) { msg = null; }
    if (!msg) return;
    e.preventDefault();
    aviso(msg, a.href);
  });
  window.MatutarUI = { home: HOME, versao: '1.0.0' };
})();

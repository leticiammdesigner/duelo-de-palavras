/**
 * Matutar Games · medição de uso.
 *
 * Conta quantas pessoas chegam, quantas começam a jogar, quantas terminam e quantas
 * compartilham. Serve para saber onde as pessoas param, não quem são elas.
 *
 * GoatCounter: sem cookie, sem identificador que persista, sem dado pessoal. Por isso o site
 * não precisa de aviso de consentimento, só da linha de transparência no rodapé do hub.
 *
 * Duas decisões que valem ler antes de mexer:
 *
 * 1. Só o endereço oficial conta. Em prévia do Netlify, em localhost e em qualquer outro host,
 *    window.medir existe mas não faz nada, e o script do GoatCounter nem é baixado. Sem isso o
 *    número nasce sujo, misturando visita de verdade com teste nosso.
 *
 * 2. Os eventos usam no_session, então cada ocorrência conta. Quem joga três partidas aparece
 *    como três. É o que torna "começou" e "terminou" comparáveis entre si. A visita à página
 *    continua contando uma vez por sessão, que é o padrão do GoatCounter.
 *
 * Uso:  medir('duelo-termina')
 * O nome do evento é o que aparece no painel, então vale ser literal: jogo primeiro, ação depois.
 */
(function () {
  'use strict';

  var CODIGO = 'maturar';                 // a conta no GoatCounter
  var CASA = 'matutargames.com.br';       // qualquer outro host não conta

  // Em prévia, local ou qualquer host que não seja o oficial, medir vira um nada que não quebra
  // nenhuma chamada espalhada pelos jogos.
  window.medir = function () {};
  if (location.hostname !== CASA) return;

  // Chamadas que chegam antes do script do GoatCounter terminar de carregar esperam aqui. O teto
  // existe porque, se um bloqueador barrar o script, a fila nunca é esvaziada.
  var fila = [];
  var TETO = 20;

  function enviar(nome) {
    window.goatcounter.count({ path: nome, title: nome, event: true, no_session: true });
  }

  window.medir = function (nome) {
    if (!nome) return;
    if (window.goatcounter && window.goatcounter.count) enviar(nome);
    else if (fila.length < TETO) fila.push(nome);
  };

  var s = document.createElement('script');
  s.async = true;
  s.src = '//gc.zgo.at/count.js';
  s.setAttribute('data-goatcounter', 'https://' + CODIGO + '.goatcounter.com/count');
  s.onload = function () {
    var presos = fila;
    fila = [];
    for (var i = 0; i < presos.length; i++) enviar(presos[i]);
  };
  document.head.appendChild(s);
})();

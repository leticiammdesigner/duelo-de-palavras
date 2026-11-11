/* Motor do Duelo de Palavras no navegador.
 * Porte de confronto.py (motor lexical v0.4, congelado). Toda decisão de língua vem pré-calculada
 * pelo motor Python nos arquivos dados/<pista>.json; aqui só se consulta o índice e se resolve o
 * confronto (emparelhamento com prioridade temporal), exatamente como em confronto.py.
 */
(function (raiz) {
  'use strict';
  var MIN_LETRAS = 3;
  var LETRAS = /^[A-Za-z\u00C0-\u00FF]+$/;   // mesmo intervalo de confronto.py ([A-Za-zÀ-ÿ])

  function sa(w) { return w.normalize('NFD').replace(/\p{Mn}/gu, '').normalize('NFC'); }
  function pontos(forma) {
    var n = sa(forma).length;
    return n <= 3 ? 1 : n <= 5 ? 3 : n <= 7 ? 5 : 8;
  }

  // ---------- filtro de existência (Bloom), espelho de exportar.py ----------
  function Existe(bits, meta) { this.bits = bits; this.m = meta.m; this.k = meta.k; }
  Existe.prototype.tem = async function (s) {
    var h = new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(s)));
    var a = (h[0] | h[1] << 8 | h[2] << 16 | h[3] << 24) >>> 0;
    var b = ((h[4] | h[5] << 8 | h[6] << 16 | h[7] << 24) | 1) >>> 0;
    for (var i = 0; i < this.k; i++) {
      var x = Number((BigInt(a) + BigInt(i) * BigInt(b)) % BigInt(this.m));
      if (!(this.bits[x >> 3] & (1 << (x & 7)))) return false;
    }
    return true;
  };

  // ---------- leituras de uma entrada numa pista ----------
  // retorna lista ordenada [[familia, forma], ...] (preferência: mais usada primeiro) ou null
  function leituras(pista, norm) {
    var k = sa(norm), e = pista.idx[k];
    if (!e) return null;
    if (norm !== k) { var ac = e[1] && e[1][norm]; return ac && ac.length ? ac : null; }
    return e[0] && e[0].length ? e[0] : null;
  }

  // ---------- pré-validação, independente do adversário ----------
  // existe(texto) -> boolean síncrono (consulta já resolvida) usado só para escolher a mensagem
  function pre(jogador, idx, t, texto, pista, vistas, existe) {
    var tx = texto.trim(), norm = tx.toLowerCase(), sem = sa(norm);
    var base = { jogador: jogador, idx: idx, t: t, digitado: tx };
    if (!LETRAS.test(tx) || sem.length < MIN_LETRAS) return Object.assign(base, { status: 'Não permitida' });
    if (vistas.has(norm)) return Object.assign(base, { status: 'Já usada', motivo: 'mesma entrada digitada de novo' });
    vistas.add(norm);
    var lei = leituras(pista, norm);
    if (!lei) {
      var ex = existe ? existe(norm) : false;
      return Object.assign(base, { status: ex ? 'Fora da pista' : 'Não encontrada' });
    }
    return Object.assign(base, { status: null, norm: norm, leituras: lei });
  }

  function ordem(a, b) {
    if (a.t !== b.t) return a.t - b.t;
    if (a.jogador !== b.jogador) return a.jogador < b.jogador ? -1 : 1;
    if (a.digitado !== b.digitado) return a.digitado < b.digitado ? -1 : 1;
    return a.idx - b.idx;
  }
  // Python ordena strings por ponto de código; JS compara por unidade UTF-16. Para o português
  // (tudo no plano básico) as duas ordens coincidem.

  function Emparelhamento() { this.dono = new Map(); this.ent = []; }
  Emparelhamento.prototype._aum = function (i, visto) {
    var ch = this.ent[i]._chaves;
    for (var j = 0; j < ch.length; j++) {
      var k = ch[j];
      if (visto.has(k)) continue;
      visto.add(k);
      if (!this.dono.has(k) || this._aum(this.dono.get(k), visto)) { this.dono.set(k, i); return true; }
    }
    return false;
  };
  Emparelhamento.prototype.add = function (e) { this.ent.push(e); return this._aum(this.ent.length - 1, new Set()); };

  function _resolver(partidas, pista, existe) {
    var todas = [];
    Object.keys(partidas).forEach(function (j) {
      var vistas = new Set();
      var seq = partidas[j].slice().sort(function (a, b) {
        return a[0] - b[0] || (a[1] < b[1] ? -1 : a[1] > b[1] ? 1 : 0);
      });
      seq.forEach(function (x, idx) { todas.push(pre(j, idx, x[0], x[1], pista, vistas, existe)); });
    });
    var validas = todas.filter(function (e) { return e.status === null; });
    validas.forEach(function (e) { e._chaves = e.leituras.map(function (l) { return l[0]; }); });
    // empate exato de tempo entre jogadores
    var porT = new Map();
    validas.forEach(function (e) { if (!porT.has(e.t)) porT.set(e.t, []); porT.get(e.t).push(e); });
    porT.forEach(function (g) {
      g.forEach(function (a) {
        g.forEach(function (b) {
          if (a.jogador < b.jogador) {
            var comum = a._chaves.filter(function (k) { return b._chaves.indexOf(k) >= 0; });
            if (comum.length) {
              a._chaves = a._chaves.filter(function (k) { return comum.indexOf(k) < 0; });
              b._chaves = b._chaves.filter(function (k) { return comum.indexOf(k) < 0; });
              a._empate = (a._empate || []).concat(comum); b._empate = (b._empate || []).concat(comum);
            }
          }
        });
      });
    });
    var m = new Emparelhamento();
    validas.slice().sort(ordem).forEach(function (e) {
      e.status = e._chaves.length ? (m.add(e) ? 'Aceita' : 'Recusada') : 'Empate';
    });
    m.dono.forEach(function (i, k) {
      var e = m.ent[i];
      var l = e.leituras.find(function (x) { return x[0] === k; });
      e.identidade = k; e.leitura = l[1]; e.pontos = pontos(l[1]);
    });
    return { todas: todas, m: m };
  }

  function culpado(e, dono) {
    var fila = e.leituras.map(function (l) { return [l[0], null]; }).sort(cmpPrimeiro), visto = new Set();
    while (fila.length) {
      var par = fila.shift(), k = par[0], via = par[1];
      if (visto.has(k) || !dono.has(k)) continue;
      visto.add(k);
      var d = dono.get(k);
      if (d.jogador !== e.jogador) return [d, via];
      fila = fila.concat(d.leituras.map(function (l) { return [l[0], via || d]; }).sort(cmpPrimeiro));
    }
    return [null, null];
  }
  function cmpPrimeiro(a, b) { return a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0; }

  // mesmo arredondamento do Python (f"{t/1000:.1f}"): empate exato (x,25 e x,75) vai para o par
  function seg(t) {
    var r = t % 1000;
    if (r === 250 || r === 750) { var d = Math.floor(t / 100); if (d % 2) d += 1; return (d / 10).toFixed(1); }
    return (t / 1000).toFixed(1);
  }

  // partidas: {jogador: [[t_ms, texto], ...]}; existe: função síncrona (opcional)
  function resolver(partidas, pista, existe) {
    var r = _resolver(partidas, pista, existe);
    var donoG = new Map();
    r.m.dono.forEach(function (i, k) { donoG.set(k, r.m.ent[i]); });
    var solo = {};
    Object.keys(partidas).forEach(function (j) {
      var p = {}; p[j] = partidas[j];
      var s = _resolver(p, pista, existe), mapa = new Map();
      s.todas.forEach(function (e) { mapa.set(e.t + '|' + e.digitado, e.status); });
      solo[j] = mapa;
    });
    r.todas.forEach(function (e) {
      if (e.status !== 'Recusada') return;
      if (solo[e.jogador].get(e.t + '|' + e.digitado) === 'Aceita') {
        e.status = 'Bloqueada';
        var c = culpado(e, donoG), d = c[0], via = c[1];
        e.bloqueadoPor = d;
        e.motivo = d.leitura + ' é de ' + d.jogador + ' (' + d.digitado + ' aos ' + seg(d.t) + ' s)';
        if (via) e.motivo += '; sua entrada ' + via.digitado + ' ficou com ' + via.leitura + ' por isso';
      } else {
        e.status = 'Já usada';
        var donos = e.leituras.map(function (l) { return l[0]; }).sort()
          .filter(function (k) { return donoG.has(k); }).map(function (k) { return donoG.get(k).digitado; });
        e.motivo = 'mesma palavra que ' + Array.from(new Set(donos)).sort().join(', ');
      }
    });
    var entradas = r.todas.slice().sort(ordem);
    var placar = {};
    Object.keys(partidas).forEach(function (j) { placar[j] = 0; });
    entradas.forEach(function (e) { if (e.status === 'Aceita') placar[e.jogador] += e.pontos; });
    return { entradas: entradas, placar: placar };
  }

  var api = { sa: sa, pontos: pontos, leituras: leituras, resolver: resolver, Existe: Existe, MIN_LETRAS: MIN_LETRAS };
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else raiz.Motor = api;
})(this);

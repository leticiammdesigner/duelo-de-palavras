/* Armazenamento do Duelo do Dia.
 *
 * Duas implementações com a MESMA interface; o jogo não sabe qual está usando:
 *   - Supabase: o banco real. Escolhido quando config.js traz supabaseUrl e supabaseKey.
 *   - Teste: só no navegador (localStorage), com participantes simulados. Serve para ver a
 *     experiência dentro do Claude, que bloqueia conexões com sites de fora. Imita as regras do
 *     banco (uma tentativa, ordem das rodadas, prazo, teto de pontos), mas não protege nada.
 *
 * Interface (todas devolvem Promise):
 *   hoje()                         -> {duelo: {data, numero, pistas, versao_dados, versao_motor} | null, partida | null, agora}
 *   iniciar(apelido)               -> partida   (cria ou devolve a tentativa de hoje)
 *   comecarRodada(id, k)           -> partida   (marca o início da rodada k no relógio do servidor)
 *   salvarRodada(id, k, entradas, pontos) -> partida   (entradas = [{t, w}])
 *   concluir(id)                   -> partida   (o total é a soma das rodadas salvas)
 *   resumo(data)                   -> {participantes, media, minimo_percentil, acima_de, simulados?}
 * partida = {id, data, apelido, status, rodada_atual, rodada_inicio, rodadas, pontos_rodadas,
 *            pontos, pontos_status, prazo, agora}
 * Erros chegam como Error com .codigo (ex.: 'partida_expirada', 'rodada_fora_de_ordem').
 */
(function (raiz) {
  'use strict';

  function erro(codigo, msg) { var e = new Error(msg || codigo); e.codigo = codigo; return e; }
  function hojeBrasilia(agora) {
    // AAAA-MM-DD no fuso de São Paulo
    var p = new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Sao_Paulo', year: 'numeric', month: '2-digit', day: '2-digit' })
      .formatToParts(agora || new Date());
    var g = function (t) { return p.find(function (x) { return x.type === t; }).value; };
    return g('year') + '-' + g('month') + '-' + g('day');
  }

  // ------------------------------------------------------------------ Supabase
  var SUPABASE_JS = 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.45.4/dist/umd/supabase.js';
  function carregarScript(src) {
    return new Promise(function (ok, falha) {
      var s = document.createElement('script'); s.src = src; s.async = true;
      s.onload = ok; s.onerror = function () { falha(erro('sem_conexao', 'não carregou ' + src)); };
      document.head.appendChild(s);
    });
  }
  function Supabase(cfg) {
    this.tipo = 'supabase';
    var self = this;
    this._pronto = (raiz.supabase ? Promise.resolve() : carregarScript(SUPABASE_JS)).then(async function () {
      self.cli = raiz.supabase.createClient(cfg.supabaseUrl, cfg.supabaseKey, { auth: { persistSession: true, autoRefreshToken: true } });
      var s = await self.cli.auth.getSession();
      if (!s.data.session) {
        var r = await self.cli.auth.signInAnonymously();      // login anônimo: identidade estável neste navegador
        if (r.error) throw erro('sem_sessao', r.error.message);
      }
    });
  }
  Supabase.prototype._rpc = async function (nome, args) {
    await this._pronto;
    var r = await this.cli.rpc(nome, args || {});
    if (r.error) {
      var m = /([a-z_]+)$/.exec(String(r.error.message || '').trim());
      throw erro(m ? m[1] : 'falha', r.error.message);
    }
    return r.data;
  };
  Supabase.prototype.hoje = function () { return this._rpc('duelo_hoje'); };
  Supabase.prototype.iniciar = function (apelido) { return this._rpc('iniciar_duelo', { p_apelido: apelido || null }); };
  Supabase.prototype.comecarRodada = function (id, k) { return this._rpc('comecar_rodada', { p_partida: id, p_rodada: k }); };
  Supabase.prototype.salvarRodada = function (id, k, entradas, pontos) {
    return this._rpc('salvar_rodada', { p_partida: id, p_rodada: k, p_entradas: entradas, p_pontos: pontos });
  };
  Supabase.prototype.concluir = function (id) { return this._rpc('concluir_duelo', { p_partida: id }); };
  Supabase.prototype.resumo = function (data) { return this._rpc('resumo_dia', { p_data: data }); };

  // ------------------------------------------------------------------ Teste (navegador)
  var CHAVE = 'duelo-dia-teste-v1';
  var JANELA_MIN = 15, MINIMO_PERCENTIL = 20, RODADA_MS = 60000;
  function Teste(opcoes) {
    this.tipo = 'teste';
    this.simulados = opcoes && opcoes.simulados != null ? opcoes.simulados : 40;
    this._duelos = null;
    this._base = (opcoes && opcoes.base) || 'dados/';
  }
  Teste.prototype._ler = function () { try { return JSON.parse(localStorage.getItem(CHAVE)) || {}; } catch (e) { return this._mem || {}; } };
  Teste.prototype._gravar = function (s) { this._mem = s; try { localStorage.setItem(CHAVE, JSON.stringify(s)); } catch (e) {} };
  Teste.prototype._duelo = async function () {
    if (!this._duelos) {
      var r = await fetch(this._base + 'duelos.json');
      if (!r.ok) throw erro('sem_conexao', 'duelos.json ' + r.status);
      this._duelos = (await r.json()).duelos;
    }
    var d = hojeBrasilia();
    return this._duelos.find(function (x) { return x.data === d; }) || null;
  };
  Teste.prototype._publica = function (p) {
    var c = JSON.parse(JSON.stringify(p)); c.agora = new Date().toISOString(); return c;
  };
  Teste.prototype._minha = function (s, data) {
    var p = s.partidas && s.partidas[data];
    if (p && p.status === 'iniciada' && Date.now() > Date.parse(p.prazo)) { p.status = 'expirada'; this._gravar(s); }
    return p || null;
  };
  Teste.prototype.hoje = async function () {
    var d = await this._duelo(), s = this._ler();
    return { duelo: d, partida: d ? (this._minha(s, d.data) ? this._publica(this._minha(s, d.data)) : null) : null, agora: new Date().toISOString() };
  };
  Teste.prototype.iniciar = async function (apelido) {
    var d = await this._duelo(); if (!d) throw erro('sem_duelo_hoje');
    var s = this._ler(); s.partidas = s.partidas || {};
    if (!s.partidas[d.data]) {
      s.partidas[d.data] = { id: 'teste-' + d.data, data: d.data, apelido: apelido || null, status: 'iniciada', rodada_atual: 0,
        rodada_inicio: null, rodadas: [], pontos_rodadas: [], pontos: null, pontos_status: 'provisoria',
        iniciada_em: new Date().toISOString(), prazo: new Date(Date.now() + JANELA_MIN * 60000).toISOString(), concluida_em: null };
      this._gravar(s);
    }
    return this._publica(this._minha(s, d.data));
  };
  Teste.prototype._propria = function (id) {
    var s = this._ler(), data = String(id).replace('teste-', ''), p = this._minha(s, data);
    if (!p || p.id !== id) throw erro('partida_nao_encontrada');
    return { s: s, p: p };
  };
  Teste.prototype.comecarRodada = async function (id, k) {
    var x = this._propria(id), p = x.p;
    if (p.status !== 'iniciada') throw erro('partida_' + p.status);
    if (k !== p.rodada_atual) throw erro('rodada_fora_de_ordem');
    if (!p.rodada_inicio) { p.rodada_inicio = new Date().toISOString(); this._gravar(x.s); }
    return this._publica(p);
  };
  Teste.prototype.salvarRodada = async function (id, k, entradas, pontos) {
    var x = this._propria(id), p = x.p;
    if (p.status !== 'iniciada') throw erro('partida_' + p.status);
    if (k !== p.rodada_atual || !p.rodada_inicio) throw erro('rodada_fora_de_ordem');
    var teto = 0;
    entradas.forEach(function (e) {
      if (typeof e.t !== 'number' || e.t < 0 || e.t > RODADA_MS || typeof e.w !== 'string' || !e.w.length || e.w.length > 40) throw erro('entradas_invalidas');
      var n = e.w.length; teto += n <= 3 ? 1 : n <= 5 ? 3 : n <= 7 ? 5 : 8;
    });
    if (pontos < 0 || pontos > teto) throw erro('pontos_invalidos');
    p.rodadas.push(entradas); p.pontos_rodadas.push(pontos); p.rodada_atual++; p.rodada_inicio = null;
    this._gravar(x.s);
    return this._publica(p);
  };
  Teste.prototype.concluir = async function (id) {
    var x = this._propria(id), p = x.p;
    if (p.status === 'concluida') return this._publica(p);
    if (p.rodada_atual !== 4) throw erro('rodadas_incompletas');
    p.status = 'concluida'; p.concluida_em = new Date().toISOString();
    p.pontos = p.pontos_rodadas.reduce(function (a, b) { return a + b; }, 0);
    this._gravar(x.s);
    return this._publica(p);
  };
  // Participantes simulados, sempre os mesmos para a data (marcados como simulados).
  Teste.prototype._simulados = function (data) {
    var seed = 0; for (var i = 0; i < data.length; i++) seed = (seed * 31 + data.charCodeAt(i)) | 0;
    var r = function () { seed = (seed + 0x6D2B79F5) | 0; var t = Math.imul(seed ^ seed >>> 15, 1 | seed);
      t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
    var xs = [];
    for (var k = 0; k < this.simulados; k++) xs.push(Math.max(4, Math.round(70 + (r() + r() + r() - 1.5) * 70)));
    return xs;
  };
  Teste.prototype.resumo = async function (data) {
    var s = this._ler(), p = this._minha(s, data), outros = this._simulados(data);
    var meus = p && p.status === 'concluida' ? [p.pontos] : [];
    var todos = outros.concat(meus), total = todos.length;
    var media = total ? Math.round(10 * todos.reduce(function (a, b) { return a + b; }, 0) / total) / 10 : null;
    var acima = null;
    if (meus.length && total >= MINIMO_PERCENTIL && total > 1)
      acima = Math.round(100 * outros.filter(function (x) { return x < meus[0]; }).length / (total - 1));
    return { participantes: total, media: media, minimo_percentil: MINIMO_PERCENTIL, acima_de: acima, simulados: outros.length };
  };
  // Só no modo de teste: apagar a tentativa de hoje para jogar de novo.
  Teste.prototype.apagarHoje = async function () {
    var d = await this._duelo(), s = this._ler();
    if (d && s.partidas) { delete s.partidas[d.data]; this._gravar(s); }
  };

  function criar(cfg, opcoes) {
    cfg = cfg || {};
    if (cfg.supabaseUrl && cfg.supabaseKey) return new Supabase(cfg);
    return new Teste(opcoes);
  }

  raiz.Armazenamento = { criar: criar, hojeBrasilia: hojeBrasilia };
})(this);

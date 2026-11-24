/* Mede quanto o adversário simulado pontua, por nível e por número de rodadas.
 *
 * Lê o gerarRival, os perfis e o catálogo do próprio index.html, e pontua com o motor do jogo.
 * Nada é reimplementado aqui: se o jogo mudar, a medição acompanha.
 *
 * O rival joga sozinho, sem humano disputando palavra. Serve para calibrar a força dele, não
 * para prever o placar de uma partida real, onde os dois bloqueiam palavras um do outro.
 *
 * Uso:  node testes/simular-rival.js [quantas partidas por cenário]
 *
 * Os números de 24/11/2026 estão registrados no comentário de RIVAIS, no index.html.
 */
const fs = require('fs'), path = require('path');
const RAIZ = path.dirname(__dirname);
const M = require(path.join(RAIZ, 'motor.js'));

const html = fs.readFileSync(path.join(RAIZ, 'index.html'), 'utf8');
const trecho = (marca) => { const i = html.indexOf(marca); return html.slice(i, html.indexOf('\n}', i) + 2); };
const RIVAIS = eval('(' + html.slice(html.indexOf('var RIVAIS = {') + 'var RIVAIS = '.length,
                                     html.indexOf('};', html.indexOf('var RIVAIS = {')) + 1) + ')');
const CATALOGO = eval(html.slice(html.indexOf('var CATALOGO = [') + 'var CATALOGO = '.length,
                                 html.indexOf('];', html.indexOf('var CATALOGO = [')) + 1));
eval(trecho('function gerarRival'));
eval('function entre(r, a, b) { return a + Math.floor(r() * (b - a + 1)); }');
eval('function embaralhar(r, xs) { xs = xs.slice(); for (var i = xs.length - 1; i > 0; i--) { var j = Math.floor(r() * (i + 1)); var t = xs[i]; xs[i] = xs[j]; xs[j] = t; } return xs; }');

const POOL = { facil: [], medio: [], dificil: [] };
CATALOGO.forEach(x => POOL[x[2]].push(x[0]));
const pistas = {};
for (const id of new Set(CATALOGO.map(x => x[0]))) {
  const f = path.join(RAIZ, 'dados', id + '.json');
  if (fs.existsSync(f)) pistas[id] = JSON.parse(fs.readFileSync(f, 'utf8'));
}
// o rival só joga palavras do próprio pool da pista, então todas existem
const existe = () => true;

function umaPartida(nivel, rodadas, r, ajuste) {
  const perfil = Object.assign({}, RIVAIS[nivel]);
  if (ajuste) perfil.n = [Math.max(1, Math.round(perfil.n[0] * ajuste)), Math.max(1, Math.round(perfil.n[1] * ajuste))];
  const ids = embaralhar(r, POOL[nivel].filter(id => pistas[id])).slice(0, rodadas);
  let total = 0, porRodada = [];
  for (const id of ids) {
    const seq = gerarRival(pistas[id], perfil, r);
    const res = M.resolver({ rival: seq, 'Você': [] }, pistas[id], existe);
    const p = res.placar.rival || 0;
    total += p; porRodada.push(p);
  }
  return { total, porRodada };
}

function rng(semente) { let s = semente >>> 0; return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; }; }
function stats(xs) {
  const o = xs.slice().sort((a, b) => a - b), n = o.length;
  const q = p => o[Math.min(n - 1, Math.floor(p * n))];
  return { media: xs.reduce((a, b) => a + b, 0) / n, mediana: q(.5), p10: q(.1), p90: q(.9), min: o[0], max: o[n - 1] };
}

const N = Number(process.argv[2] || 500);
console.log('Pontos do adversário simulado · ' + N + ' partidas por cenário\n');
for (const rodadas of [4, 3]) {
  console.log('--- ' + rodadas + ' rodadas ' + (rodadas === 3 ? '(como ficou)' : '(como era)'));
  for (const nivel of ['facil', 'medio', 'dificil']) {
    const xs = Array.from({ length: N }, (_, i) => umaPartida(nivel, rodadas, rng(i * 7919 + rodadas), null).total);
    const s = stats(xs);
    console.log('  ' + (RIVAIS[nivel].nome + ' (' + nivel + ')').padEnd(18) +
      'média ' + s.media.toFixed(0).padStart(4) + '   mediana ' + String(s.mediana).padStart(4) +
      '   faixa comum ' + String(s.p10).padStart(3) + ' a ' + String(s.p90).padStart(4) +
      '   extremos ' + s.min + ' a ' + s.max);
  }
  console.log();
}

// ---- o que explica a sensação de mais tensão ----
console.log('=== peso de uma rodada ruim no Médio ===');
for (const rodadas of [4, 3]) {
  const amostras = Array.from({ length: 2000 }, (_, i) => umaPartida('medio', rodadas, rng(i * 104729 + rodadas), null));
  const porRodada = amostras.flatMap(a => a.porRodada);
  const sR = stats(porRodada);
  const totais = amostras.map(a => a.total), sT = stats(totais);
  const dp = Math.sqrt(totais.reduce((a, b) => a + (b - sT.media) ** 2, 0) / totais.length);
  // quanto a pior rodada representa do total
  const pesoPior = amostras.map(a => Math.max(...a.porRodada.map(p => (sR.media - p))) / sT.media);
  console.log('  ' + rodadas + ' rodadas: ' + sT.media.toFixed(0) + ' pontos em média, ' +
    (sR.media).toFixed(0) + ' por rodada');
  console.log('      dispersão do total: ' + (100 * dp / sT.media).toFixed(1) + '% da média');
  console.log('      uma rodada vale ' + (100 / rodadas).toFixed(0) + '% da partida');
}

console.log('\n=== e se a Ana fosse amaciada no Médio ===');
console.log('  (ajuste no número de palavras que ela consegue por rodada)');
for (const aj of [1, .9, .85, .8, .75, .7]) {
  const xs = Array.from({ length: 1000 }, (_, i) => umaPartida('medio', 3, rng(i * 7919 + 3), aj === 1 ? null : aj).total);
  const s = stats(xs);
  const perfil = RIVAIS.medio;
  const n = aj === 1 ? perfil.n : [Math.round(perfil.n[0] * aj), Math.round(perfil.n[1] * aj)];
  console.log('  ' + (aj === 1 ? 'hoje        ' : ('×' + aj.toFixed(2) + '      ')) +
    ' palavras/rodada ' + JSON.stringify(n).padEnd(9) +
    '  média ' + s.media.toFixed(0).padStart(4) + '  mediana ' + String(s.mediana).padStart(4) +
    '  faixa comum ' + s.p10 + ' a ' + s.p90);
}

/* Configuração por ambiente.
 * - Dentro do Claude: deixe vazio. O Duelo do Dia usa o armazenamento de teste (só no navegador).
 * - No Netlify: preencha com a Project URL e a publishable key do Supabase. Elas são públicas por
 *   natureza; quem protege os dados são as regras de acesso do banco (001_duelo_do_dia.sql).
 *   Nunca coloque aqui a chave secreta (service role).
 */
window.DUELO_CONFIG = {
  supabaseUrl: '',
  supabaseKey: ''
};

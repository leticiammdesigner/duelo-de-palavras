# Duelo de Palavras · Matutar Games

Encontre palavras que seguem as pistas, some pontos e desafie outras pessoas.

Site estático, sem build. Netlify publica a raiz (`netlify.toml`).

- `index.html`: jogo (partida contra adversário simulado, identificado como tal, e Duelo do Dia).
- `motor.js`: porte do motor lexical v0.4. `dados/`: índices por pista, catálogo v0.5 e calendário de duelos.
- `armazenamento.js` + `config.js`: Duelo do Dia. Com `config.js` vazio, roda em **modo de teste** no navegador (marcado na tela, participantes simulados). Com a Project URL e a publishable key do Supabase, usa o banco real. Nunca colocar a chave secreta.
- Desafio por link só existe dentro do Claude (usa o armazenamento do artifact); fora dele, o bloco não aparece.

Origem: exportado do artifact "Duelo de Palavras" no Claude em 11/11/2026, com duas mudanças: link do jogo passa a ser o endereço publicado e o bloco de desafio por link some fora do Claude.

## Matutar UI
Este jogo usa uma cópia da Matutar UI **v1.0.0** (pasta `matutar-ui`, versão em `matutar-ui/VERSAO`). A fonte de verdade fica no repositório `matutar-games`. Ajustes só deste jogo vão em `duelo-matutar.css`.

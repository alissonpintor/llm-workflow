---
trigger: manual
description: Orquestra o planejamento completo até READY
---

Execute em sequência, com autores e reviewers em subsessões diferentes quando a ferramenta permitir:

1. `criar-prd.md` e perguntas ao usuário;
2. `revisar-prd.md`, com correção até aprovação;
3. `criar-techspec.md`;
4. `revisar-techspec.md`, com correção até aprovação;
5. `criar-uiux.md` quando aplicável;
6. `criar-tasks.md`, com aprovação high-level;
7. `validar-planejamento.md`.

Não implemente produto. Termine com `READY` ou bloqueios explícitos.

Uma subsessão filha recebe todos os caminhos e decisões necessários; não presuma que ela herda a conversa. O orquestrador centraliza os spawns, sem exigir filhos de filhos. Se não houver subsessão independente para review, informe a limitação e aguarde decisão humana.

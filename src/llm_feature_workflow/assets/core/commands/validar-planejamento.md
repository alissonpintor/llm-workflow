---
trigger: manual
description: Faz lint e review semântico antes de READY
---

1. Execute `llm-workflow validate . tasks/prd-[slug]`.
2. Faça review semântico da rastreabilidade `RF/NFR → DEC → task → TEST`.
3. Reprove contradição, placeholder, pergunta bloqueante, hipótese crítica sem spike, requisito sem task, task sem prova ou dependência inválida.
4. Escreva `reviews/planning-review.md`.
5. Somente se aprovado, altere `tasks.md` para `Status: READY` e `Gate de planejamento: APROVADO`.

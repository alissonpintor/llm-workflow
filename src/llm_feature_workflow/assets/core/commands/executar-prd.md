---
trigger: manual
description: Executa PRD READY com review por task e aceite integrado
---

Você é o orquestrador. Exija plano `READY`, validação documental verde e working tree sem alterações alheias. Prefira worktree dedicado e capture `PRD_BASE_SHA`.

Registre o baseline original e os resultados por task em `tasks/prd-[slug]/execution.md`. Ao retomar uma execução, preserve o `PRD_BASE_SHA` original: não o substitua pelo HEAD atual, pois isso esconderia tasks anteriores do aceite integrado. Valide reviews/commits antes de confiar em um checkbox marcado.

Use subsessões independentes para implementação e review; cada prompt contém pasta do projeto, task, comando a seguir, baseline e tentativa. Filhos não disparam outros filhos. Se o ambiente não permitir review independente, pare e informe a limitação em vez de simular independência.

Para cada task, em sequência de dependências:

1. capture `TASK_BASE_SHA`;
2. delegue `executar-task.md` sem commit/checkmark/versionamento;
3. delegue `executar-review.md` em subsessão independente;
4. em reprovação, corrija e repita por no máximo dois ciclos;
5. em `SPEC_GAP`, pause e devolva ao planejamento;
6. após aprovação, preencha evidências, marque `[x]`, faça commit atômico e confirme working tree limpo.

Depois da última task, execute `validar-entrega-prd.md` com o `PRD_BASE_SHA` original. Após aprovação, faça um único bump SemVer por aplicação cujo runtime mudou; docs/testes/tooling não exigem bump da aplicação. Execute gates completos, inclua `acceptance.md`/tracker no commit final, marque `DONE` e confirme working tree limpo.

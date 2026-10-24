# Executa PRD READY com review por task e aceite integrado

Você é o orquestrador. Exija plano `READY`, validação documental verde e working tree sem alterações alheias. Prefira worktree dedicado e capture `PRD_BASE_SHA`.

Registre o baseline original e os resultados por task em `tasks/prd-[slug]/execution.md`. Ao retomar uma execução, preserve o `PRD_BASE_SHA` original: não o substitua pelo HEAD atual, pois isso esconderia tasks anteriores do aceite integrado. Valide reviews/commits antes de confiar em um checkbox marcado.

Conduza implementação e review separadamente; delegação nativa é opcional. Cada entrega de contexto
contém pasta do projeto, task, documento a seguir, baseline e tentativa. Sem delegação, faça a
implementação na sessão atual e peça review humano ou outra sessão independente. Sem reviewer,
pare e registre o bloqueio em vez de simular independência. Sem execução local, peça ao usuário
os resultados dos gates e mantenha a validação pendente. Veja `.workflow/START.md`.

Para cada task, em sequência de dependências:

1. capture `TASK_BASE_SHA`;
2. conduza `executar-task.md` sem commit/checkmark/versionamento, com delegação somente se disponível e autorizada;
3. solicite `executar-review.md` em outra sessão independente ou a um reviewer humano;
4. em reprovação, corrija e repita por no máximo dois ciclos;
5. em `SPEC_GAP`, pause e devolva ao planejamento;
6. após aprovação, preencha evidências, marque `[x]`, faça commit atômico e confirme working tree limpo.

Depois da última task, execute `validar-entrega-prd.md` com o `PRD_BASE_SHA` original. Após aprovação, faça um único bump SemVer por aplicação cujo runtime mudou; docs/testes/tooling não exigem bump da aplicação. Execute gates completos, inclua `acceptance.md`/tracker no commit final, marque `DONE` e confirme working tree limpo.

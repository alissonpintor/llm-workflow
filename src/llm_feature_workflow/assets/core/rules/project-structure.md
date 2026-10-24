# Estrutura do workflow

- `.workflow/workflow.yaml` — fonte de verdade da configuração.
- `.workflow/workflow.lock` — versão, perfis e hashes gerados.
- `.workflow/START.md` — entrada portátil, índice de etapas, alternativas de capacidade e retomada.
- `.workflow/generated/` — artefatos canônicos gerados; não editar manualmente.
- `commands/`, `templates/` e diretórios opcionais dos agentes — cópias sincronizadas.
- `tasks/prd-<slug>/` — descoberta, PRD, avaliação de domínio, Tech Spec, UI/UX opcional, tasks, reviews e aceite.
- `docs/` e `MEMORY.md` — conhecimento durável do projeto.

Altere configuração/perfis e execute `llm-workflow sync`; não corrija apenas um espelho.

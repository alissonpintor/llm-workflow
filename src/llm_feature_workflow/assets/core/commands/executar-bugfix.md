---
trigger: manual
description: Diagnostica e corrige um bug com regressão testada e review independente
---

1. Reproduza o comportamento e registre esperado/observado, impacto e evidência.
2. Leia decisões, testes, rules e profile-context aplicáveis. Capture o SHA-base.
3. Localize a causa antes de editar; use hipóteses e experimentos pequenos.
4. Crie um teste que falha pela causa correta, corrija minimamente e execute gates/plugins aplicáveis.
5. Submeta o diff a review independente; preserve código alheio.
6. Após aprovação, registre evidências, documentação necessária e commit atômico.

Se o bug pertence a PRD em execução, siga seu gate de versão único. Em correção avulsa de runtime, incremente PATCH apenas após testes e review. Mudança ampla de requisito volta ao planejamento.

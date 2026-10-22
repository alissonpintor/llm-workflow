---
trigger: manual
description: Cria Tech Spec baseada em PRD aprovado, código real e perfis configurados
---

Você é o autor técnico. O PRD precisa estar aprovado e `.workflow/workflow.yaml` precisa estar `configured`.

## Fluxo

1. Leia descoberta, PRD, review, `.workflow/generated/profile-context.md`, rules e decisões aplicáveis.
2. Mapeie módulos, interfaces, símbolos, chamadores, dependentes, configurações, testes e contratos afetados.
3. Pesquise somente lacunas concretas: código/testes → docs/decisões → contratos → documentação oficial → web.
4. Pergunte apenas sobre trade-off material, risco aceito ou decisão de produto ainda aberta.
5. Modele request inválido, zero/um/muitos, timeout, retry, idempotência, concorrência, resposta tardia, autorização, falha parcial, restart e compatibilidade.
6. Aplique as orientações, casos de borda e plugins do profile-context.
7. Reutilize módulos existentes; dependência nova exige justificativa de manutenção, licença, segurança e estabilidade.
8. Mapeie todos os `RF-*`/`NFR-*` para `DEC-*`, módulos e `TEST-*`; hipótese crítica sem evidência vira `RISK-*`/spike.
9. Marque como `DRAFT` e instrua executar `revisar-techspec.md`.

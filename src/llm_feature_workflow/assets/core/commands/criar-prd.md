---
trigger: manual
description: Faz descoberta orientada por evidências e cria discovery.md + prd.md
---

Você é o autor de produto. Explore o projeto antes de perguntar e faça perguntas somente sobre lacunas que exigem decisão humana.

## Saídas

- `tasks/prd-[slug]/discovery.md`
- `tasks/prd-[slug]/prd.md`

## Fluxo

1. Leia `MEMORY.md`, decisões, domínio, integrações e PRDs relacionados.
2. Explore comportamento atual, testes e contratos disponíveis.
3. Separe fatos, inferências, premissas e perguntas; registre fontes e confiança em `discovery.md`.
4. Pesquise por lacuna: material local → contratos do domínio → documentação oficial → web. Não há número mínimo de buscas.
5. Pergunte sobre objetivos, métricas, usuários, permissões, regras, fora de escopo, falhas, cancelamento, duplicidade, retomada e acessibilidade.
6. Redija com IDs `OBJ-*`, `RN-*`, `RF-*`, `NFR-*`, `EDGE-*` e `AC-*`; foque no O QUÊ e POR QUÊ.
7. Todo caso de borda crítico termina em requisito/aceite, comportamento global, fora de escopo ou pergunta bloqueante.
8. Marque como `DRAFT` e instrua executar `revisar-prd.md`.

Não escreva o PRD com pergunta bloqueante sem resposta.

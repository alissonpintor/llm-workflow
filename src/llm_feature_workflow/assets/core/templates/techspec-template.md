# Especificação Técnica — [Nome da Funcionalidade]

## Estado do Documento

- Status: DRAFT
- PRD: `prd.md`
- Review do PRD: `reviews/prd-review.md`
- Perguntas técnicas bloqueantes: [quantidade]

## Resumo Executivo

[Abordagem, decisões e impactos principais.]

## Estado Atual e Análise de Impacto

- Fluxo atual:
- Módulos e interfaces:
- Chamadores/dependentes:
- Contratos afetados:
- Comportamentos preservados:

## Cobertura dos Requisitos

| Requisito | Decisão | Módulos/arquivos | Testes | Estado |
|---|---|---|---|---|
| RF-01 | DEC-01 | [módulos] | TEST-01 | coberto / pendente |

## Arquitetura da Solução

### Adequação de DDD

- Avaliação aprovada: `domain-assessment.md`
- Recomendação por módulo/área e evidências do usuário:
- Padrões escolhidos, problema concreto, benefícios e custos:
- Alternativa mais simples e motivo da decisão:
- Hipóteses/gatilhos de reavaliação:

### Visão Geral dos Módulos

| Módulo | Novo/modificado | Responsabilidade | Interface afetada |
|---|---|---|---|
| [módulo] | novo / modificado | [responsabilidade] | [interface] |

### Fluxo de Dados

[Descreva módulos internos, adaptadores externos e sequência de dados.]

## Design de Implementação

### Interfaces Principais

[Interface, invariantes, erros, ordenação e características que chamadores precisam conhecer.]

### Modelos de Dados

- Tipos e entidades:
- Entrada/saída:
- Persistência/cache:
- Compatibilidade:

### Contratos Externos

[Método/operação, autenticação, request, response, erros, idempotência, timeout/retry e versionamento.]

## Casos de Borda, Concorrência e Modos de Falha

| ID | Cenário | Comportamento | Responsável | Teste | Estado |
|---|---|---|---|---|---|
| EDGE-T01 | [cenário] | [resultado] | [módulo] | TEST-01 | definido / pendente |

Consulte `.workflow/generated/profile-context.md` para casos específicos da stack e plugins.

## Segurança e Privacidade

- Identidade/autenticação:
- Autorização:
- Validação e confiança dos dados:
- Segredos/logs:
- Ameaças relevantes:

## Estratégia de Testes

| ID | Nível | Cenário | Módulos | Dependências simuladas | Comando/gate |
|---|---|---|---|---|---|
| TEST-01 | unidade / integração / contrato / E2E | [cenário] | [módulos] | [simulações] | [gate] |

## Sequenciamento

1. [slice e motivo]
2. [slice e dependência]

## Migração, Rollout e Rollback

- Compatibilidade:
- Migração:
- Ordem de deploy:
- Rollback:
- Condição de aborto:

## Observabilidade

- Infraestrutura existente:
- Logs:
- Métricas:
- Correlação:
- Dados proibidos:

## Decisões Técnicas

### DEC-01 — [decisão]

- Contexto:
- Decisão:
- Alternativas:
- Consequências:
- Evidência:
- Confiança: confirmada / inferida / precisa de spike

## Riscos e Spikes

| ID | Risco/hipótese | Probabilidade/impacto | Mitigação | Spike bloqueante? |
|---|---|---|---|---|
| RISK-01 | [risco] | [avaliação] | [ação] | sim / não |

## Conformidade com Perfis e Rules

| Rule/perfil | Seções | Aderência | Desvio |
|---|---|---|---|
| [referência] | [seção] | [como atende] | nenhum / justificativa |

## Arquivos e Símbolos Relevantes

| Arquivo | Existente/novo | Símbolos | Alteração |
|---|---|---|---|
| [caminho] | existente / novo | [símbolos] | [impacto] |

## Perguntas Técnicas Abertas

| ID | Pergunta | Evidência necessária | Bloqueia? | Estado |
|---|---|---|---|---|
| TQ-01 | [pergunta] | [fonte/spike] | sim / não | pendente / respondida |

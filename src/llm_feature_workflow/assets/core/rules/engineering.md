# Engenharia de software — base independente de stack

## Modularidade e SOLID contextual

- Organize cada módulo por responsabilidade e motivo de mudança; se alterações não relacionadas sempre exigirem editar o mesmo módulo, reveja o limite.
- Mantenha interfaces pequenas e coesas para seus consumidores. Não crie uma interface para cada classe nem camadas que apenas repassam chamadas.
- Receba dependências externas nas fronteiras testáveis; regras de negócio não devem precisar conhecer detalhes HTTP, arquivos, bancos ou SDKs para expressar invariantes.
- Ao substituir uma implementação, preserve contrato, erros e invariantes observados pelos chamadores. Teste esse contrato, não apenas a implementação isolada.
- Estenda comportamento por composição quando existir variação real. Não antecipe pontos de extensão para requisitos imaginários.

## Clean Code e tratamento de erros

- Use nomes do domínio e tipos que tornem estados inválidos difíceis de representar; não codifique vários significados em flags, strings mágicas ou números sentinela sem contrato.
- Funções devem realizar uma operação coesa, com entradas, saída e efeitos observáveis claros. Não imponha um limite de linhas arbitrário no lugar de coesão.
- Valide dados externos na entrada; diferencie DTOs externos e modelos internos quando suas responsabilidades divergirem.
- Torne falhas explícitas. Não use catch vazio, retorno de sucesso em exceção ou defaults que escondam dados obrigatórios ausentes.
- Comentários explicam decisões e limitações não óbvias. Remova código morto, debug temporário e abstrações redundantes, preservando trabalho fora do escopo.

## Design Patterns sem complexidade artificial

- Use Adapter para isolar contratos externos diferentes, Strategy para algoritmos realmente intercambiáveis e Factory quando a construção tiver variação relevante.
- Antes de introduzir um padrão, registre o problema concreto, o ganho para chamadores e a alternativa mais simples.
- Evite singleton com estado compartilhado mutável, service locator oculto e repository genérico sem necessidade de domínio.

## DDD proporcional ao problema

- Mantenha vocabulário compartilhado em `docs/domain.md`; nomes de entidades, ações e estados devem refletir o negócio.
- Identifique ownership das invariantes e limites entre domínios. Não replique regra em UI, rota e persistência sem uma autoridade definida.
- Agregados, eventos de domínio, CQRS e múltiplas camadas exigem complexidade de negócio que os justifique. CRUD simples não precisa de toda a arquitetura tática de DDD.
- Organize por feature ou outro estilo aprovado no ADR; preserve a convenção real do framework quando não contrariar os limites acordados.

## Testabilidade e critérios de revisão

- Testes exercitam comportamento e invariantes pela mesma interface usada pelos chamadores; evite mocks de todos os detalhes internos.
- Cubra caminho principal, falhas, limites, concorrência e regressões relevantes. Relate testes não executados em vez de declará-los verdes.
- Toda regra material nova precisa de exemplo, exceções e forma de verificação. Nomes de padrões e contagem de arquivos não demonstram qualidade.
- O review verifica dependências entre módulos, efeitos colaterais, contratos, manutenção e risco, não somente lint e cobertura.

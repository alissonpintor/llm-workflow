# Diagnóstico real do OpenRouter — 2026-10-24

Chamadas autorizadas pelo usuário, com contexto sintético de uma API e frontend. A chave foi
obtida do ambiente de usuário do Windows sem exibição ou persistência. Nenhum código, documento
ou configuração privada do projeto de teste foi enviado. Não foram gravados respostas brutas
nem raciocínio; o script temporário de diagnóstico foi removido após o uso.

## Observações

| Chamada | Modelo | Cenário | Tokens de saída / raciocínio | Resultado | Custo informado (USD) |
|---|---|---|---|---|---|
| 1 | DeepSeek V4 Flash | Contexto insuficiente, raciocínio padrão | 2080 / 1947 | Pergunta válida | 0.0002552004 |
| 2 | DeepSeek V4 Flash | Mesmo contexto, raciocínio desligado | 1828 / 0 | Rascunho com avaliação de domínio incompleta | 0.00016971864 |
| 3 | DeepSeek V4 Flash | Entrevista com contrato separado | 333 / 0 | Perguntas válidas, sem rascunhos | 0.0001218945 |
| 4 | DeepSeek V4 Flash | Contexto de produto ampliado | 2763 / 2258 | Mais perguntas | 0.0003380727 |
| 5 | DeepSeek V4 Flash | Respostas fornecidas, contrato ainda ambíguo | 1737 / 1325 | Copiou respostas como perguntas, reutilizando IDs | 0.0002745519 |
| 6 | DeepSeek V4 Flash | Retomada com formato de proposta | 6314 / 4118 | Faltou categoria obrigatória; também havia citação não literal | 0.000644385 |
| 7 | DeepSeek V3.2 | Mesmo cenário de proposta | 3316 / 0 | Padrões referenciaram fontes BRIEF/Q-XX em vez de evidências E-XX | 0.003564998 |

Total informado: **USD 0.00536882114**, sem retries automáticos. Os custos são os retornados
pelo serviço, não uma auditoria independente de faturamento. As chamadas concluíram com `stop`;
o truncamento informado pelo usuário (`length`, 8000 tokens, 3922 de raciocínio) não foi reproduzido
exatamente. Não atribuímos a ele uma causa diferente da evidência disponível.

## Causas e correções

- O raciocínio usa parte do limite de saída. Desligá-lo não garante conformidade do JSON.
- O contrato anterior permitia ao modelo gerar rascunhos extensos mesmo quando precisava perguntar.
  A entrevista agora usa um formato curto separado, convertido para uma proposta bloqueada.
- Na retomada, o modelo recebe o formato de proposta e não a alternativa curta de entrevista.
  Perguntas novas ainda bloqueiam aplicação; respostas copiadas com IDs antigos são rejeitadas.
- Categorias de regras deixaram de depender apenas de instruções/validadores: o contrato de rede
  exige seções design, security e testing, convertidas para a representação interna existente.
- Avaliações conclusivas exigem ao menos uma evidência no JSON Schema. Referências de padrões têm
  formato E-XX e o campo de citação recebe opções literais derivadas do contexto enviado.
- Validações locais continuam verificando relações entre IDs, cobertura, fonte da citação,
  adequação de padrões e preservação da configuração. Não foram relaxadas para aceitar saídas ruins.

As alterações finais de categorias/citações foram verificadas por testes automatizados, **não por
uma nova geração real completa**. Portanto, este diagnóstico não garante que todo modelo/provedor
produza uma proposta completa válida. Não ampliamos silenciosamente tokens, custo ou retries.

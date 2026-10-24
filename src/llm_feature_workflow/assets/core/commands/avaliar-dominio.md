# Avaliar domínio e adequação de DDD

Avalie cada módulo e área de negócio antes de recomendar padrões. Use o contexto explicitamente
fornecido: processos, regras que impedem operações, estados/transições, invariantes que precisam
permanecer consistentes e conceitos com significados diferentes entre áreas.

1. Identifique fontes do usuário: BRIEF e perguntas/respostas Q-XX. Cite literalmente a fonte,
   separe a observação da interpretação e não trate sugestões anteriores da LLM como fatos.
2. Compare design simples por funcionalidades, DDD estratégico e DDD tático seletivo. Quantidade
   de tabelas, linguagem/framework e tamanho do projeto não demonstram complexidade de negócio.
3. Quando faltar contexto material, faça perguntas bloqueantes. Não conclua que o sistema é CRUD
   apenas porque o brief descreve somente a stack. Não gere uma arquitetura definitiva nessa situação.
4. Para cada padrão candidato, justifique problema concreto, evidências, benefícios e custos.
   Compare com uma alternativa mais simples e registre quando reavaliar a decisão.
5. Use linguagem/contextos quando úteis e agregados/objetos de valor/eventos somente quando
   justificados pelas invariantes. DDD não implica microserviços, CQRS ou event sourcing.
6. Use `templates/domain-assessment-template.md` e registre `domain-assessment.md`
   na pasta da funcionalidade com escopo, recomendação, fontes,
   citações, hipóteses, padrões seletivos, alternativa e perguntas. Exija aprovação humana antes
   de incorporar a decisão na Tech Spec e nas regras. Sem aprovação, mantenha estado PROPOSTA.

Na geração assistida da CLI, `configure --ai` produz essa avaliação estruturada, `llm preview`
mostra os fundamentos e `llm apply --approve` incorpora a decisão nas regras. Não faça uma chamada
externa em nome do usuário sem consentimento separado de envio/custo.

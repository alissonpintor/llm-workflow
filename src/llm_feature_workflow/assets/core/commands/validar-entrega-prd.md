---
trigger: manual
description: Faz aceite integrado antes do release
---

Com todas as tasks aprovadas e commitadas, compare a entrega completa com RF/NFR/EDGE/AC, execute todos os gates configurados e plugins de aceite final, confirme documentação, segurança, operação e ausência de dívida bloqueante.

Use `PRD_BASE_SHA` para delimitar a entrega. Escreva `acceptance.md` com comandos/resultados e `Status: APROVADO` ou `REPROVADO`. O bump de versão ocorre depois deste aceite.

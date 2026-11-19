## ADR-002: Autenticação Stateless com JWT (HS256) e Validação em Duas Camadas

### Status
Aceito

### Contexto
O EventHub é composto por 7 serviços distribuídos (API Gateway, serviços SOA e microsserviços) que precisam autenticar usuários e aplicar controle de acesso baseado em papéis (`admin`, `organizador` e `participante`). Era necessário definir um mecanismo de autenticação que não exigisse sessões armazenadas em memória no servidor nem consultas constantes ao banco do Serviço de Identidade a cada requisição interna.

### Decisão
Adotar tokens JWT (JSON Web Token) assinados com o algoritmo simétrico **HS256**, utilizando a chave secreta compartilhada `JWT_SECRET` (mínimo de 32 caracteres) configurada via variável de ambiente em todos os serviços.

1. **Emissão:** realizada exclusivamente pelo Serviço de Identidade (`POST /auth/login`), gerando um token com validade de 24 horas contendo os campos `sub` (string), `nome`, `email`, `papel` e `exp`.
2. **Propagação:** o cliente envia o cabeçalho `Authorization: Bearer <token>` ao API Gateway, que o repassa intacto aos serviços de destino e nas chamadas internas entre serviços.
3. **Validação em duas camadas:**
   - **API Gateway:** verifica a presença, assinatura e expiração do token na entrada, bloqueando requisições inválidas com HTTP `401 Unauthorized`.
   - **Serviços internos:** validam a permissão do perfil (`papel`) por meio do decorator compartilhado `@requer_papel` (`comum/auth.py`), retornando HTTP `403 Forbidden` quando o perfil não tem autorização.

### Alternativas Consideradas
- **Sessão centralizada em banco ou cache (ex.: Redis):** descartada por adicionar estado ao API Gateway e exigir uma consulta de rede extra a cada requisição recebida.
- **Introspecção via chamada HTTP ao Serviço de Identidade:** descartada por criar um gargalo de desempenho e ponto único de falha na comunicação interna entre os microsserviços.
- **Assinatura assimétrica (RS256):** descartada por introduzir complexidade desnecessária de geração e rotação de pares de chaves pública/privada para o escopo do projeto.

### Consequências
- **Positivas:** Arquitetura totalmente *stateless*; o API Gateway permanece leve e sem banco de dados; serviços como o Orquestrador e o `ms-certificados` extraem `nome` e `email` diretamente do payload do token sem precisar consultar o Serviço de Identidade.
- **Negativas / Riscos:** **O token não pode ser revogado antes de expirar** — caso um usuário seja excluído ou tenha seu perfil alterado no banco `identidade.db`, ele continuará com acesso válido até o vencimento do timestamp `exp` (24 horas). Além disso, o vazamento da `JWT_SECRET` comprometeria a assinatura de todos os serviços simultaneamente.
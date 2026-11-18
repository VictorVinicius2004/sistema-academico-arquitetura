# Guia do Integrante 4: Orquestrador + Notificação

Roteiro de tudo que falta para completar a minha parte do EventHub. Marque `[x]` conforme for terminando.

**Minha responsabilidade:** os dois serviços da camada **SOA** que fazem o fluxo mais importante da avaliação, a **inscrição orquestrada**.

| Serviço      | Porta | O que faz                                                            |
| ------------ | ----- | -------------------------------------------------------------------- |
| Notificação  | 5002  | Recebe destinatário + mensagem, escreve no log e responde `201`      |
| Orquestrador | 5003  | Coordena a inscrição: evento → inscrição → notificação → confirmação |

---

## Visão geral das etapas

| #   | Etapa                                  | Depende de alguém?                  | Situação |
| --- | -------------------------------------- | ----------------------------------- | -------- |
| 0   | Preparar o ambiente                    | Não                                 | ✅ feito  |
| 1   | Notificação: versão simples            | Não                                 | ✅ feito  |
| 2   | Token / `auth.py`                      | Integrante 1 (ou versão provisória) | ✅ feito (Integrante 1) |
| 3   | Notificação completa (token + Swagger) | Etapa 2                             | ✅ feito  |
| 4   | Orquestrador em modo SIMULADO          | Etapa 2                             | ✅ feito  |
| 5   | Testes no Postman                      | Etapas 3 e 4                        | 🟡 testado no terminal, falta a coleção |
| 6   | Integração com os serviços reais       | Integrantes 2 e 3                   | ⬜        |
| 7   | Documentação + ADR-001                 | Não (pode adiantar a qualquer hora) | ⬜        |
| 8   | Diário de Uso de IA                    | Não (anotar durante, não no final)  | ⬜        |
| 9   | Preparar a apresentação                | Tudo acima                          | ⬜        |

### Prazos do grupo

| Quando           | O quê                                                                     |
| ---------------- | ------------------------------------------------------------------------- |
| Quarta de manhã  | Cada um termina e testa o próprio serviço isolado (etapas 2 a 5)          |
| **Quarta, ~14h** | **Integração em chamada**: `docker compose up` + fluxo completo (etapa 6) |
| Quarta à tarde   | Correções, documentação, ADR, Diário de IA (etapas 7 e 8)                 |
| **Quarta, 22h**  | **Código congelado**: ninguém mexe mais                                   |
| Quarta à noite   | Ensaio da apresentação, incluindo **derrubar a Notificação ao vivo**      |
| Quinta de manhã  | Entrega                                                                   |

> Se travar no código, adiante a documentação (etapa 7). Ela não depende de nada.

---

## Etapa 0: Ambiente ✅

- [x] Python 3 instalado
- [x] Ambiente virtual criado (`.venv`) com `flask`, `requests`, `pyjwt` e `flasgger`
- [x] Postman instalado

**Para ligar o ambiente toda vez que abrir um terminal novo:**

```fish
cd ~/Documentos/GitHub/sistema-academico-arquitetura
source .venv/bin/activate.fish
```

---

## Etapa 1: Notificação, versão simples ✅

- [x] `notificacao/app.py` com `GET /health` e `POST /notificacoes`
- [x] Testado no Postman: `201` com dados certos, `400` com `{}`

---

## Etapa 2: Token (o "crachá" JWT)

Todo pedido precisa de um **token** no cabeçalho `Authorization: Bearer <token>`. Quem confere o token é o decorator `@requer_papel(...)`, que fica em `comum/auth.py`. **Esse arquivo é do Integrante 1** e hoje está vazio.

- [x] Perguntar ao Integrante 1 se o `comum/auth.py` e o `scripts/gerar_token.py` já estão prontos e pedir que suba para o GitHub (subiu no commit `d4bc883`)
- [x] ~~**Se não estiverem:**~~ não foi preciso: fazer uma versão provisória seguindo exatamente o combinado (abaixo) e trocar pela dele depois
- [ ] Rodar `python scripts/gerar_token.py` e guardar os 3 tokens (admin, organizador, participante)

**Combinados que a versão provisória precisa respeitar:**

- Conteúdo do token: `{"sub", "nome", "email", "papel", "exp"}`
- `sub` é **texto** (`"3"`, não `3`), porque a PyJWT recusa número. Para comparar com o banco: `int(g.usuario["sub"])`
- Algoritmo **HS256**, chave na variável de ambiente `JWT_SECRET` (32 caracteres ou mais)
- Papéis em minúsculo: `admin`, `organizador`, `participante`
- Ids dos tokens de teste: admin = `"1"`, organizador = `"2"`, participante = `"3"`
- Sem token ou token inválido: `401`. Papel errado: `403`. Formato de erro: `{"erro": "mensagem"}`

---

## Etapa 3: Notificação completa

- [x] Proteger `POST /notificacoes` com `@requer_papel("admin", "organizador", "participante")`, ou seja, **qualquer usuário autenticado**
- [x] Adicionar o **Swagger** (contrato OpenAPI) com `flasgger`: documentar a rota, o corpo e as respostas `201`, `400` e `401`
- [x] Preencher `notificacao/requirements.txt`:

  ```
  Flask==3.1.0
  PyJWT==2.10.1
  flasgger==0.9.7.1
  ```
- [x] Conferir que a página do Swagger abre em `http://localhost:5002/apidocs`

**Regra de ouro (é SOA):** a Notificação **não pode saber** o que é "evento" ou "inscrição". Ela recebe só `destinatario` e `mensagem`. É isso que a torna reutilizável por qualquer outro serviço.

---

## Etapa 4: Orquestrador em modo SIMULADO

### O que ele faz

`POST /inscricoes`, só para **participante**, com o corpo `{"evento_id": 7}`.

```
1. GET  ms-eventos/eventos/7         → o evento existe? está aprovado?
2. POST ms-inscricoes/inscricoes     → grava {"evento_id": 7, "usuario_id": 3}
3. POST notificacao/notificacoes     → avisa o e-mail que veio no token
4. responde 201 com a confirmação
```

**Resposta de sucesso (`201`):**

```json
{ "inscricao_id": 15, "evento_id": 7, "status": "confirmada", "notificado": true }
```

### Tradução dos erros

| Situação                                   | Quem detecta                    | O Orquestrador responde                                   |
| ------------------------------------------ | ------------------------------- | --------------------------------------------------------- |
| Sem token / token inválido                 | `@requer_papel`                 | `401`                                                     |
| Organizador ou admin tentando se inscrever | `@requer_papel("participante")` | `403`                                                     |
| Faltou `evento_id` no corpo                | o próprio Orquestrador          | `400`                                                     |
| ms-eventos devolve `404`                   | passo 1                         | `404` `{"erro": "evento não encontrado"}`                 |
| Evento com `"status": "pendente"`          | passo 1                         | `400` `{"erro": "evento não aprovado"}`                   |
| ms-inscricoes devolve `409`                | passo 2                         | `409` `{"erro": "participante já inscrito neste evento"}` |
| Notificação fora do ar ou com erro         | passo 3                         | **`201` mesmo assim**, com `"notificado": false`          |
| ms-eventos ou ms-inscricoes fora do ar     | passos 1 e 2                    | `503` `{"erro": "serviço indisponível: ..."}`             |

> A falha da notificação **não desfaz** a inscrição: o aviso é secundário, o importante é a vaga garantida (ADR-004).

### Checklist do código

- [x] Endereços dos outros serviços em variáveis de ambiente, com padrão `localhost`:
  - `URL_EVENTOS` (padrão `http://localhost:5004`)
  - `URL_INSCRICOES` (padrão `http://localhost:5005`)
  - `URL_NOTIFICACAO` (padrão `http://localhost:5002`)
- [x] `SIMULADO = os.getenv("SIMULADO") == "1"`
- [x] Uma função para cada chamada: `buscar_evento()`, `criar_inscricao()` e `notificar()`
- [x] **Repassar o token** em todas as chamadas: `headers={"Authorization": request.headers["Authorization"]}`
- [x] Usar `timeout=3` nas chamadas, para não travar se um serviço estiver fora do ar
- [x] `notificar()` dentro de `try/except`: se der qualquer erro, `notificado = False`
- [x] `usuario_id` vem do token: `int(g.usuario["sub"])`. O e-mail também: `g.usuario["email"]`
- [x] Swagger documentando a rota e todas as respostas (`201`, `400`, `401`, `403`, `404`, `409`)
- [x] `GET /health`
- [x] Preencher `orquestrador/requirements.txt`:

  ```
  Flask==3.1.0
  PyJWT==2.10.1
  flasgger==0.9.7.1
  requests==2.32.3
  ```

### Respostas simuladas

As respostas fingidas precisam ser **cópia exata** do formato combinado, senão tudo quebra na integração:

```python
# GET /eventos/{id} (ms-eventos)
{"id": 7, "titulo": "Semana de SI", "descricao": "...", "data": "2026-12-01",
 "local": "Auditório", "status": "aprovado", "organizador_id": 2}

# POST /inscricoes (ms-inscricoes): resposta 201
{"id": 15, "evento_id": 7, "usuario_id": 3, "status": "ativa", "presente": False}
```

**Ideia para testar os erros sem editar o código toda hora:** o `evento_id` que você manda decide qual resposta simulada volta.

| `evento_id` enviado | Simulação devolve                  | Resultado esperado |
| ------------------- | ---------------------------------- | ------------------ |
| `7`                 | evento aprovado + inscrição criada | `201`              |
| `999`               | evento não encontrado              | `404`              |
| `8`                 | evento com `"status": "pendente"`  | `400`              |
| `9`                 | ms-inscricoes responde `409`       | `409`              |

A Notificação **não** precisa ser simulada: ela é sua e já funciona. Para testar o `"notificado": false`, basta desligá-la (Ctrl+C no terminal dela).

**Como rodar o Orquestrador simulado (fish):**

```fish
env SIMULADO=1 python orquestrador/app.py
```

Não precisa passar `JWT_SECRET`: o `comum/auth.py` já tem a chave padrão, a mesma do `gerar_token.py`.

---

## Etapa 5: Testes no Postman

Criar no Postman uma **coleção** chamada `Integrante 4`, com duas pastas: `Notificação` e `Orquestrador`. Salvar cada pedido nela.

**Notificação (porta 5002)**

- [ ] Com token válido e dados certos: `201`
- [ ] Sem `mensagem`: `400`
- [ ] Sem token: `401`

**Orquestrador (porta 5003)**: os testes exigidos pelo trabalho

- [ ] Fluxo completo, token de participante, evento `7`: `201` com `"notificado": true`, e a mensagem aparece no terminal da Notificação

- [ ] Evento inexistente (`999`): `404`

- [ ] Evento pendente (`8`): `400`

- [ ] Inscrição duplicada (`9`): `409`

- [ ] Token de **organizador**: `403`

- [ ] Notificação desligada: `201` com `"notificado": false`

- [ ] Sem token: `401`

- [ ] **Exportar a coleção** (botão `...` na coleção, depois *Export*) e mandar para o **Integrante 5**, que junta as coleções de todos

---

## Etapa 6: Integração com os serviços reais

- [ ] Confirmar com o Integrante 2 que o `GET /eventos/{id}` devolve **exatamente** o formato combinado, **inclusive para evento pendente**
- [ ] Confirmar com o Integrante 3 que o `POST /inscricoes` devolve `201` e `409` no formato combinado
- [ ] Rodar o Orquestrador **sem** `SIMULADO` e repetir todos os testes da etapa 5
- [ ] Na chamada de integração (quarta, ~14h): `docker compose up`, depois o fluxo completo **pelo gateway** (porta 5000)
- [ ] Ver as notificações no log: `docker compose logs notificacao`
- [ ] Testar a queda ao vivo: `docker compose stop notificacao`, depois inscrever em outro evento, que deve dar `201` com `"notificado": false`
- [ ] Depois: `docker compose start notificacao`

**Pontos de contato (com quem combinar formatos):**

| Com quem     | Sobre o quê                                                                                                |
| ------------ | ---------------------------------------------------------------------------------------------------------- |
| Integrante 1 | `auth.py`, token, rota do gateway `POST /inscricoes` apontando para o Orquestrador, URLs no docker-compose |
| Integrante 2 | Formato do `GET /eventos/{id}`                                                                             |
| Integrante 3 | Formato do `POST /inscricoes` e o `409`                                                                    |
| Integrante 5 | Coleção do Postman, seções da documentação, entradas do Diário de IA                                       |

---

## Etapa 7: Documentação (minha seção)

Entregar ao Integrante 5, que monta o documento final.

- [ ] **ADR-001: arquitetura híbrida SOA + microsserviços.** Reescrever com as minhas palavras no `adrs.md`. Preciso conseguir defender na apresentação.

  - Contexto, decisão, alternativas consideradas, consequências (prós e contras)

- [ ] **Por que cada serviço é SOA ou microsserviço**

  - SOA (Identidade, Notificação, Orquestrador): serviços **genéricos e reutilizáveis**, com **contrato formal** (Swagger), que não conhecem o domínio
  - Microsserviços (ms-eventos, ms-inscricoes, ms-certificados): cada um é **dono de um pedaço do domínio** e do **próprio banco**
  - Vantagens de misturar: reuso, serviços pequenos e independentes, fluxo centralizado e fácil de entender
  - Desvantagens: mais peças para subir, chamadas pela rede (mais lentas e podem falhar), o Orquestrador vira ponto central de falha

- [ ] **Modelo de dados:** registrar que Notificação e Orquestrador **não têm banco**, e por quê

  - Notificação só escreve no log; não há nada para guardar
  - Orquestrador só coordena; quem guarda a inscrição é o ms-inscricoes (cada um no seu banco)

- [ ] **Diagrama de sequência** do fluxo de inscrição (Mermaid):

  ```mermaid
  sequenceDiagram
      actor P as Participante
      participant G as Gateway
      participant O as Orquestrador
      participant E as ms-eventos
      participant I as ms-inscricoes
      participant N as Notificação
      P->>G: POST /inscricoes {evento_id} + token
      G->>O: repassa + token
      O->>E: GET /eventos/{id}
      E-->>O: evento aprovado
      O->>I: POST /inscricoes {evento_id, usuario_id}
      I-->>O: 201 inscrição criada
      O->>N: POST /notificacoes {destinatario, mensagem}
      N-->>O: 201 registrada
      O-->>G: 201 confirmada
      G-->>P: 201 confirmada
  ```

- [ ] **Evolução futura**

  - **Mensageria (RabbitMQ):** a notificação vira uma mensagem numa fila, assíncrona, que não se perde se o serviço cair
  - **Service discovery:** os serviços se encontram sozinhos, sem endereço fixo em variável de ambiente
  - **Circuit breaker:** se um serviço falha muitas vezes, o Orquestrador para de chamá-lo por um tempo em vez de esperar o timeout toda vez

- [ ] Passar a lista dos meus endpoints para o **Integrante 3** montar a tabela geral:

  | Método | Rota                         | Descrição                | Perfis               |
  | ------ | ---------------------------- | ------------------------ | -------------------- |
  | POST   | `/notificacoes`              | Registra uma notificação | qualquer autenticado |
  | POST   | `/inscricoes` (Orquestrador) | Inscrição orquestrada    | participante         |

---

## Etapa 8: Diário de Uso de IA

Anotar **durante** o trabalho. Precisa ter: os principais prompts, o que foi aceito/modificado/rejeitado e por quê, e **pelo menos um erro da IA que eu percebi e corrigi**.

- [ ] Entrada sobre a criação da Notificação
- [ ] Entrada sobre o Orquestrador
- [ ] Entrada com um erro ou limitação da IA
  - *Exemplo real desta sessão:* a IA explicou que `host="0.0.0.0"` "aceita conexões de fora do próprio programa"; o correto é "de fora do próprio computador/container". Ela mesma corrigiu quando perguntei o porquê.
- [ ] Mandar as entradas para o Integrante 5

**Modelo:**

```markdown
### [Nome] — [serviço] — [data]
**IA usada:** ...
**Prompt:** ...
**Resultado:** aceito / modificado / rejeitado
**Por quê:** ...
**Erro encontrado (se houver):** ...
```

---

## Etapa 9: Preparar a apresentação

Conseguir explicar, com as minhas palavras:

- [ ] O que a Notificação e o Orquestrador fazem, e por que são SOA
- [ ] O caminho completo de uma inscrição (o diagrama de sequência)
- [ ] Por que o token é **repassado** em todas as chamadas (cada serviço valida sozinho, ADR-002)
- [ ] Por que a falha da notificação não cancela a inscrição
- [ ] Por que `host="0.0.0.0"` e não `127.0.0.1`
- [ ] Por que nenhum dos dois serviços tem banco
- [ ] O que é o modo `SIMULADO` e como ele permitiu trabalhar sem esperar os colegas
- [ ] Defender o ADR-001
- [ ] **Demonstração ao vivo:** derrubar a Notificação e mostrar o `"notificado": false`

---

## Pronto quando...

- [ ] O fluxo de inscrição funciona **com os serviços reais**, pelo gateway, no Docker
- [ ] Todos os testes da etapa 5 passam e a coleção foi entregue ao Integrante 5
- [ ] Os dois Swaggers estão no ar
- [ ] ADR-001, seção de documentação e entradas do Diário de IA foram entregues

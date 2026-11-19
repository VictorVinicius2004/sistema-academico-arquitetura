# EventHub

O **EventHub** é um sistema distribuído baseado em arquitetura híbrida (SOA e Microsserviços) desenvolvido para o gerenciamento de eventos acadêmicos, inscrições, emissão de certificados e notificações.

---

## 1. Guia de Instalação e Execução

### Pré-requisitos
* **Docker** e **Docker Compose** instalados.
* **Git** para clonar o repositório.

### Passo a passo

1. **Clone o repositório e acesse a pasta do projeto:**
   ```bash
   git clone https://github.com/VictorVinicius2004/sistema-academico-arquitetura.git
   cd sistema-academico-arquitetura
   ```

2. **Configuração de ambiente (`JWT_SECRET`):**
   Todos os 7 serviços compartilham a mesma chave secreta `JWT_SECRET` (com 32 ou mais caracteres) para assinatura e validação dos tokens JWT. Essa variável já vem configurada no arquivo `docker-compose.yml` para execução imediata em ambiente de desenvolvimento.

3. **Suba toda a arquitetura com Docker Compose:**
   ```bash
   docker compose up --build
   ```
   *(Para executar os contêineres em segundo plano, utilize `docker compose up --build -d`.)*

4. **Verifique os serviços de entrada:**
   * **API Gateway:** `http://localhost:5000` (ponto único de acesso para os clientes)
   * **Serviço de Identidade:** `http://localhost:5001`

5. **Para encerrar e remover os contêineres:**
   ```bash
   docker compose down
   ```

---

## 2. Arquitetura de Entrada e Segurança

### API Gateway (`gateway/` — Porta `5000`)
Atua como ponto único de entrada (*Single Entry Point*) e roteador reverso da aplicação. Ele intercepta todas as requisições externas, valida a autenticidade do token JWT na borda e encaminha a chamada para o microsserviço ou serviço SOA correspondente, repassando o cabeçalho `Authorization` intacto.

### Serviço de Identidade (`identidade/` — Porta `5001`)
Responsável pelo cadastro de usuários, gerenciamento de perfis de acesso (RBAC) e autenticação de credenciais com emissão de tokens JWT.

---

## 3. Autenticação e Autorização (JWT & RBAC)

O EventHub utiliza autenticação **stateless** baseada em **JWT (JSON Web Token)** assinado com o algoritmo simétrico **HS256**.

### 3.1. Geração do Token
A emissão ocorre exclusivamente na rota pública `POST /auth/login`. Após validar o e-mail e comparar a senha informada com o hash armazenado no banco (`401 Unauthorized` caso inválidos), o Serviço de Identidade gera um token com validade de **24 horas** contendo o seguinte *payload*:

```json
{
  "sub": "1",
  "nome": "Carlos Admin",
  "email": "admin@ifnmg.edu.br",
  "papel": "admin",
  "exp": 1795120580
}
```

* **`sub`:** identificador do usuário armazenado obrigatoriamente como texto (`str`), conforme exigência da biblioteca `PyJWT`.
* **`nome` e `email`:** incluídos diretamente no token para que serviços como o **Orquestrador** e o **ms-certificados** obtenham os dados do usuário sem precisar consultar o Serviço de Identidade.
* **`papel`:** perfil de acesso utilizado no controle RBAC (`admin`, `organizador` ou `participante`).
* **`exp`:** *timestamp* Unix de expiração do token.

### 3.2. Propagação entre os Serviços
* **Cliente $\rightarrow$ Gateway:** o cliente envia o token no cabeçalho HTTP `Authorization: Bearer <token>` para a porta `5000`.
* **Gateway $\rightarrow$ Destino:** após validar o token, o Gateway repassa o cabeçalho `Authorization` original ao serviço responsável pela rota.
* **Comunicação Interna:** quando um serviço aciona outro via HTTP (como o **Orquestrador** chamando `ms-eventos`, `ms-inscricoes` e `notificacao`, ou o `ms-certificados` consultando o `ms-inscricoes`), o mesmo cabeçalho `Authorization` é propagado na requisição interna.

### 3.3. Validação em Duas Camadas
1. **Camada de Entrada (API Gateway):** verifica a presença do cabeçalho `Authorization`, a assinatura criptográfica (`HS256`) e o prazo de expiração em todas as rotas protegidas. Tokens ausentes, adulterados ou expirados são bloqueados imediatamente com **`401 Unauthorized`**.
2. **Camada de Destino (Serviços Internos):** cada serviço importa o módulo compartilhado `comum/auth.py` e utiliza o decorator `@requer_papel(...)` para decodificar o token e verificar se o campo `papel` possui permissão para aquela operação, retornando **`403 Forbidden`** em caso negativo.

---

## 4. Modelo de Dados (Identidade e Gateway)

### API Gateway (Sem Banco de Dados)
O **API Gateway não possui banco de dados próprio**, pois atua exclusivamente como camada *stateless* de filtro de autenticação e roteamento. Manter o Gateway sem persistência evita acoplamento com regras de negócio, reduz a latência no repasse das requisições e delega o armazenamento de dados exclusivamente aos serviços de domínio.

### Serviço de Identidade (`identidade.db`)
O Serviço de Identidade utiliza um banco **SQLite** (`identidade.db`) com a tabela `usuarios`:

| Campo | Tipo | Descrição |
| :--- | :--- | :--- |
| `id` | `INTEGER` | Chave primária autoincremental |
| `nome` | `TEXT` | Nome completo do usuário |
| `email` | `TEXT` | E-mail único do usuário (restrição `UNIQUE`) |
| `senha_hash` | `TEXT` | Senha armazenada em formato de hash seguro |
| `papel` | `TEXT` | Perfil de acesso (`admin`, `organizador` ou `participante`) |

### Carga Inicial (*Seed*)
Na primeira inicialização, o serviço cria automaticamente três usuários padrão com IDs fixos para facilitar os testes da arquitetura:

| ID | Papel | Nome | E-mail |
| :--- | :--- | :--- | :--- |
| `1` | `admin` | Carlos Admin | `admin@ifnmg.edu.br` |
| `2` | `organizador` | André Organizador | `andre@ifnmg.edu.br` |
| `3` | `participante` | Eric | `eric@ifnmg.edu.br` |

---

## 5. Endpoints (Gateway e Identidade)

| Serviço / Porta | Método | Rota | Descrição | Quem acessa |
| :--- | :--- | :--- | :--- | :--- |
| API Gateway (`:5000`) | `ANY` | `/<prefixo>` | Valida o JWT e encaminha a requisição para o serviço correto. | Autenticados (exceto login) |
| Identidade (`:5001`) | `POST` | `/auth/login` | Valida e-mail e senha e devolve o token JWT. | Público (sem token) |
| Identidade (`:5001`) | `POST` | `/usuarios` | Cadastra um novo usuário no sistema. | `admin` |
| Identidade (`:5001`) | `GET` | `/usuarios` | Lista todos os usuários cadastrados. | `admin` |
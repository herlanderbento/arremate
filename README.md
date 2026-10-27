<div align="center">
  <span style="display: inline-flex; align-items: center; gap: 28px;">
    <img src="https://www.python.org/static/img/python-logo-large.c36dccadd999.png?1576869008" alt="Python Logo" width="120" height="120" />
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="https://cdn.simpleicons.org/nextdotjs/white" />
      <img src="https://cdn.simpleicons.org/nextdotjs/black" alt="Next.js Logo" width="90" height="90" />
    </picture>
  </span>
</div>

<h1 align="center">Arremate</h1>

<p align="center">
  Casa de leilões online de obras de arte, com lances ao vivo,<br />
  carteira simulada e histórico de lances à prova de adulteração.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.14-blue?logo=python&logoColor=white" alt="Python 3.14" />
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/PostgreSQL-15-336791?logo=postgresql&logoColor=white" alt="PostgreSQL" />
  <img src="https://img.shields.io/badge/Next.js-16-000000?logo=nextdotjs&logoColor=white" alt="Next.js 16" />
  <img src="https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black" alt="React 19" />
  <img src="https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white" alt="Docker" />
</p>

---

## Sobre o projeto

**Arremate** é uma casa de leilões online de obras de arte, desenvolvida para o desafio técnico Elite Dev da Verzel. Leiloeiros criam lotes a partir de obras da API pública do [Art Institute of Chicago](https://api.artic.edu/docs/); licitantes depositam saldo simulado, dão lances ao vivo e recebem um comprovante de arremate partilhável. Qualquer pessoa, sem login, pode auditar o histórico de lances de um lote e verificar que ele não foi adulterado.

O back-end segue **Clean Architecture** e **Domain-Driven Design (DDD)**, organizado por módulos de domínio (contas, carteira, catálogo, leilão e auditoria), com as regras de negócio em Python puro, testáveis sem banco. O front-end é uma aplicação Next.js que consome a API.

## Estrutura do repositório

```
arremate/
├── backend/            API (FastAPI), migrations, seed e testes
├── frontend/           aplicação web (Next.js)
├── docker-compose.yml  Postgres + API para desenvolvimento
└── README.md
```

## Sumário

1. [Backend](#backend)
   - [Stack](#stack) · [Como executar](#como-executar) · [Variáveis de ambiente](#variáveis-de-ambiente) · [Deploy](#deploy) · [Dados de teste](#dados-de-teste) · [API](#api)
   - [Histórico à prova de adulteração](#histórico-à-prova-de-adulteração) · [Regras de lance, saldo e liquidação](#regras-de-lance-saldo-e-liquidação) · [Concorrência](#concorrência) · [Resiliência à API externa](#resiliência-à-api-externa) · [Privacidade](#privacidade) · [Testes](#testes) · [Arquitetura](#arquitetura)
2. [Frontend](#frontend)
   - [Stack](#stack-1) · [Como executar](#como-executar-1) · [Variáveis de ambiente](#variáveis-de-ambiente-1) · [Como o front fala com a API](#como-o-front-fala-com-a-api) · [Páginas](#páginas) · [Arquitetura](#arquitetura-1) · [Deploy (Vercel)](#deploy-vercel)
3. [Comportamentos a saber e limitações](#comportamentos-a-saber-e-limitações)
4. [Uso de IA](#uso-de-ia)

---

## Backend

### Stack

Python 3.14 · FastAPI · PostgreSQL 15 · SQLAlchemy 2.0 async (asyncpg) · Alembic · Pydantic v2 · PyJWT + bcrypt · httpx · pytest.

### Como executar

#### Com Docker (recomendado)

Pré-requisito: Docker com Compose.

```bash
cp backend/.env.example backend/.env
# Preencha no backend/.env: POSTGRES_PASSWORD, JWT_SECRET_KEY e AUDIT_SECRET.
# Para gerar segredos: python3 -c "import secrets; print(secrets.token_urlsafe(48))"

docker compose up -d --build                # na raiz: sobe Postgres + API (as migrations correm no arranque)
docker compose exec api python -m scripts.seed
```

- API: http://localhost:8000 · Documentação interativa (Swagger): http://localhost:8000/docs
- Postgres exposto só para a máquina local em `localhost:5433` (usuário e base `arremate`).

#### Sem Docker

Pré-requisitos: Python 3.14 e um PostgreSQL 15+ acessível (por exemplo, só o banco do Compose: `docker compose up -d db`, na raiz).

```bash
cd backend
python3.14 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # ajuste DATABASE_URL para o seu Postgres e preencha os segredos
alembic upgrade head          # cria as tabelas
python -m scripts.seed        # dados de teste
uvicorn main:app --reload --reload-dir src   # http://localhost:8000
```

### Variáveis de ambiente

| Variável | Obrigatória | Descrição |
|---|---|---|
| `DATABASE_URL` | sim | `postgresql+asyncpg://usuario:senha@host:porta/base` |
| `JWT_SECRET_KEY` | sim | Assinatura do token de sessão (≥ 32 bytes) |
| `AUDIT_SECRET` | sim | Chave HMAC da cadeia de lances e dos pseudônimos (≥ 32 bytes). **Nunca fica no banco.** Trocá-la faz todos os lotes aparecerem como adulterados. |
| `POSTGRES_PASSWORD` | só Docker | Senha do Postgres do `docker-compose.yml` |
| `CORS_ORIGINS` | não | Origens do front, separadas por vírgula (padrão `http://localhost:3000`) |
| `COOKIE_SECURE` | não | `true` (padrão). Use `false` só em http local |
| `COOKIE_SAMESITE` | não | `lax` (padrão; serve em produção com o proxy `/api` do front). `none` só se o front chamar a API diretamente noutro domínio (exige `COOKIE_SECURE=true`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | não | Duração da sessão (padrão 1440) |
| `CATALOG_BASE_URL` | não | Padrão `https://api.artic.edu/api/v1` |
| `SETTLEMENT_WORKER_ENABLED` / `SETTLEMENT_INTERVAL_SECONDS` | não | Worker de liquidação (padrão ligado, a cada 10 s) |

### Deploy

A imagem do `backend/Dockerfile` (no Render, por exemplo, com *Root Directory* `backend`) executa `alembic upgrade head` e depois o Uvicorn na porta 8000; basta fornecer as variáveis acima e um Postgres. Depois do primeiro deploy, rode `python -m scripts.seed` uma vez.

**Use uma única instância com um único processo** (sem réplicas e sem `--workers` > 1): as salas de WebSocket e o worker de liquidação vivem em memória dentro da API.

### Dados de teste

`python -m scripts.seed` é idempotente (não faz nada se já tiver sido aplicado). Senha de todos: **`arremate123`**.

| Papel | Email | Saldo |
|---|---|---|
| Leiloeiro | `leiloeiro@arremate.dev` | recebe a venda do lote encerrado |
| Licitante | `ana@arremate.dev` | R$ 10.000,00 depositados |
| Licitante | `bruno@arremate.dev` | R$ 10.000,00 depositados |

Lotes criados:

| Obra | Situação | Para testar |
|---|---|---|
| Nighthawks (Hopper) | **ao vivo por 30 dias**, 3 lances (Ana lidera com R$ 1.200,00) | entrar como Bruno e cobrir; entrar como Ana e ver "você foi superado" |
| Water Lilies (Monet) | ao vivo por 3 dias, sem lances | primeiro lance (mínimo R$ 800,00) |
| The Bedroom (Van Gogh) | agendado (começa em 7 dias) | recusa `LOT_NOT_STARTED` |
| American Gothic (Wood) | encerrado e liquidado, Bruno venceu | comprovante, "Meus arremates", painel do leiloeiro, auditoria |

Se o lote ao vivo já tiver terminado quando for avaliar, `python -m scripts.seed --refresh-live` cria outro lote ao vivo com lances (só se não houver nenhum).

### API

Autenticação por **cookie httpOnly** (`access_token`), gravado pelo login. O front envia as requisições pelo seu proxy `/api` com `withCredentials: true`.

| Método | Rota | Acesso | Descrição |
|---|---|---|---|
| POST | `/auth/register` | público | Cria usuário (`AUCTIONEER` ou `BIDDER`) e carteira |
| POST | `/auth/login` · `/auth/logout` | público | Grava / apaga o cookie de sessão |
| GET | `/auth/me` | autenticado | Usuário atual |
| GET | `/wallet` | licitante | Saldo total, comprometido e disponível |
| POST | `/wallet/deposit` | licitante | Depósito simulado (`amount`, até 2 casas, máx. R$ 100.000,00 por depósito) |
| GET | `/catalog/search?filter=&page=&per_page=` | leiloeiro | Busca obras na API do museu |
| POST | `/lots` | leiloeiro | Cria lote a partir de `external_id` |
| GET | `/lots/mine?filter=&page=&per_page=&sort=&sort_dir=` | leiloeiro | Os seus lotes (inclui cancelados), resultado de cada um e total recebido |
| POST | `/lots/{id}/cancel` | leiloeiro dono | Cancela (com estorno automático se houver lances) |
| GET | `/lots?status=live\|scheduled\|ended&filter=&page=&per_page=` | público | Vitrine (cancelados nunca aparecem) |
| GET | `/lots/{id}` | público | Detalhe, histórico, `server_time`; com sessão de licitante, `my_alias` |
| POST | `/lots/{id}/bids` | licitante | Dá um lance (`amount`) |
| GET | `/me/bids?filter=&page=&per_page=` | licitante | Meus arremates: situação (`winning`, `outbid`, `won`, `lost`, `cancelled`) e token do comprovante |
| GET | `/receipts/{token}` | público | Comprovante de arremate (link partilhável) |
| GET | `/audit/lots/{id}` | público | Auditoria do histórico: `INTACT` ou `TAMPERED` |
| WS | `/ws/lots/{id}` | público | Atualizações ao vivo do lote |
| GET | `/health` | público | Verifica API e banco |

Valores monetários em **reais, decimais com 2 casas**: na entrada, número ou string (`1050.5` ou `"1050.50"`; mais de 2 casas é recusado com `VALIDATION_ERROR`); na saída, sempre string com 2 casas (`"1050.00"`), para não perder precisão no JavaScript. Internamente `Decimal` e `NUMERIC(14,2)`, nunca `float`. Datas em ISO 8601 com fuso (UTC na resposta). Ao criar um lote, `starts_at`/`ends_at` precisam de fuso horário.

#### Erros

Formato único:

```json
{ "error": { "code": "BELOW_MINIMUM", "message": "O lance mínimo é R$ 1.050,00.", "details": { "min_amount": "1050.00" } } }
```

Recusas de lance (HTTP 422, mensagem pronta para exibir): `BELOW_MINIMUM`, `INSUFFICIENT_BALANCE` (com `details.available`), `ALREADY_WINNING`, `LOT_NOT_STARTED`, `LOT_ENDED`; e `403 AUCTIONEER_CANNOT_BID`. Outros códigos: `401 UNAUTHORIZED`/`INVALID_CREDENTIALS`, `403 WRONG_ROLE`/`NOT_OWNER`, `409 EMAIL_ALREADY_REGISTERED`/`BID_CONFLICT`, `422 VALIDATION_ERROR` (com `details.fields`), `503 CATALOG_UNAVAILABLE`.

#### WebSocket

O cliente carrega `GET /lots/{id}` para o estado completo e depois só recebe atualizações:

```json
{ "type": "bid_placed", "lot_id": "…", "seq": 5, "amount": "1200.00", "bidder_alias": "Licitante a3f9c2d1",
  "created_at": "…", "ends_at": "…", "min_next_bid": "1250.00", "bid_count": 5 }
{ "type": "lot_extended", "lot_id": "…", "ends_at": "…" }
{ "type": "lot_closed", "lot_id": "…", "winner_alias": "Licitante a3f9c2d1", "final_amount": "1200.00" }
{ "type": "lot_cancelled", "lot_id": "…" }
```

"Você está ganhando / foi superado": o front compara `bidder_alias` do evento com o `my_alias` recebido em `GET /lots/{id}`. A contagem regressiva usa `server_time` para corrigir a diferença entre o relógio do navegador e o do servidor.

### Histórico à prova de adulteração

**Técnica: cadeia de HMAC-SHA256 com chave fora do banco.**

Cada lance guarda `prev_hash` e `hash`:

```
genesis      = HMAC(K, "genesis|lot_id")                         # prev_hash do 1.º lance
hash         = HMAC(K, "prev_hash|lot_id|seq|bidder_id|amount|created_at")   # amount como "1050.00"
chain_head   = HMAC(K, "head|lot_id|n.º de lances|hash do último lance")   # gravado no lote
```

`K` é o `AUDIT_SECRET`, que existe só na variável de ambiente do servidor. A auditoria (`GET /audit/lots/{id}`) recalcula tudo e compara:

| O que foi feito no banco | Como é detectado |
|---|---|
| Alterar valor, licitante ou data de um lance | o `hash` recalculado não bate (`HASH_MISMATCH`, só naquele lance) |
| Apagar um lance do meio | buraco no `seq` e elo quebrado no seguinte (`SEQ_GAP`, `PREV_HASH_MISMATCH`) |
| Apagar o último lance | `chain_head` do lote não bate (`CHAIN_HEAD_MISMATCH`) |
| Inserir um lance | hash inválido e `chain_head` não bate |
| Apagar o último lance **e** reescrever o lote para apontar para o anterior | `chain_head` exige a chave: copiar o hash visível do penúltimo lance não serve |
| Alterar o lote (lance atual, líder, contagem) | `LOT_STATE_MISMATCH` |
| Alterar o comprovante | `RECEIPT_MISMATCH` (o comprovante guarda o `chain_head` do fecho) |

**Por que HMAC e não um hash simples:** com SHA-256 puro, quem tem acesso ao banco recalcula a cadeia inteira depois de alterar um lance. Com HMAC, recalcular exige a chave, que não está no banco. Por isso também o `chain_head` é um HMAC próprio e não apenas "o hash do último lance": senão, apagar o último lance e copiar o hash do anterior para o lote deixaria tudo consistente.

Não há trigger que impeça escrever em `bids`, de propósito: o banco aceita a adulteração e a auditoria mostra-a. As FKs que apontam para `bids` são `ON DELETE SET NULL`, para que um `DELETE` manual não seja bloqueado.

**Para testar à mão** (com o seed aplicado):

```bash
docker compose exec db psql -U arremate -d arremate
```

```sql
-- id do lote ao vivo (Nighthawks)
SELECT id FROM lots WHERE title = 'Nighthawks';

-- 1) alterar o valor de um lance
UPDATE bids SET amount = 0.01 WHERE lot_id = '<id>' AND seq = 2;
-- 2) ou apagar o último lance
DELETE FROM bids WHERE lot_id = '<id>' AND seq = 3;
-- 3) ou inserir um lance falso
INSERT INTO bids (lot_id, seq, bidder_id, amount, created_at, prev_hash, hash)
SELECT lot_id, 4, bidder_id, 9999.99, now(), hash, repeat('0', 64) FROM bids WHERE lot_id = '<id>' AND seq = 3;
```

Depois abra `GET /audit/lots/<id>`: `status` passa a `TAMPERED`, com a lista de problemas e cada lance marcado `valid: true/false`.

**Limites (assumidos):** quem tiver também o `AUDIT_SECRET` consegue refazer a cadeia; e restaurar um backup antigo do banco inteiro (ou um `chain_head` antigo copiado antes) não é detectável sem uma âncora externa ao sistema (por exemplo, publicar os `chain_head` periodicamente fora dele).

### Regras de lance, saldo e liquidação

- Lances só entre o início e o fim do lote. O primeiro deve ser **≥ lance inicial**; os seguintes **≥ lance atual + incremento mínimo**. O líder não pode cobrir o próprio lance. Leiloeiros não dão lances.
- **Saldo comprometido:** disponível = total − comprometido. Ao liderar, o valor do lance fica comprometido; ao ser superado, volta ao disponível **na mesma transação** do lance que o superou. O lance só é aceito se couber no disponível, que considera todos os lotes que o licitante lidera.
- **Anti-sniping:** um lance aceito quando faltam 2 minutos ou menos muda o fim para **agora + 2 minutos** (evento `lot_extended`).
- **Liquidação:** um worker dentro da API verifica a cada 10 s os lotes vencidos; o vencedor é debitado, o leiloeiro é creditado e é emitido o comprovante (com token aleatório para o link). Lotes sem lances fecham sem vencedor. Se alguém abrir um lote vencido antes do worker passar, `GET /lots/{id}` liquida-o na hora. A liquidação é idempotente.
- **Cancelamento:** só o dono, só antes do fim. Com lances, o valor comprometido do líder é estornado automaticamente.
- Toda movimentação fica no extrato `wallet_transactions` (`DEPOSIT`, `HOLD`, `RELEASE`, `DEBIT`, `CREDIT`).

### Concorrência

- Cada lance corre numa transação que começa com `SELECT … FOR UPDATE` no lote: lances, cancelamento e liquidação do mesmo lote são serializados.
- As carteiras envolvidas (licitante e líder anterior; vencedor e leiloeiro) são bloqueadas **numa única query ordenada por `wallets.id`**, para que duas transações nunca esperem uma pela outra em ciclo (deadlock).
- `UNIQUE (lot_id, seq)` é a rede de segurança: se ainda assim dois lances disputarem a mesma posição, o segundo recebe `409 BID_CONFLICT`.
- `receipts.lot_id` é `UNIQUE`: um lote não pode ser liquidado duas vezes.
- Testados contra Postgres real: lances simultâneos (só um vence), guerra de 6 licitantes (só o líder fica com saldo comprometido), lances cruzados em dois lotes (sem deadlock), depósitos simultâneos (nenhum se perde) e liquidações simultâneas (débito único). Os testes de concorrência foram validados removendo cada proteção e confirmando que passam a falhar.

### Resiliência à API externa

- Ao criar o lote, título, imagem e atributos são **copiados para o lote** (snapshot), com os dados oficiais da API (o que o front envia é ignorado). Vitrine, sala, auditoria e comprovante nunca chamam a API externa.
- Só a **busca do leiloeiro** e a **criação de lote** dependem dela: timeout de 5 s, cache de 5 minutos por busca e, em falha, `503 CATALOG_UNAVAILABLE` com mensagem clara.
- As imagens são servidas pelo servidor IIIF do museu (ver limitações).

### Privacidade

Auditoria, comprovante, WebSocket e histórico identificam licitantes apenas por um **pseudônimo por lote**: `Licitante` + 8 caracteres de `HMAC(K, user_id|lot_id)`. É estável dentro do lote, diferente entre lotes (não dá para seguir um licitante entre leilões) e não revela nome, email nem id.

### Testes

```bash
docker compose up -d db          # na raiz: os testes de integração usam um Postgres real
cd backend && .venv/bin/pytest    # cria e migra a base arremate_test automaticamente
```

- `tests/unit`: regras do lote (cada código de recusa, mínimo, anti-sniping), carteira, cadeia de HMAC, verificação de integridade, cliente da API do museu (com respostas simuladas) e gestor de salas.
- `tests/integration`: todas as rotas com Postgres real, incluindo concorrência, adulteração direta no banco, liquidação, resiliência com a API externa fora do ar, WebSocket de ponta a ponta e seed.

### Arquitetura

O back-end (`backend/`) está organizado em módulos por domínio, cada um com `domain/` (regras em Python puro, testáveis sem banco), `application/` (casos de uso) e `infra/` (HTTP, banco, gateways):

```
backend/
├── main.py         app FastAPI (CORS, erros, rotas, worker no lifespan)
├── migrations/     Alembic
├── scripts/seed.py dados de teste
└── src/
    ├── account/    usuários e autenticação
    ├── wallet/     carteira e extrato
    ├── catalog/    cliente da API do museu (porta + adaptador, com cache)
    ├── auction/    lotes, lances, comprovantes, liquidação, WebSocket
    ├── audit/      cadeia de HMAC, pseudônimos e verificação de integridade
    └── shared/     configuração, banco, erros, segurança
```

Cada requisição usa uma única sessão do banco partilhada pelos repositórios; os repositórios nunca fazem commit. Casos de uso que notificam a sala (lance, liquidação, cancelamento) fazem commit explícito e só depois publicam, para nunca anunciar algo que ainda pode ser desfeito.

---

## Frontend

### Stack

Next.js 16 · React 19 · TypeScript · Tailwind CSS 4 · TanStack Query · Axios.

### Como executar

Pré-requisitos: Node.js 20+ e a API rodando (ver acima).

```bash
cd frontend
cp .env.example .env.local   # os valores padrão já apontam para a API local
npm install
npm run dev                  # http://localhost:3000
```

Para produção: `npm run build` e `npm run start`.

### Variáveis de ambiente

| Variável | Descrição |
|---|---|
| `API_URL` | Para onde o servidor Next encaminha `/api/*` (padrão `http://localhost:8000`). Lida no **build**. |
| `NEXT_PUBLIC_WS_URL` | WebSocket da sala ao vivo, ao qual o navegador se conecta diretamente (padrão `ws://localhost:8000`; em produção `wss://...`). Embutida no **build**. |

### Como o front fala com a API

- O navegador só conversa com o próprio site: `next.config.ts` reescreve `/api/*` para a API. Assim o cookie de sessão (`httpOnly`) pertence ao domínio do front (*first-party*) e funciona em todos os navegadores, inclusive no Safari, que bloqueia cookies de terceiros. O JavaScript nunca vê o token.
- O WebSocket não passa pelo proxy: a sala conecta-se direto à API (`NEXT_PUBLIC_WS_URL`). Não precisa de cookie, porque a sala é pública e só transmite pseudônimos.
- Dados do servidor com TanStack Query; os eventos do WebSocket (`bid_placed`, `lot_extended`, `lot_closed`, `lot_cancelled`) atualizam o cache do lote na hora. Ao reconectar, o lote é recarregado para não perder eventos.
- Imagens das obras pela rota `/museum-image/...` do próprio front (ver [limitações](#comportamentos-a-saber-e-limitações)).
- Tema claro e escuro: segue o sistema na primeira visita e guarda a escolha no navegador.
- Valores monetários chegam e são enviados como texto (`"1050.00"`), nunca como `float`; o front só os formata (`R$ 1.050,00`).

### Páginas

| Rota | Acesso | O que faz |
|---|---|---|
| `/` | público | Vitrine: lotes ao vivo, agendados e encerrados, com busca e paginação |
| `/lotes/[id]` | público (lance só para licitante) | Sala ao vivo: lances em tempo real, contagem regressiva sincronizada com o servidor, prorrogação anti-sniping, "você está ganhando / foi superado", histórico com pseudônimos |
| `/auditoria/[id]` | público | Verificação da cadeia de hashes: íntegro ou adulterado, com o motivo em cada lance |
| `/comprovativos/[token]` | público | Comprovante de arremate (sem dados pessoais), imprimível |
| `/login`, `/registo` | público | Entrar e criar conta (licitante ou leiloeiro) |
| `/carteira` | licitante | Saldo total, comprometido e disponível; depósito simulado |
| `/meus-arremates` | licitante | Lotes em que licitou, situação de cada um e link para o comprovante |
| `/painel` | leiloeiro | Os meus lotes com resultado, total recebido e cancelamento (com reembolso) |
| `/painel/novo` | leiloeiro | Busca no catálogo do museu e criação de lote |

As páginas privadas também são protegidas no navegador (redirecionam para o login e voltam à página de origem), mas quem decide é sempre a API.

### Arquitetura

O front-end (`frontend/`) usa o App Router do Next.js. As páginas só montam a interface; o acesso à API fica nos hooks e as regras de apresentação em `lib/`:

```
frontend/
├── next.config.ts        proxy /api/* → API
├── app/                  rotas (App Router)
│   ├── layout.tsx        HTML raiz, fonte, tema e QueryProvider
│   ├── (auth)/           login e registo (layout próprio, sem cabeçalho)
│   ├── (site)/           páginas com cabeçalho e rodapé
│   │   ├── page.tsx      vitrine
│   │   ├── lotes/[id]/   sala ao vivo (lot-room, bid-form)
│   │   ├── auditoria/[id]/      auditoria pública
│   │   ├── comprovativos/[token]/ comprovante público
│   │   ├── carteira/  meus-arremates/   páginas do licitante
│   │   └── painel/  painel/novo/       páginas do leiloeiro
│   └── museum-image/     rota que serve as imagens do museu pelo próprio site
├── components/           componentes de interface reutilizáveis (cabeçalho, cartão do lote,
│                         contagem regressiva, badges, formulários, proteção de rota, tema)
├── hooks/                acesso à API com TanStack Query, por domínio
│   ├── auth/             sessão: me, login, registo, logout
│   ├── lots/             vitrine, lote, lance, WebSocket da sala, meus arremates, comprovante, auditoria
│   ├── wallet/           carteira e depósito
│   └── panel/            painel do leiloeiro: meus lotes, catálogo, criar e cancelar lote
├── lib/                  cliente HTTP (axios), formatação (moeda, datas, contagem),
│                         estado do lote, tema, redirecionamento seguro
├── providers/            QueryClientProvider
└── types/                tipos das respostas da API
```

- **Server e Client Components:** as páginas dinâmicas (`lotes/[id]`, `auditoria/[id]`, `comprovativos/[token]`) são Server Components que só leem o parâmetro da URL e entregam a um Client Component, que busca os dados. Os dados vivem no navegador porque dependem da sessão (cookie) e das atualizações ao vivo.
- **Estado do servidor:** tudo passa pelo cache do TanStack Query. Lances, eventos do WebSocket, depósitos e cancelamentos atualizam ou invalidam as chaves certas (`["lots", ...]`, `["wallet"]`, `["me", "bids"]`), e as outras páginas ficam corretas sem recarregar.
- **Proteção de rota:** `RequireAuth` redireciona para o login (com `?next=` para voltar) e mostra um aviso quando o papel não é o certo; a API faz a mesma verificação em cada pedido.
- **Estilo:** Tailwind CSS 4, com as cores em variáveis CSS (`app/globals.css`) para o tema claro e escuro.

### Deploy (Vercel)

1. Importe o repositório na Vercel com **Root Directory** `frontend` (framework Next.js detectado automaticamente).
2. Defina as variáveis **antes** do primeiro build (as duas são lidas no build):
   - `API_URL=https://<sua-api>.onrender.com`
   - `NEXT_PUBLIC_WS_URL=wss://<sua-api>.onrender.com`
3. Na API, defina `CORS_ORIGINS=https://<seu-front>.vercel.app`, `COOKIE_SECURE=true` e `COOKIE_SAMESITE=lax`. Com o proxy `/api`, o cookie é do domínio do front, então `lax` basta.

Se mudar o endereço da API, faça um novo deploy do front.

---

## Comportamentos a saber e limitações

- **Instância única:** WebSocket e worker vivem em memória; com várias réplicas, cada uma teria salas próprias e eventos se perderiam entre elas. Escalar exigiria Redis pub/sub (ou similar) e um worker separado com lock.
- **Sessão sem refresh token:** o cookie vale 24 h (configurável); depois é preciso entrar de novo.
- **Cookies entre domínios:** com o proxy `/api` do front (configuração padrão), o cookie é do domínio do front e `COOKIE_SAMESITE=lax` basta. Só se o front chamar a API diretamente noutro domínio é preciso `COOKIE_SAMESITE=none` e `COOKIE_SECURE=true`, e o Safari pode bloquear o cookie.
- **Plano gratuito do Render:** a API dorme após ~15 min sem tráfego; o primeiro acesso depois disso demora até ~1 min. Um ping periódico a `/health` evita isso.
- **Imagens:** os lotes guardam a URL da imagem no servidor do museu, não a imagem. O museu responde com `Cross-Origin-Resource-Policy: same-origin` (o navegador recusa exibi-la noutro site), por isso o front serve-as pela rota `/museum-image/...`, que as busca no museu e as guarda em cache por um dia. Se o museu cair, os lotes continuam funcionando, com "Imagem indisponível" no lugar da foto.
- **Registo aberto:** qualquer pessoa pode criar conta como leiloeiro (não há aprovação).
- **Status "encerrado" antes da liquidação:** entre o fim do lote e a passagem do worker (até ~10 s), o lote já aparece como `ended` e recusa lances; o comprovante surge quando é liquidado.
- **Trocar o `AUDIT_SECRET`** invalida a auditoria de todos os lotes existentes (aparecem como `TAMPERED`) e muda os pseudônimos.

## Uso de IA

Usei IA (Claude Code) como apoio durante o desenvolvimento, principalmente para:

- **Testes:** ajuda na escrita dos testes unitários e de integração, incluindo os cenários de concorrência e de adulteração direta no banco.
- **Correção de bugs:** investigação e correção de erros encontrados durante o desenvolvimento, como as imagens do museu bloqueadas pelo navegador.
- **Revisão do projeto:** revisão do código e da estrutura, para confirmar que o back-end e o front-end cumpriam os requisitos do desafio e apontar problemas.
- **Documentação:** apoio na redação deste README.

As decisões de arquitetura e de produto são minhas. Revi e ajustei o que a IA sugeriu antes de incorporar ao projeto.

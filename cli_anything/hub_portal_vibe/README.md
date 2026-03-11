# cli-anything-hub-portal-vibe

CLI harness for **hub-portal-vibe** — SomosAHub's graduation portal. Provides
Supabase data queries and **browser-automated enrollment flows** via Playwright.

## Quick Start

```bash
cd hub-portal-vibe/agent-harness
pip install -e .
pip install playwright requests
playwright install chromium
```

## Commands

### Data Queries

```bash
# Turmas (graduation classes)
cli-anything-hub-portal-vibe turma list
cli-anything-hub-portal-vibe turma list --status ativa
cli-anything-hub-portal-vibe turma info --codigo 1253
cli-anything-hub-portal-vibe turma stats <turma_id>

# Planos (plans)
cli-anything-hub-portal-vibe plano list --turma-id <id>
cli-anything-hub-portal-vibe plano info <plano_id>

# Lotes (pricing tiers)
cli-anything-hub-portal-vibe lote list --plano-id <id>
cli-anything-hub-portal-vibe lote ativo <plano_id>

# Contratos (contracts)
cli-anything-hub-portal-vibe contrato list --turma-id <id>
cli-anything-hub-portal-vibe contrato info <contrato_id>

# Enrollment summary
cli-anything-hub-portal-vibe adesao summary <turma_id>

# JSON output (any command)
cli-anything-hub-portal-vibe --json turma list
```

### Browser Automation: Enrollment Flow (`adesao run`)

Runs the full formando enrollment via Playwright:
portal -> email+OTP -> dados pessoais -> senha -> turma -> plano -> parcelamento -> contratacao

```bash
# Basic - first plan, default options
cli-anything-hub-portal-vibe adesao run FORMAE-99999

# Choose second plan, 36 installments, due day 15
cli-anything-hub-portal-vibe adesao run FORMAE-99999 --plano 1 --parcelas 36 --dia-vencimento 15

# Extended installments + alternative collection
cli-anything-hub-portal-vibe adesao run FORMAE-99999 --parcelas 24 --estendido --parcelas-estendido 6

# Disable alternative collection (rifas)
cli-anything-hub-portal-vibe adesao run FORMAE-99999 --no-arrecadacao

# Headless with JSON output
cli-anything-hub-portal-vibe --json adesao run FORMAE-99999 --headless
```

#### `adesao run` Options

| Option | Default | Description |
|--------|---------|-------------|
| `--headless/--no-headless` | visible | Browser visibility |
| `--senha` | `369258Gt@` | Password for new account |
| `--reports-dir` | None | Screenshot output directory |
| `--plano` | 0 (first) | Plan index (0-based) |
| `--parcelas` | max | Number of installments |
| `--dia-vencimento` | 10 | Due day (1-28) |
| `--data-primeira-parcela` | auto | First installment (YYYY-MM-DD) |
| `--estendido/--no-estendido` | off | Extended installments toggle |
| `--parcelas-estendido` | None | Extended installment count |
| `--arrecadacao/--no-arrecadacao` | on | Alternative collection (rifas) |
| `--pular-recorrencia/--no-pular-recorrencia` | skip | Skip recurring payment |

#### Enrollment Steps (14 total)

1. Open portal and enter turma code
2. Enter email (auto-generated temp email via mail.tm)
3. Capture OTP from temp email inbox
4. Fill personal data (name, CPF, phone, birth date)
5. Set password
6. Confirm turma selection
7. Select plan (by `--plano` index)
8. Configure installments (parcelas, dia vencimento, estendido, arrecadacao)
9. Fill responsible person data
10. Fill address
11. Sign contract (digital signature)
12. Skip/configure recurring payment
13. Verify final status
14. Cleanup (close browser, delete temp email)

### Browser Automation: Replanejamento (`replanejamento run`)

Renegociacao financeira para contratos com parcelas vencidas:

```bash
cli-anything-hub-portal-vibe replanejamento run user@email.com
cli-anything-hub-portal-vibe replanejamento run user@email.com --senha mypass --parcelas 12
cli-anything-hub-portal-vibe replanejamento run user@email.com --estendido --parcelas-estendido 6

# Data queries
cli-anything-hub-portal-vibe replanejamento listar --contrato-id <id>
cli-anything-hub-portal-vibe replanejamento simular <contrato_id> --parcelas 12
```

Steps: login -> meus contratos -> acoes > replanejamento -> formulario (calendar+sliders) -> confirmar -> verificar

### Browser Automation: Rescisao (`rescisao run`)

Rescisao contratual (contract termination):

```bash
cli-anything-hub-portal-vibe rescisao run user@email.com
cli-anything-hub-portal-vibe rescisao run user@email.com --motivo "Mudanca de cidade"

# Data queries
cli-anything-hub-portal-vibe rescisao listar --turma-id <id>
cli-anything-hub-portal-vibe rescisao simular <contrato_id> --valor-plano 10000 --retencao 30
```

Steps: login -> meus contratos -> acoes > rescisao -> motivo -> verificar calculo -> confirmar -> verificar

### Browser Automation: Upgrade (`upgrade run`)

Mudanca para plano superior:

```bash
cli-anything-hub-portal-vibe upgrade run user@email.com
cli-anything-hub-portal-vibe upgrade run user@email.com --parcelas 24 --estendido --parcelas-estendido 6

# Data queries
cli-anything-hub-portal-vibe upgrade listar --contrato-id <id>
cli-anything-hub-portal-vibe upgrade simular <contrato_id> --valor-atual 8000 --valor-novo 12000
```

Steps: login -> meus contratos -> acoes > upgrade -> selecionar plano -> parcelamento -> confirmar -> verificar

### Browser Automation: Downgrade (`downgrade run`)

Mudanca para plano inferior:

```bash
cli-anything-hub-portal-vibe downgrade run user@email.com
cli-anything-hub-portal-vibe downgrade run user@email.com --parcelas 12

# Data queries
cli-anything-hub-portal-vibe downgrade listar --contrato-id <id>
cli-anything-hub-portal-vibe downgrade simular <contrato_id> --valor-atual 12000 --valor-novo 8000
```

Steps: login -> meus contratos -> acoes > downgrade -> selecionar plano -> parcelamento -> confirmar -> verificar

### Common Options for Financial Flows

| Option | Default | Description |
|--------|---------|-------------|
| `EMAIL` (arg) | required | Formando's portal account email |
| `--senha` | `369258Gt@` | Account password |
| `--headless/--no-headless` | visible | Browser visibility |
| `--reports-dir` | None | Screenshot output directory |
| `--parcelas` | None (portal default) | Number of installments |
| `--estendido/--no-estendido` | off | Extended installments (upgrade/replanejamento) |
| `--parcelas-estendido` | None | Extended installment count |
| `--arrecadacao/--no-arrecadacao` | on | Alternative collection (upgrade/replanejamento) |
| `--motivo` | auto | Reason for termination (rescisao only) |

### Interactive REPL

```bash
cli-anything-hub-portal-vibe  # no subcommand -> enters REPL
```

Available REPL commands: `turma list`, `turma info <codigo>`, `turma stats <id>`,
`plano list <turma_id>`, `lote list <plano_id>`, `lote ativo <plano_id>`,
`contrato list [turma_id]`, `contrato info <id>`, `adesao summary <turma_id>`.

## Architecture

```
agent-harness/
  setup.py                          # PEP 420 namespace package
  cli_anything/
    hub_portal_vibe/
      __init__.py
      __main__.py
      hub_portal_vibe_cli.py        # Click CLI + REPL (9 command groups)
      core/
        __init__.py
        adesao.py                   # Supabase data queries (enrollment)
        adesao_flow.py              # Playwright: full enrollment flow
        financeiro_base.py          # Shared financial formulas
        portal_flow_base.py         # Shared browser automation base class
        replanejamento.py           # Data queries (replanning)
        replanejamento_flow.py      # Playwright: replanejamento flow
        rescisao.py                 # Data queries (termination)
        rescisao_flow.py            # Playwright: rescisao flow
        upgrade.py                  # Data queries (plan upgrade)
        upgrade_flow.py             # Playwright: upgrade flow
        downgrade.py                # Data queries (plan downgrade)
        downgrade_flow.py           # Playwright: downgrade flow
      utils/
        __init__.py
        supabase_backend.py         # Supabase client wrapper
        temp_email.py               # mail.tm API for OTP capture
        repl_skin.py                # Branded REPL interface
      tests/
        __init__.py
        test_installed.py           # Smoke tests
```

**Key dependencies:** click, prompt-toolkit, supabase, playwright, requests

**OTP Resolution:** Uses mail.tm API to create temporary email accounts and poll
for OTP codes. OTP typically arrives in 3-6 seconds. Handles 429 rate limiting
with exponential backoff.

**Supabase:** Connects with anon key by default. Some tables (contratos) require
service role key due to RLS policies.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SUPABASE_URL` | hardcoded | Supabase project URL |
| `SUPABASE_KEY` | hardcoded anon | Supabase API key |

## Running Tests

```bash
cd hub-portal-vibe/agent-harness
python -m pytest cli_anything/hub_portal_vibe/tests/ -v -s
```

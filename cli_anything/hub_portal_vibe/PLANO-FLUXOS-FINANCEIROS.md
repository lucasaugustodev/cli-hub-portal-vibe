# Plano de Implementacao - Fluxos Financeiros

Extensao do CLI para os 5 fluxos financeiros restantes do portal SomosAHub.
Cada fluxo segue o mesmo padrao: **data queries** (Supabase) + **browser automation** (Playwright).

## Referencias

- Cenarios de teste: `C:\Users\PC\Documents\GitHub\scripts-teste-portal-hub\cenarios\cenarios-testes-financeiros.md`
- Implementacoes JS de referencia: `scripts-teste-portal-hub\cenarios\{replanejamento,rescisao,transferencia,upgrade,downgrade}\`
- Fluxo JS de replanejamento: `scripts-teste-portal-hub\fluxos\replanejamento.js`
- Fluxo JS de adesao (referencia padrao): `scripts-teste-portal-hub\fluxos\adesao.js`

---

## 1. Replanejamento (Financial Replanning)

**O que faz:** Renegocia parcelas vencidas/a vencer de um contrato existente, gerando novo plano de pagamento.

**Cenarios de teste:** CT-REP-01 a CT-REP-10 (10 cenarios)
**Referencia JS:** `cenarios/replanejamento/cenario-rep-01.js` ... `cenario-rep-10.js`

### CLI Commands

```bash
# Data queries
cli-anything-hub-portal-vibe replanejamento listar --contrato-id <id>
cli-anything-hub-portal-vibe replanejamento simular --contrato-id <id> --parcelas 12

# Browser automation
cli-anything-hub-portal-vibe replanejamento run <contrato_id> [options]
```

### Options (`replanejamento run`)

| Option | Descricao |
|--------|-----------|
| `--parcelas` | Numero de parcelas do replanejamento |
| `--dia-vencimento` | Dia de vencimento (1-28) |
| `--entrada` | Valor da entrada (entrada inteligente) |
| `--estendido/--no-estendido` | Parcelamento estendido |
| `--parcelas-estendido` | Qtd parcelas estendido |
| `--arrecadacao/--no-arrecadacao` | Arrecadacao alternativa |
| `--headless/--no-headless` | Visibilidade do browser |

### Implementacao

**Arquivo:** `core/replanejamento_flow.py`

**Steps do fluxo browser:**
1. Login como admin no painel
2. Navegar ate contrato do formando
3. Clicar em "Replanejamento"
4. Selecionar parcelas para replanejamento (decomposicao do principal)
5. Configurar entrada inteligente (se --entrada)
6. Configurar numero de parcelas (slider)
7. Configurar dia de vencimento
8. Toggle estendido + parcelas estendido
9. Toggle arrecadacao alternativa
10. Confirmar e verificar taxa de renegociacao (10% padrao)
11. Verificar criacao das novas parcelas
12. Screenshot final + validacao

**Formulas chave:**
- `saldo_base = sum(parcelas_selecionadas.valor_original)` (sem juros/multa)
- `taxa_renegociacao = saldo_base * 0.10`
- `total_replanejamento = saldo_base + taxa_renegociacao`
- `valor_parcela = total_replanejamento / num_parcelas`
- Parcela minima: R$ 50,00

**Data queries:** `core/replanejamento.py`
- `list_renegociacoes(contrato_id)` - tabela `renegociacoes`
- `get_parcelas_vencidas(contrato_id)` - parcelas com status vencida
- `simular_replanejamento(contrato_id, parcelas)` - calculo local

---

## 2. Rescisao (Contract Termination)

**O que faz:** Encerra contrato com calculo de multa rescisoria e saldo devedor/credor.

**Cenarios de teste:** CT-RES-01 a CT-RES-08 (8 cenarios)
**Referencia JS:** `cenarios/rescisao/cenario-res-01.js` ... `cenario-res-08.js`

### CLI Commands

```bash
# Data queries
cli-anything-hub-portal-vibe rescisao simular --contrato-id <id>
cli-anything-hub-portal-vibe rescisao listar  # lista rescisoes existentes

# Browser automation
cli-anything-hub-portal-vibe rescisao run <contrato_id> [options]
```

### Options (`rescisao run`)

| Option | Descricao |
|--------|-----------|
| `--motivo` | Motivo da rescisao (texto) |
| `--headless/--no-headless` | Visibilidade do browser |

### Implementacao

**Arquivo:** `core/rescisao_flow.py`

**Steps do fluxo browser:**
1. Login como admin
2. Navegar ate contrato
3. Clicar "Solicitar Rescisao"
4. Preencher motivo
5. Verificar calculo automatico (multa, saldo)
6. Confirmar rescisao
7. Verificar cancelamento da recorrencia
8. Verificar backup das parcelas originais
9. Screenshot + validacao

**Formulas chave:**
- Regra de retencao por data:
  - Ate 7 dias apos assinatura: retencao 0%
  - 8-30 dias: retencao 10%
  - 31-90 dias: retencao 20%
  - 91-180 dias: retencao 30%
  - 181+ dias: retencao 50%
- `multa_rescisoria = valor_total_contrato * percentual_retencao`
- `total_pago = sum(parcelas com status='paga')`
- `saldo = total_pago - multa_rescisoria`
  - Se positivo -> credito ao formando
  - Se negativo -> debito do formando

**Data queries:** `core/rescisao.py`
- `list_rescisoes(turma_id)` - tabela `rescission_requests`
- `simular_rescisao(contrato_id)` - calculo de multa/saldo
- `get_contrato_parcelas_pagas(contrato_id)` - parcelas com status paga

---

## 3. Transferencia (Contract Transfer)

**O que faz:** Transfere contrato de um formando para outro (mesmo plano ou plano diferente).

**Cenarios de teste:** CT-TRANS-01 a CT-TRANS-06 (6 cenarios)
**Referencia JS:** `cenarios/transferencia/cenario-trans-01.js` ... `cenario-trans-06.js`

### CLI Commands

```bash
# Data queries
cli-anything-hub-portal-vibe transferencia listar --turma-id <id>

# Browser automation
cli-anything-hub-portal-vibe transferencia run <contrato_id> --para-email <email> [options]
```

### Options (`transferencia run`)

| Option | Descricao |
|--------|-----------|
| `--para-email` | Email do destinatario |
| `--novo-plano` | ID do novo plano (se mudar) |
| `--headless/--no-headless` | Visibilidade do browser |

### Implementacao

**Arquivo:** `core/transferencia_flow.py`

**Steps do fluxo browser:**
1. Login como admin
2. Navegar ate contrato origem
3. Clicar "Transferir Contrato"
4. Buscar/selecionar destinatario por email
5. Selecionar plano destino (se diferente)
6. Verificar calculo de credito/debito
7. Confirmar transferencia
8. Verificar novo contrato criado para destinatario
9. Verificar contrato original marcado como transferido
10. Screenshot + validacao

**Data queries:** `core/transferencia.py`
- `list_transferencias(turma_id)` - tabela `transfer_requests`
- `get_transferencia(id)` - detalhes

---

## 4. Upgrade (Plan Upgrade)

**O que faz:** Migra formando para plano superior, calculando credito da rescisao parcial + novo contrato.

**Cenarios de teste:** CT-UPG-01 a CT-UPG-06 (6 cenarios)
**Referencia JS:** `cenarios/upgrade/cenario-upg-01.js` ... `cenario-upg-06.js`

### CLI Commands

```bash
# Data queries
cli-anything-hub-portal-vibe upgrade simular --contrato-id <id> --novo-plano <plano_id>

# Browser automation
cli-anything-hub-portal-vibe upgrade run <contrato_id> --novo-plano <plano_id> [options]
```

### Options (`upgrade run`)

| Option | Descricao |
|--------|-----------|
| `--novo-plano` | ID do plano superior |
| `--parcelas` | Numero de parcelas do novo contrato |
| `--estendido/--no-estendido` | Parcelamento estendido no novo |
| `--parcelas-estendido` | Qtd parcelas estendido |
| `--arrecadacao/--no-arrecadacao` | Arrecadacao alternativa |
| `--headless/--no-headless` | Visibilidade do browser |

### Implementacao

**Arquivo:** `core/upgrade_flow.py`

**Steps do fluxo browser:**
1. Login como admin
2. Navegar ate contrato atual
3. Clicar "Upgrade de Plano"
4. Selecionar novo plano (superior)
5. Verificar calculo: credito da rescisao do plano atual
6. Configurar parcelamento do novo contrato
7. Verificar debito = valor_novo - credito_rescisao
8. Confirmar upgrade
9. Verificar contrato antigo rescindido
10. Verificar novo contrato criado com parcelas
11. Se estendido: verificar taxa de antecipacao
12. Screenshot + validacao

**Formulas chave:**
- `credito = total_pago_contrato_atual - multa_rescisoria`
- `debito_novo = valor_novo_plano - credito`
- `valor_parcela_novo = debito_novo / num_parcelas`
- Se estendido: `taxa_antecipacao` aplicada sobre parcelas estendidas

**Data queries:** `core/upgrade.py`
- `list_mudancas_plano(turma_id, tipo='upgrade')` - tabela `mudancas_plano`
- `simular_upgrade(contrato_id, novo_plano_id)` - calculo credito/debito

---

## 5. Downgrade (Plan Downgrade)

**O que faz:** Migra formando para plano inferior, com credito total ou parcial.

**Cenarios de teste:** CT-DWN-01 a CT-DWN-03 (3 cenarios)
**Referencia JS:** `cenarios/downgrade/cenario-dwn-01.js` ... `cenario-dwn-03.js`

### CLI Commands

```bash
# Data queries
cli-anything-hub-portal-vibe downgrade simular --contrato-id <id> --novo-plano <plano_id>

# Browser automation
cli-anything-hub-portal-vibe downgrade run <contrato_id> --novo-plano <plano_id> [options]
```

### Options (`downgrade run`)

| Option | Descricao |
|--------|-----------|
| `--novo-plano` | ID do plano inferior |
| `--parcelas` | Numero de parcelas |
| `--headless/--no-headless` | Visibilidade do browser |

### Implementacao

**Arquivo:** `core/downgrade_flow.py`

**Steps do fluxo browser:**
1. Login como admin
2. Navegar ate contrato atual
3. Clicar "Downgrade de Plano"
4. Selecionar plano inferior
5. Verificar: bloqueio se tem parcelas vencidas nao pagas
6. Verificar calculo de credito
7. Configurar novo parcelamento
8. Confirmar downgrade
9. Verificar contrato antigo rescindido
10. Verificar novo contrato com credito aplicado
11. Screenshot + validacao

**Formulas chave:**
- Bloqueio: nao permite downgrade se existem parcelas vencidas
- `credito_total = total_pago - multa_rescisoria`
- `valor_novo_plano < valor_plano_atual` (obrigatorio)
- `credito_parcial` se credito > valor_novo_plano

**Data queries:** `core/downgrade.py`
- `list_mudancas_plano(turma_id, tipo='downgrade')` - tabela `mudancas_plano`
- `simular_downgrade(contrato_id, novo_plano_id)` - calculo credito

---

## Regras Transversais (aplicam-se a todos os fluxos)

1. **Cancelamento de recorrencia** - ao rescindir/transferir/upgrade/downgrade, cancelar recorrencia ativa no gateway
2. **Backup de parcelas** - antes de qualquer alteracao, salvar snapshot das parcelas originais
3. **Dia util bancario** - datas de vencimento devem cair em dia util (excluir feriados bancarios)
4. **Arredondamento** - diferenca de centavos vai na ultima parcela
5. **Correcao monetaria** - IGPM/IPCA aplicada em parcelas futuras conforme configuracao do plano

---

## Ordem de Implementacao Sugerida

| Fase | Fluxo | Complexidade | Cenarios | Prioridade |
|------|-------|-------------|----------|------------|
| 1 | **Replanejamento** | Alta | 10 | Alta - mais usado |
| 2 | **Rescisao** | Media | 8 | Alta - base para upgrade/downgrade |
| 3 | **Upgrade** | Alta | 6 | Media - depende de rescisao |
| 4 | **Downgrade** | Media | 3 | Media - similar ao upgrade |
| 5 | **Transferencia** | Media | 6 | Baixa - menos frequente |

**Fase 1 e 2** sao independentes e podem ser implementadas em paralelo.
**Fase 3 e 4** dependem da logica de rescisao (fase 2) pois usam a mesma formula de credito/multa.
**Fase 5** e independente mas menos prioritaria.

---

## Estrutura de Arquivos Final

```
core/
  adesao.py               # [EXISTENTE] data queries adesao
  adesao_flow.py           # [EXISTENTE] browser automation adesao
  replanejamento.py        # [NOVO] data queries + simulacao
  replanejamento_flow.py   # [NOVO] browser automation
  rescisao.py              # [NOVO] data queries + simulacao
  rescisao_flow.py         # [NOVO] browser automation
  transferencia.py         # [NOVO] data queries
  transferencia_flow.py    # [NOVO] browser automation
  upgrade.py               # [NOVO] data queries + simulacao
  upgrade_flow.py          # [NOVO] browser automation
  downgrade.py             # [NOVO] data queries + simulacao
  downgrade_flow.py        # [NOVO] browser automation
  financeiro_base.py       # [NOVO] formulas compartilhadas (multa, retencao, dia util)
```

O `financeiro_base.py` centraliza:
- `calcular_multa_rescisoria(contrato, data_atual)`
- `calcular_saldo(contrato, parcelas_pagas)`
- `proximo_dia_util(data)`
- `arredondar_parcelas(total, num_parcelas)`
- `FERIADOS_BANCARIOS` lista

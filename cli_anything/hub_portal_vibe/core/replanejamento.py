"""Replanejamento (financial replanning) data queries and simulation."""
from datetime import datetime, date
from cli_anything.hub_portal_vibe.utils.supabase_backend import query_table
from cli_anything.hub_portal_vibe.core.financeiro_base import (
    calcular_taxa_renegociacao, proximo_dia_util,
)


def list_renegociacoes(contrato_id=None, turma_id=None):
    """List renegociacoes (replanning records)."""
    filters = {}
    if contrato_id:
        filters["contrato_id"] = contrato_id
    if turma_id:
        filters["turma_id"] = turma_id
    return query_table("renegociacoes", order="-created_at", filters=filters or None)


def get_parcelas_pendentes(contrato_id):
    """Get all pending/overdue parcelas for a contract."""
    rows = query_table("parcelas", filters={"contrato_id": contrato_id}, order="data_vencimento")
    return [r for r in rows if r.get("status") in ("pendente", "vencida", "em_atraso")]


def decompor_principal(parcelas_pendentes, data_referencia=None):
    """Decompose principal into mensal/AA vencido/futuro."""
    if data_referencia is None:
        data_referencia = date.today()
    if isinstance(data_referencia, str):
        data_referencia = datetime.strptime(data_referencia[:10], "%Y-%m-%d").date()

    mensal_vencido = aa_vencida = mensal_futuro = aa_futura = 0
    for p in parcelas_pendentes:
        valor = float(p.get("valor") or p.get("valor_original") or 0)
        tipo = p.get("tipo", "normal")
        venc = p.get("data_vencimento", "")
        if not venc:
            continue
        venc_date = datetime.strptime(str(venc)[:10], "%Y-%m-%d").date()
        is_aa = tipo == "arrecadacao"
        if venc_date < data_referencia:
            if is_aa:
                aa_vencida += valor
            else:
                mensal_vencido += valor
        else:
            if is_aa:
                aa_futura += valor
            else:
                mensal_futuro += valor

    return {
        "mensal_vencido": round(mensal_vencido, 2),
        "aa_vencida": round(aa_vencida, 2),
        "mensal_futuro": round(mensal_futuro, 2),
        "aa_futura": round(aa_futura, 2),
        "principal_vencido": round(mensal_vencido + aa_vencida, 2),
        "principal_total": round(mensal_vencido + aa_vencida + mensal_futuro + aa_futura, 2),
    }


def simular_replanejamento(contrato_id, num_parcelas, config_multa_juros=None,
                            aa_ativa=True, percentual_entrada_minimo=10,
                            data_referencia=None):
    """Simulate a replanning calculation. Returns dict with computed values."""
    if config_multa_juros is None:
        config_multa_juros = {"percentualMulta": "2", "percentualJuros": "1",
                               "periodicidadeJuros": "MENSAL", "regraJuros": "SIMPLES"}
    if data_referencia is None:
        data_referencia = date.today()

    pendentes = get_parcelas_pendentes(contrato_id)
    if not pendentes:
        return {"error": "Nenhuma parcela pendente encontrada"}

    decomp = decompor_principal(pendentes, data_referencia)

    # Principal a replanejar
    if aa_ativa:
        principal = decomp["mensal_vencido"] + decomp["aa_vencida"] + decomp["mensal_futuro"]
    else:
        principal = decomp["principal_total"]

    # Entrada inteligente
    pv = decomp["principal_vencido"]
    if pv == 0:
        entrada = 0
    else:
        entrada_pct = (percentual_entrada_minimo / 100) * pv
        valor_parcela_base = principal / num_parcelas if num_parcelas > 0 else 0
        entrada = max(entrada_pct, valor_parcela_base)
    entrada = round(entrada, 2)

    # Parcelas regulares
    restante = principal - entrada
    n_rest = num_parcelas - 1 if entrada > 0 else num_parcelas
    valor_parcela = round(restante / n_rest, 2) if n_rest > 0 else restante

    # Taxa de renegociacao
    vencidas = [p for p in pendentes
                if p.get("data_vencimento") and
                datetime.strptime(str(p["data_vencimento"])[:10], "%Y-%m-%d").date() < data_referencia]
    taxa = calcular_taxa_renegociacao(vencidas, config_multa_juros, data_referencia)

    return {
        "contrato_id": contrato_id,
        "decomposicao": decomp,
        "aa_ativa": aa_ativa,
        "principal": round(principal, 2),
        "entrada": entrada,
        "num_parcelas": num_parcelas,
        "parcelas_restantes": n_rest,
        "valor_parcela": valor_parcela,
        "parcela_minima_ok": valor_parcela >= 50 if valor_parcela > 0 else True,
        "taxa_renegociacao": taxa,
        "total_com_taxa": round(principal + taxa, 2),
    }

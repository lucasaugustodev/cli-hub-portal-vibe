"""Rescisao (contract termination) data queries and simulation."""
from datetime import datetime, date
from cli_anything.hub_portal_vibe.utils.supabase_backend import query_table
from cli_anything.hub_portal_vibe.core.financeiro_base import (
    selecionar_regra_retencao, calcular_multa_rescisoria, calcular_rescisao,
    calcular_multa, calcular_juros,
)


def list_rescisoes(turma_id=None, contrato_id=None):
    """List rescission requests."""
    filters = {}
    if turma_id:
        filters["turma_id"] = turma_id
    if contrato_id:
        filters["contrato_id"] = contrato_id
    return query_table("rescission_requests", order="-created_at", filters=filters or None)


def get_rescisao(rescisao_id):
    """Get a single rescission request by ID."""
    rows = query_table("rescission_requests", filters={"id": rescisao_id}, limit=1)
    return rows[0] if rows else None


def get_parcelas_pagas(contrato_id):
    """Get all paid parcelas for a contract."""
    rows = query_table("parcelas", filters={"contrato_id": contrato_id}, order="data_vencimento")
    return [r for r in rows if r.get("status") == "pago"]


def get_acordos_pendentes(contrato_id):
    """Get pending renegociation parcelas."""
    rows = query_table("parcelas", filters={"contrato_id": contrato_id}, order="data_vencimento")
    acordos = []
    for r in rows:
        tipo = r.get("tipo", "")
        if tipo in ("renegociacao", "entrada_renegociacao"):
            if r.get("status") not in ("pago", "cancelado"):
                valor_total = float(r.get("valor") or r.get("valor_original") or 0)
                valor_pago = float(r.get("valor_pago") or 0)
                saldo = valor_total - valor_pago
                if saldo > 0:
                    acordos.append({**r, "saldo_pendente": round(saldo, 2)})
    return acordos


def simular_rescisao(contrato_id, valor_plano=None, regras_retencao=None,
                      data_ultima_parcela=None, desconto_admin=0, data_referencia=None):
    """Simulate a rescisao calculation.

    Returns dict with tipo (FORMANDO_RECEBE/FORMANDO_PAGA), valor, details.
    """
    if data_referencia is None:
        data_referencia = date.today()
    if isinstance(data_referencia, str):
        data_referencia = datetime.strptime(data_referencia[:10], "%Y-%m-%d").date()

    # Principal quitado
    pagas = get_parcelas_pagas(contrato_id)
    principal_quitado = sum(
        float(p.get("valor") or p.get("valor_original") or 0)
        for p in pagas
        if p.get("tipo", "normal") in ("normal", "estendido", "arrecadacao")
    )

    # Juros e multas pendentes (rescisao usa taxas fixas: 2% multa, 1% juros mensal simples)
    config_fixo = {"percentualMulta": "2", "percentualJuros": "1",
                    "periodicidadeJuros": "MENSAL", "regraJuros": "SIMPLES"}
    rows = query_table("parcelas", filters={"contrato_id": contrato_id}, order="data_vencimento")
    juros_multas = 0.0
    n_vencidas = 0
    for r in rows:
        if r.get("status") not in ("pendente", "vencida", "em_atraso"):
            continue
        if r.get("tipo", "normal") not in ("normal", "estendido", "arrecadacao"):
            continue
        venc = r.get("data_vencimento", "")
        if not venc:
            continue
        venc_date = datetime.strptime(str(venc)[:10], "%Y-%m-%d").date()
        dias = (data_referencia - venc_date).days
        if dias > 0:
            valor = float(r.get("valor") or r.get("valor_original") or 0)
            juros_multas += calcular_multa(valor, config_fixo)
            juros_multas += calcular_juros(valor, dias, config_fixo)
            n_vencidas += 1
    juros_multas = round(juros_multas, 2)

    # Acordos nao quitados
    acordos = get_acordos_pendentes(contrato_id)
    acordos_total = sum(a.get("saldo_pendente", 0) for a in acordos)

    base_info = {
        "principal_quitado": round(principal_quitado, 2),
        "juros_multas_pendentes": juros_multas,
        "acordos_nao_quitados": round(acordos_total, 2),
        "parcelas_pagas": len(pagas),
        "parcelas_vencidas": n_vencidas,
        "acordos_pendentes": len(acordos),
    }

    if valor_plano is None or regras_retencao is None or data_ultima_parcela is None:
        return {"error": "valor_plano, regras_retencao, data_ultima_parcela obrigatorios", **base_info}

    regra = selecionar_regra_retencao(regras_retencao, data_ultima_parcela, data_referencia)
    if not regra:
        return {"error": "Nenhuma regra de retencao aplicavel", **base_info}

    multa_resc = calcular_multa_rescisoria(valor_plano, regra, desconto_admin)

    resultado = calcular_rescisao(
        valor_plano=valor_plano,
        principal_quitado=principal_quitado,
        multa_rescisoria=multa_resc,
        juros_multas_pendentes=juros_multas,
        acordos_nao_quitados=acordos_total,
    )

    return {
        **resultado, **base_info,
        "valor_plano": valor_plano,
        "multa_rescisoria": multa_resc,
        "regra_aplicada": regra,
        "desconto_admin": desconto_admin,
    }

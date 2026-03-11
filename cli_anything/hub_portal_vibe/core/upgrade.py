"""Upgrade (plan upgrade) data queries and simulation."""
from datetime import datetime, date
from cli_anything.hub_portal_vibe.utils.supabase_backend import query_table
from cli_anything.hub_portal_vibe.core.financeiro_base import (
    aplicar_credito_novo_contrato, arredondar_parcelas,
)


def list_mudancas_plano(contrato_id=None, turma_id=None, tipo=None):
    """List plan change records (upgrade/downgrade)."""
    filters = {}
    if contrato_id:
        filters["contrato_id"] = contrato_id
    if turma_id:
        filters["turma_id"] = turma_id
    if tipo:
        filters["tipo"] = tipo
    return query_table("mudancas_plano", order="-created_at", filters=filters or None)


def get_lotes_disponiveis(turma_id, plano_atual_id=None):
    """Get available lotes for upgrade (higher value than current)."""
    lotes = query_table("lotes", filters={"turma_id": turma_id}, order="valor")
    if plano_atual_id:
        plano_atual = query_table("planos", filters={"id": plano_atual_id}, limit=1)
        if plano_atual:
            valor_atual = float(plano_atual[0].get("valor") or 0)
            lotes = [l for l in lotes if float(l.get("valor") or 0) > valor_atual]
    return [l for l in lotes if l.get("status_venda") in ("ativo", "disponivel", None)]


def simular_upgrade(contrato_id, valor_plano_atual, valor_plano_novo,
                    num_parcelas=12, percentual_entrada=10, data_referencia=None):
    """Simulate an upgrade calculation.

    Upgrade: new plan is more expensive. Formando pays the difference.
    Credit from current contract is applied to the new one.
    """
    if data_referencia is None:
        data_referencia = date.today()

    # Get paid parcelas from current contract
    rows = query_table("parcelas", filters={"contrato_id": contrato_id}, order="data_vencimento")
    pagas = [r for r in rows if r.get("status") == "pago"]
    principal_quitado = sum(
        float(p.get("valor") or p.get("valor_original") or 0)
        for p in pagas
        if p.get("tipo", "normal") in ("normal", "estendido", "arrecadacao")
    )

    diferenca = valor_plano_novo - valor_plano_atual
    credito = principal_quitado

    rc = aplicar_credito_novo_contrato(
        credito, valor_plano_novo, percentual_entrada, num_parcelas
    )

    parcelas_arr = arredondar_parcelas(rc["valor_parcelado"], num_parcelas)

    return {
        "contrato_id": contrato_id,
        "tipo": "UPGRADE",
        "valor_plano_atual": round(valor_plano_atual, 2),
        "valor_plano_novo": round(valor_plano_novo, 2),
        "diferenca": round(diferenca, 2),
        "principal_quitado": round(principal_quitado, 2),
        "credito": round(credito, 2),
        "entrada": rc["entrada_final"],
        "num_parcelas": num_parcelas,
        "valor_parcela": rc["valor_parcela"],
        "valor_parcelado": rc["valor_parcelado"],
        "credito_na_entrada": rc["credito_na_entrada"],
        "credito_nas_parcelas": rc["credito_nas_parcelas"],
        "credito_excedente": rc["credito_excedente"],
        "parcelas": parcelas_arr,
        "parcelas_pagas": len(pagas),
    }

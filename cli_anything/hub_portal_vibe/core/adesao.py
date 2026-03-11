"""Adesao (enrollment) module - manages the enrollment flow.

Flow: turma -> plano -> lote -> contrato -> parcelas
"""
from datetime import datetime, timedelta
from cli_anything.hub_portal_vibe.utils.supabase_backend import (
    query_table, insert_row, update_row, count_rows
)


# ── Turmas ─────────────────────────────────────────────────────────────

def list_turmas(status: str = None):
    """List all turmas (classes), optionally filtered by status."""
    filters = {}
    if status:
        filters["status"] = status
    return query_table("turmas", order="-created_at", filters=filters or None)


def get_turma(turma_id: str = None, codigo: str = None):
    """Get a turma by ID or codigo."""
    if turma_id:
        rows = query_table("turmas", filters={"id": turma_id}, limit=1)
    elif codigo:
        rows = query_table("turmas", filters={"codigo": codigo}, limit=1)
    else:
        raise ValueError("Provide turma_id or codigo")
    return rows[0] if rows else None


def get_turma_stats(turma_id: str):
    """Get enrollment statistics for a turma."""
    participantes = count_rows("turma_participantes", {"turma_id": turma_id})
    contratos = count_rows("contratos", {"turma_id": turma_id})
    contratos_ativos = len(query_table(
        "contratos",
        select="id",
        filters={"turma_id": turma_id, "status": "ativo"}
    ))
    return {
        "turma_id": turma_id,
        "total_participantes": participantes,
        "total_contratos": contratos,
        "contratos_ativos": contratos_ativos,
    }


# ── Planos ─────────────────────────────────────────────────────────────

def list_planos(turma_id: str = None):
    """List planos, optionally for a specific turma."""
    filters = {}
    if turma_id:
        filters["turma_id"] = turma_id
    return query_table("planos", order="nome_plano", filters=filters or None)


def get_plano(plano_id: str):
    """Get a plano by ID."""
    rows = query_table("planos", filters={"id": plano_id}, limit=1)
    return rows[0] if rows else None


# ── Lotes ──────────────────────────────────────────────────────────────

def list_lotes(plano_id: str = None, disponivel: bool = None):
    """List lotes, optionally filtered by plano and availability."""
    filters = {}
    if plano_id:
        filters["plano_id"] = plano_id
    if disponivel is not None:
        filters["disponivel"] = disponivel
    return query_table("lotes", order="created_at", filters=filters or None)


def get_lote_ativo(plano_id: str):
    """Get the current active lote for a plano."""
    rows = query_table(
        "lotes",
        filters={"plano_id": plano_id, "disponivel": True, "status_venda": "ativo"},
        order="created_at",
        limit=1,
    )
    return rows[0] if rows else None


def get_lote(lote_id: str):
    """Get a lote by ID."""
    rows = query_table("lotes", filters={"id": lote_id}, limit=1)
    return rows[0] if rows else None


# ── Contratos ──────────────────────────────────────────────────────────

def list_contratos(turma_id: str = None, user_id: str = None, status: str = None):
    """List contratos with optional filters."""
    filters = {}
    if turma_id:
        filters["turma_id"] = turma_id
    if user_id:
        filters["user_id"] = user_id
    if status:
        filters["status"] = status
    return query_table(
        "contratos",
        select="id,numero_contrato,status,valor_total,valor_parcela,numero_parcelas,"
               "dia_vencimento,data_primeira_parcela,created_at,plano_id,turma_id,user_id,"
               "assinado,data_assinatura,lote_id",
        order="-created_at",
        filters=filters or None,
    )


def get_contrato(contrato_id: str):
    """Get a contrato by ID."""
    rows = query_table("contratos", filters={"id": contrato_id}, limit=1)
    return rows[0] if rows else None


def get_contrato_parcelas(contrato_id: str):
    """Get all parcelas for a contrato."""
    return query_table(
        "parcelas",
        filters={"contrato_id": contrato_id} if contrato_id else None,
        order="numero_parcela",
    )


# ── Parcelas ───────────────────────────────────────────────────────────

def list_parcelas(contrato_id: str = None, status: str = None):
    """List parcelas with optional filters."""
    filters = {}
    if contrato_id:
        # parcelas table might use contrato_id or similar FK
        filters["contrato_id"] = contrato_id
    if status:
        filters["status"] = status
    return query_table("parcelas", order="numero_parcela", filters=filters or None)


# ── Participantes ──────────────────────────────────────────────────────

def list_participantes(turma_id: str):
    """List participantes of a turma."""
    return query_table(
        "turma_participantes",
        filters={"turma_id": turma_id},
        order="-created_at",
    )


def get_participante_status(turma_id: str, user_id: str):
    """Check if a user is a participant in a turma."""
    rows = query_table(
        "turma_participantes",
        filters={"turma_id": turma_id, "user_id": user_id},
        limit=1,
    )
    return rows[0] if rows else None


# ── Summary helpers ────────────────────────────────────────────────────

def enrollment_summary(turma_id: str):
    """Get a full enrollment summary for a turma."""
    turma = get_turma(turma_id=turma_id)
    if not turma:
        return {"error": f"Turma {turma_id} not found"}

    planos = list_planos(turma_id=turma_id)
    stats = get_turma_stats(turma_id)

    planos_summary = []
    for plano in planos:
        lote = get_lote_ativo(plano["id"])
        planos_summary.append({
            "id": plano["id"],
            "nome": plano["nome_plano"],
            "valor": plano.get("valor"),
            "status": plano.get("status"),
            "lote_ativo": {
                "id": lote["id"],
                "nome": lote["nome_lote"],
                "valor": lote.get("valor"),
                "vendidos": lote.get("quantidade_vendida", 0),
                "limite": lote.get("quantidade_limite"),
            } if lote else None,
        })

    return {
        "turma": {
            "id": turma["id"],
            "nome": turma["nome"],
            "codigo": turma["codigo"],
            "sede": turma["sede"],
            "status": turma["status"],
        },
        "stats": stats,
        "planos": planos_summary,
    }

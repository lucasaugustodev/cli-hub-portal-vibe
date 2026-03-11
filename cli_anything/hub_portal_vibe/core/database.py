"""Database operations — thin wrappers over Supabase PostgREST API."""

from __future__ import annotations

from typing import Any, Optional


def list_turmas(client, limit: int = 50, offset: int = 0) -> list[dict]:
    """List all turmas."""
    resp = (
        client.table("turmas")
        .select("id, nome, status, created_at, updated_at")
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return resp.data or []


def get_turma(client, turma_id: str) -> Optional[dict]:
    """Get a single turma by ID."""
    resp = (
        client.table("turmas")
        .select("*")
        .eq("id", turma_id)
        .single()
        .execute()
    )
    return resp.data


def list_categorias(client, turma_id: Optional[str] = None, limit: int = 50) -> list[dict]:
    """List categories, optionally filtered by turma."""
    q = client.table("categorias").select("id, nome, status_ativo, turma_id, created_at")
    if turma_id:
        q = q.eq("turma_id", turma_id)
    resp = q.order("nome").limit(limit).execute()
    return resp.data or []


def get_categoria(client, categoria_id: str) -> Optional[dict]:
    """Get a single categoria by ID."""
    resp = (
        client.table("categorias")
        .select("*")
        .eq("id", categoria_id)
        .single()
        .execute()
    )
    return resp.data


def list_planos(client, turma_id: Optional[str] = None, limit: int = 100) -> list[dict]:
    """List planos, optionally filtered by turma via categoria."""
    q = client.table("planos").select(
        "id, nome, valor_base, numero_parcelas, status, turma_id, categoria_id, created_at"
    )
    if turma_id:
        q = q.eq("turma_id", turma_id)
    resp = q.order("nome").limit(limit).execute()
    return resp.data or []


def list_lotes(client, plano_id: Optional[str] = None, limit: int = 100) -> list[dict]:
    """List lotes, optionally filtered by plano."""
    q = client.table("lotes").select(
        "id, nome_lote, valor, status_venda, disponivel, quantidade_limite, quantidade_vendida, "
        "inicio_vendas, fim_vendas, plano_id"
    )
    if plano_id:
        q = q.eq("plano_id", plano_id)
    resp = q.order("inicio_vendas", desc=True).limit(limit).execute()
    return resp.data or []


def get_lote(client, lote_id: str) -> Optional[dict]:
    """Get a single lote by ID."""
    resp = (
        client.table("lotes")
        .select("*")
        .eq("id", lote_id)
        .single()
        .execute()
    )
    return resp.data


def list_contratos(
    client,
    turma_id: Optional[str] = None,
    user_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    """List contratos with optional filters."""
    q = client.table("contratos").select(
        "id, numero_contrato, status, user_id, turma_id, plano_id, categoria_id, "
        "valor_total, valor_parcela, numero_parcelas, data_primeira_parcela, "
        "assinado, created_at, updated_at"
    )
    if turma_id:
        q = q.eq("turma_id", turma_id)
    if user_id:
        q = q.eq("user_id", user_id)
    if status:
        q = q.eq("status", status)
    resp = q.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
    return resp.data or []


def get_contrato(client, contrato_id: str) -> Optional[dict]:
    """Get a single contrato by ID."""
    resp = (
        client.table("contratos")
        .select("*")
        .eq("id", contrato_id)
        .single()
        .execute()
    )
    return resp.data


def list_parcelas(
    client,
    contrato_id: Optional[str] = None,
    user_id: Optional[str] = None,
    status: Optional[str] = None,
    vencidas: bool = False,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    """List parcelas with optional filters."""
    q = client.table("parcelas").select(
        "id, contrato_id, user_id, numero_parcela, valor, valor_com_multa, "
        "data_vencimento, status, pago_em, forma_pagamento, created_at"
    )
    if contrato_id:
        q = q.eq("contrato_id", contrato_id)
    if user_id:
        q = q.eq("user_id", user_id)
    if status:
        q = q.eq("status", status)
    if vencidas:
        from datetime import date
        today = date.today().isoformat()
        q = q.lt("data_vencimento", today).neq("status", "pago")
    resp = q.order("data_vencimento").range(offset, offset + limit - 1).execute()
    return resp.data or []


def list_profiles(
    client,
    limit: int = 50,
    offset: int = 0,
    search_email: Optional[str] = None,
) -> list[dict]:
    """List user profiles."""
    q = client.table("profiles").select("*")
    if search_email:
        q = q.ilike("email", f"%{search_email}%")
    resp = q.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
    return resp.data or []


def get_profile(client, user_id: str) -> Optional[dict]:
    """Get a single user profile."""
    resp = (
        client.table("profiles")
        .select("*")
        .eq("id", user_id)
        .single()
        .execute()
    )
    return resp.data


def list_boletos(
    client,
    user_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    """List boletos."""
    q = client.table("boletos").select(
        "id, parcela_id, user_id, valor, status, data_vencimento, data_emissao, "
        "codigo_barras, linha_digitavel, pdf_url, created_at"
    )
    if user_id:
        q = q.eq("user_id", user_id)
    if status:
        q = q.eq("status", status)
    resp = q.order("created_at", desc=True).limit(limit).execute()
    return resp.data or []


def list_pix_transactions(
    client,
    user_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    """List PIX transactions."""
    q = client.table("pix_transactions").select("*")
    if user_id:
        q = q.eq("user_id", user_id)
    if status:
        q = q.eq("status", status)
    resp = q.order("created_at", desc=True).limit(limit).execute()
    return resp.data or []


def list_renegociacoes(
    client,
    user_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    """List renegociacoes."""
    q = client.table("renegociacoes").select("*")
    if user_id:
        q = q.eq("user_id", user_id)
    if status:
        q = q.eq("status", status)
    resp = q.order("created_at", desc=True).limit(limit).execute()
    return resp.data or []


def list_rescission_requests(
    client,
    turma_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    """List rescission requests."""
    q = client.table("rescission_requests").select("*")
    if turma_id:
        q = q.eq("turma_id", turma_id)
    if status:
        q = q.eq("status", status)
    resp = q.order("created_at", desc=True).limit(limit).execute()
    return resp.data or []


def list_wallets(client, user_id: Optional[str] = None, limit: int = 50) -> list[dict]:
    """List HubCash wallets."""
    q = client.table("wallets").select("*")
    if user_id:
        q = q.eq("user_id", user_id)
    resp = q.order("created_at", desc=True).limit(limit).execute()
    return resp.data or []


def list_wallet_transactions(
    client,
    wallet_id: Optional[str] = None,
    limit: int = 50,
) -> list[dict]:
    """List wallet transactions."""
    q = client.table("wallet_transactions").select("*")
    if wallet_id:
        q = q.eq("wallet_id", wallet_id)
    resp = q.order("created_at", desc=True).limit(limit).execute()
    return resp.data or []


def list_contract_templates(client, limit: int = 50) -> list[dict]:
    """List contract templates."""
    resp = (
        client.table("contract_templates")
        .select("id, nome, created_at, updated_at")
        .order("nome")
        .limit(limit)
        .execute()
    )
    return resp.data or []


def get_contract_template(client, template_id: str) -> Optional[dict]:
    """Get a single contract template."""
    resp = (
        client.table("contract_templates")
        .select("*")
        .eq("id", template_id)
        .single()
        .execute()
    )
    return resp.data


def list_aptidao(
    client,
    turma_id: Optional[str] = None,
    status_aptidao: Optional[str] = None,
    limit: int = 100,
) -> list[dict]:
    """List aptidao financeira records."""
    q = client.table("aptidao_financeira_alunos").select(
        "id, user_id, turma_id, lote_id, status_aptidao, "
        "parcelas_pagas, parcelas_pendentes, parcelas_vencidas, "
        "valor_total_contratado, valor_total_inadimplente, ultima_verificacao"
    )
    if turma_id:
        q = q.eq("turma_id", turma_id)
    if status_aptidao:
        q = q.eq("status_aptidao", status_aptidao)
    resp = q.order("ultima_verificacao", desc=True).limit(limit).execute()
    return resp.data or []


def list_campanhas_desconto(client, ativo: Optional[bool] = None, limit: int = 50) -> list[dict]:
    """List discount campaigns."""
    q = client.table("campanhas_desconto").select("*")
    if ativo is not None:
        q = q.eq("ativo", ativo)
    resp = q.order("created_at", desc=True).limit(limit).execute()
    return resp.data or []


def table_count(client, table: str) -> int:
    """Get row count for a table (approximate via head=True)."""
    resp = client.table(table).select("id", count="exact").execute()
    return resp.count or 0

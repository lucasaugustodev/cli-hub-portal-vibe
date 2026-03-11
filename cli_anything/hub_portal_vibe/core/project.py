"""Project/app information and health-check for hub-portal-vibe."""

from __future__ import annotations

PROJECT_URL = "https://amylxrskjhqwrlarqfcz.supabase.co"
PROJECT_REF = "amylxrskjhqwrlarqfcz"
PROJECT_NAME = "hub-portal-vibe"
APP_NAME = "SomosAHub Portal"

# Known tables in the schema
SCHEMA_TABLES = [
    "administradores",
    "aptidao_financeira_alunos",
    "aptidao_financeira_historico",
    "boletos",
    "campanhas_desconto",
    "categoria_audit",
    "categorias",
    "configuracoes_padrao_gestao",
    "contract_signatures",
    "contract_templates",
    "contratos",
    "contratos_lock",
    "credit_card_tokens",
    "email_change_audit_log",
    "email_change_requests",
    "eventos",
    "itens",
    "lotes",
    "lotes_disponibilidade_logs",
    "lotes_logs",
    "mudancas_plano",
    "notificacoes",
    "parcelas",
    "parcelas_backup",
    "perfil_participante",
    "pix_transactions",
    "planos",
    "profiles",
    "renegociacoes",
    "rescission_requests",
    "rifas",
    "rifa_bilhetes",
    "transferencias",
    "turma_participantes",
    "turmas",
    "wallet_transactions",
    "wallets",
]

# Edge functions
EDGE_FUNCTIONS = [
    "asaas-payment-proxy",
    "cancelar-pix-manual",
    "check-rescission-expiration",
    "gerar-pix-omie",
    "initiate-email-change-otp",
    "manage-lotes-schedule",
    "obter-status-pix",
    "omie-pix-webhook",
    "send-otp-email",
    "verificar-aptidao-financeira",
    "verificar-status-boleto-inter",
    "verificar-status-pix",
]


def get_project_info() -> dict:
    """Return static project metadata."""
    return {
        "name": PROJECT_NAME,
        "display_name": APP_NAME,
        "url": PROJECT_URL,
        "ref": PROJECT_REF,
        "tables": SCHEMA_TABLES,
        "edge_functions": EDGE_FUNCTIONS,
        "version": "1.0.0",
        "description": "SomosAHub graduation portal — turmas, contratos, financeiro",
    }


def get_domain_map() -> dict[str, list[str]]:
    """Return domain -> tables mapping for CLI command organization."""
    return {
        "turmas": ["turmas", "turma_participantes"],
        "categorias": ["categorias", "categoria_audit", "eventos", "itens"],
        "lotes": ["lotes", "lotes_logs", "lotes_disponibilidade_logs"],
        "contratos": ["contratos", "contratos_lock", "contract_signatures", "contract_templates", "mudancas_plano"],
        "financeiro": ["parcelas", "boletos", "pix_transactions", "wallet_transactions", "wallets",
                       "campanhas_desconto", "renegociacoes", "rescission_requests", "parcelas_backup"],
        "usuarios": ["profiles", "administradores", "aptidao_financeira_alunos", "aptidao_financeira_historico",
                     "credit_card_tokens", "email_change_requests", "email_change_audit_log"],
        "planos": ["planos"],
        "rifas": ["rifas", "rifa_bilhetes"],
        "transferencias": ["transferencias"],
        "configuracoes": ["configuracoes_padrao_gestao"],
    }

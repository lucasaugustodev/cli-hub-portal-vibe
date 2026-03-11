"""Shared financial formulas used across replanejamento, rescisao, upgrade, downgrade.

Implements the rules from cenarios-testes-financeiros.md.
"""
import math
from datetime import datetime, timedelta, date


# -- Feriados bancarios fixos (mes, dia) --
FERIADOS_FIXOS = [
    (1, 1),   # Ano Novo
    (5, 1),   # Dia do Trabalho
    (9, 7),   # Independencia
    (10, 12), # N.S. Aparecida
    (11, 2),  # Finados
    (11, 15), # Proclamacao Republica
    (11, 20), # Consciencia Negra
    (12, 25), # Natal
]


def _calcular_pascoa(ano):
    """Algoritmo de Meeus/Jones/Butcher para calcular data da Pascoa."""
    a = ano % 19
    b = ano // 100
    c = ano % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = ((h + l - 7 * m + 114) % 31) + 1
    return date(ano, mes, dia)


def feriados_moveis(ano):
    """Retorna lista de feriados moveis para o ano."""
    pascoa = _calcular_pascoa(ano)
    return [
        pascoa - timedelta(days=47),  # Carnaval (segunda)
        pascoa - timedelta(days=46),  # Carnaval (terca)
        pascoa - timedelta(days=2),   # Sexta-feira Santa
        pascoa + timedelta(days=60),  # Corpus Christi
    ]


def eh_feriado_bancario(d):
    """Verifica se uma data e feriado bancario."""
    if isinstance(d, datetime):
        d = d.date()
    if (d.month, d.day) in FERIADOS_FIXOS:
        return True
    for fm in feriados_moveis(d.year):
        if d == fm:
            return True
    return False


def eh_dia_util(d):
    """Verifica se uma data e dia util bancario."""
    if isinstance(d, datetime):
        d = d.date()
    if d.weekday() >= 5:  # sabado=5, domingo=6
        return False
    return not eh_feriado_bancario(d)


def proximo_dia_util(d, dias_minimos=0):
    """Retorna proximo dia util a partir de d (ou apos dias_minimos)."""
    if isinstance(d, datetime):
        d = d.date()
    d = d + timedelta(days=dias_minimos)
    while not eh_dia_util(d):
        d += timedelta(days=1)
    return d


# -- Formulas de multa e juros --

def calcular_multa(valor_parcela, config):
    """Calcula multa sobre uma parcela vencida.

    config: dict com 'percentualMulta' ou 'valorMulta'
    """
    perc = config.get("percentualMulta")
    fixo = config.get("valorMulta")
    if perc:
        multa = valor_parcela * (float(perc) / 100)
    elif fixo:
        multa = float(fixo)
    else:
        multa = 0
    return round(multa * 100) / 100


def calcular_juros(valor_parcela, dias_vencido, config):
    """Calcula juros sobre uma parcela vencida.

    config: dict com 'percentualJuros', 'periodicidadeJuros', 'regraJuros'
    """
    taxa = float(config.get("percentualJuros", 0))
    if taxa == 0 or dias_vencido <= 0:
        return 0.0

    periodicidade = config.get("periodicidadeJuros", "MENSAL")
    regra = config.get("regraJuros", "SIMPLES")
    taxa_decimal = taxa / 100

    if periodicidade == "DIARIA":
        periodo = dias_vencido
    elif periodicidade == "MENSAL":
        periodo = dias_vencido / 30
    elif periodicidade == "ANUAL":
        periodo = dias_vencido / 365
    else:
        periodo = dias_vencido / 30

    if regra == "SIMPLES":
        juros = valor_parcela * taxa_decimal * periodo
    else:  # COMPOSTO
        juros = valor_parcela * ((1 + taxa_decimal) ** periodo - 1)

    return round(juros * 100) / 100


def calcular_taxa_renegociacao(parcelas_vencidas, config_multa_juros, data_referencia=None):
    """Calcula taxa de renegociacao (multa + juros de parcelas vencidas).

    parcelas_vencidas: list of dicts com 'valor', 'data_vencimento'
    config_multa_juros: dict com config de multa e juros da turma
    data_referencia: date para calculo de dias (default: hoje)
    """
    if data_referencia is None:
        data_referencia = date.today()
    if isinstance(data_referencia, datetime):
        data_referencia = data_referencia.date()

    total = 0.0
    for p in parcelas_vencidas:
        valor = float(p.get("valor") or p.get("valor_original") or 0)
        venc = p.get("data_vencimento")
        if isinstance(venc, str):
            venc = datetime.strptime(venc[:10], "%Y-%m-%d").date()
        elif isinstance(venc, datetime):
            venc = venc.date()

        dias = (data_referencia - venc).days
        if dias <= 0:
            continue

        multa = calcular_multa(valor, config_multa_juros)
        juros = calcular_juros(valor, dias, config_multa_juros)
        total += multa + juros

    return round(total * 100) / 100


# -- Rescisao formulas --

def selecionar_regra_retencao(regras, data_ultima_parcela, data_hoje=None):
    """Seleciona regra de retencao baseada em dias ate ultima parcela.

    regras: list of dicts com 'diasAntesUltimaParcela', 'tipoRetencao',
            'percentualRetencao', 'valorRetencao'
    """
    if data_hoje is None:
        data_hoje = date.today()
    if isinstance(data_hoje, datetime):
        data_hoje = data_hoje.date()
    if isinstance(data_ultima_parcela, str):
        data_ultima_parcela = datetime.strptime(data_ultima_parcela[:10], "%Y-%m-%d").date()
    elif isinstance(data_ultima_parcela, datetime):
        data_ultima_parcela = data_ultima_parcela.date()

    dias_restantes = (data_ultima_parcela - data_hoje).days

    # Ordenar regras decrescente por diasAntesUltimaParcela
    regras_sorted = sorted(regras, key=lambda r: int(r.get("diasAntesUltimaParcela", 0)), reverse=True)

    for regra in regras_sorted:
        if dias_restantes >= int(regra.get("diasAntesUltimaParcela", 0)):
            return regra

    # Fallback: ultima regra (menor dias)
    return regras_sorted[-1] if regras_sorted else None


def calcular_multa_rescisoria(valor_plano, regra, desconto_admin=0):
    """Calcula multa rescisoria baseada na regra de retencao.

    regra: dict com 'tipoRetencao', 'percentualRetencao' ou 'valorRetencao'
    """
    tipo = regra.get("tipoRetencao", "PERCENTUAL")
    if tipo == "PERCENTUAL":
        perc = float(regra.get("percentualRetencao", 0))
        multa = (perc / 100) * valor_plano
    else:  # VALOR
        multa = float(regra.get("valorRetencao", 0))

    multa -= desconto_admin
    return max(0, round(multa * 100) / 100)


def calcular_rescisao(valor_plano, principal_quitado, multa_rescisoria,
                       juros_multas_pendentes=0, acordos_nao_quitados=0):
    """Calcula resultado final da rescisao.

    Returns:
        dict com 'tipo' (FORMANDO_RECEBE ou FORMANDO_PAGA), 'valor', detalhes
    """
    saldo_base = multa_rescisoria - principal_quitado
    pendencias = juros_multas_pendentes + acordos_nao_quitados

    if saldo_base > 0:
        # Formando paga
        valor_final = saldo_base + pendencias
        return {
            "tipo": "FORMANDO_PAGA",
            "valor": round(valor_final * 100) / 100,
            "saldo_base": round(saldo_base * 100) / 100,
            "pendencias": round(pendencias * 100) / 100,
        }
    else:
        # Formando teria credito
        valor_a_receber = abs(saldo_base) - pendencias

        if valor_a_receber < 0:
            # Inversao: pendencias excedem credito
            return {
                "tipo": "FORMANDO_PAGA",
                "valor": round(abs(valor_a_receber) * 100) / 100,
                "saldo_base": round(saldo_base * 100) / 100,
                "pendencias": round(pendencias * 100) / 100,
                "inversao": True,
            }
        else:
            return {
                "tipo": "FORMANDO_RECEBE",
                "valor": round(valor_a_receber * 100) / 100,
                "saldo_base": round(saldo_base * 100) / 100,
                "pendencias": round(pendencias * 100) / 100,
            }


# -- Arredondamento de parcelas --

def arredondar_parcelas(total, num_parcelas):
    """Distribui valor em parcelas iguais, diferenca de centavos na ultima.

    Returns: list of float values
    """
    if num_parcelas <= 0:
        return []
    valor_base = math.floor(total / num_parcelas * 100) / 100
    parcelas = [valor_base] * num_parcelas
    # Ajustar ultima parcela
    soma = valor_base * (num_parcelas - 1)
    parcelas[-1] = round((total - soma) * 100) / 100
    return parcelas


# -- Credito/Debito para upgrade/downgrade --

def aplicar_credito_novo_contrato(credito, valor_novo_lote, percentual_entrada, num_parcelas):
    """Aplica credito da rescisao no novo contrato (upgrade/downgrade).

    Returns:
        dict com 'entrada_final', 'valor_parcela', 'credito_na_entrada',
              'credito_nas_parcelas', 'valor_parcelado'
    """
    entrada_original = valor_novo_lote * (percentual_entrada / 100)
    valor_parcelado = valor_novo_lote - entrada_original

    if credito >= entrada_original:
        credito_na_entrada = entrada_original
        entrada_final = 0
        credito_restante = credito - entrada_original
    else:
        credito_na_entrada = credito
        entrada_final = entrada_original - credito
        credito_restante = 0

    credito_nas_parcelas = min(credito_restante, valor_parcelado) if credito_restante > 0 else 0

    valor_parcela = (valor_parcelado - credito_nas_parcelas) / num_parcelas if num_parcelas > 0 else 0

    return {
        "entrada_original": round(entrada_original * 100) / 100,
        "entrada_final": round(entrada_final * 100) / 100,
        "valor_parcelado": round(valor_parcelado * 100) / 100,
        "valor_parcela": round(valor_parcela * 100) / 100,
        "credito_na_entrada": round(credito_na_entrada * 100) / 100,
        "credito_nas_parcelas": round(credito_nas_parcelas * 100) / 100,
        "credito_excedente": round(max(0, credito_restante - credito_nas_parcelas) * 100) / 100,
    }

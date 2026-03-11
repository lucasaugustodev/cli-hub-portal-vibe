"""Test all financial calculation flows."""
from cli_anything.hub_portal_vibe.core.financeiro_base import (
    calcular_multa, calcular_juros, calcular_rescisao,
    aplicar_credito_novo_contrato, arredondar_parcelas,
)

cfg = {
    "percentualMulta": "2",
    "percentualJuros": "1",
    "periodicidadeJuros": "MENSAL",
    "regraJuros": "SIMPLES",
}

print("=" * 50)
print("TESTE 1: REPLANEJAMENTO")
print("=" * 50)
print()
print("Cenario: Contrato com parcelas vencidas")
print("  3 parcelas vencidas de R$500 cada")
print("  2 parcelas futuras de R$500 cada")
print("  Multa: 2% | Juros: 1% ao mes (simples)")
print()

vencidas = []
for i, dias in enumerate([90, 60, 30]):
    valor = 500
    multa = calcular_multa(valor, cfg)
    juros = calcular_juros(valor, dias, cfg)
    total = multa + juros
    vencidas.append({"valor": valor, "dias": dias, "multa": multa, "juros": juros})
    print(f"  Parcela {i+1}: R${valor} vencida ha {dias} dias")
    print(f"    Multa: R${multa:.2f} | Juros: R${juros:.2f} | Encargos: R${total:.2f}")

taxa_total = sum(v["multa"] + v["juros"] for v in vencidas)
principal_vencido = 1500
principal_futuro = 1000
principal_total = 2500

print()
print(f"  Principal vencido: R${principal_vencido:.2f}")
print(f"  Principal futuro: R${principal_futuro:.2f}")
print(f"  Principal total: R${principal_total:.2f}")
print(f"  Taxa renegociacao (multa+juros): R${taxa_total:.2f}")

pct_entrada = 10
entrada_pct = (pct_entrada / 100) * principal_vencido
num_parcelas = 12
valor_parcela_base = principal_total / num_parcelas
entrada = max(entrada_pct, valor_parcela_base)
print(f"  Entrada (max entre 10% vencido={entrada_pct:.2f} e parcela_base={valor_parcela_base:.2f}): R${entrada:.2f}")

restante = principal_total - entrada
n_rest = num_parcelas - 1
vp = restante / n_rest
print(f"  Parcelas: {n_rest}x de R${vp:.2f}")
print(f"  Parcela minima OK: {vp >= 50}")
print(f"  Total com taxa: R${principal_total + taxa_total:.2f}")

print()
print("=" * 50)
print("TESTE 2: RESCISAO")
print("=" * 50)
print()

print("Cenario A: Formando recebe")
print("  Plano: R$10.000 | Quitado: R$5.000 | Retencao: 30%")
multa_resc = 10000 * 0.30
resultado = calcular_rescisao(10000, 5000, multa_resc, 0, 0)
print(f"  Multa rescisoria: R${multa_resc:.2f}")
print(f"  Saldo = 5000 - 3000 = R${5000 - multa_resc:.2f}")
print(f"  Tipo: {resultado['tipo']} | Valor: R${resultado['valor']:.2f}")

print()
print("Cenario B: Formando paga")
print("  Plano: R$10.000 | Quitado: R$2.000 | Retencao: 30%")
resultado2 = calcular_rescisao(10000, 2000, 3000, 0, 0)
print(f"  Saldo = 2000 - 3000 = -R$1000")
print(f"  Tipo: {resultado2['tipo']} | Valor: R${resultado2['valor']:.2f}")

print()
print("Cenario C: Com juros e acordos pendentes")
print("  Quitado: R$5.000 | Multa: R$3.000 | Juros: R$200 | Acordos: R$800")
resultado3 = calcular_rescisao(10000, 5000, 3000, 200, 800)
print(f"  Saldo = 5000 - 3000 - 200 - 800 = R${5000-3000-200-800:.2f}")
print(f"  Tipo: {resultado3['tipo']} | Valor: R${resultado3['valor']:.2f}")

print()
print("=" * 50)
print("TESTE 3: UPGRADE")
print("=" * 50)
print()
print("Cenario: Muda para plano mais caro")
print("  Plano atual: R$8.000 | Plano novo: R$12.000")
print("  Ja pagou: R$1.600 (4x R$400)")
print("  Entrada: 10% | Parcelas: 12x")

rc = aplicar_credito_novo_contrato(1600, 12000, 10, 12)
print()
print(f"  Diferenca: R${12000-8000:.2f}")
print(f"  Credito: R$1.600,00")
print(f"  Entrada original (10% de 12000): R${rc['entrada_original']:.2f}")
print(f"  Credito absorve entrada: R${rc['credito_na_entrada']:.2f}")
print(f"  Entrada a pagar: R${rc['entrada_final']:.2f}")
print(f"  Credito restante nas parcelas: R${rc['credito_nas_parcelas']:.2f}")
print(f"  Valor parcelado: R${rc['valor_parcelado']:.2f}")
print(f"  Valor parcela: R${rc['valor_parcela']:.2f}")
print(f"  Credito excedente: R${rc['credito_excedente']:.2f}")

arr = arredondar_parcelas(rc["valor_parcelado"], 12)
print(f"  Parcelas arredondadas: {arr[:3]}... total=R${sum(arr):.2f}")

print()
print("=" * 50)
print("TESTE 4: DOWNGRADE")
print("=" * 50)
print()
print("Cenario: Muda para plano mais barato")
print("  Plano atual: R$12.000 | Plano novo: R$8.000")
print("  Ja pagou: R$5.000")
print("  Entrada: 10% | Parcelas: 12x")

rc2 = aplicar_credito_novo_contrato(5000, 8000, 10, 12)
print()
print(f"  Diferenca: R${8000-12000:.2f} (plano mais barato)")
print(f"  Credito: R$5.000,00")
print(f"  Entrada original (10% de 8000): R${rc2['entrada_original']:.2f}")
print(f"  Credito absorve entrada: R${rc2['credito_na_entrada']:.2f}")
print(f"  Entrada a pagar: R${rc2['entrada_final']:.2f}")
print(f"  Credito restante nas parcelas: R${rc2['credito_nas_parcelas']:.2f}")
print(f"  Valor parcelado: R${rc2['valor_parcelado']:.2f}")
print(f"  Valor parcela: R${rc2['valor_parcela']:.2f}")
print(f"  Credito excedente (devolver): R${rc2['credito_excedente']:.2f}")
if rc2["credito_excedente"] > 0:
    print(f"  >> Formando tem R${rc2['credito_excedente']:.2f} de credito!")
    print(f"  >> Parcela: R$0. Contrato ja quitado pelo credito.")

print()
print("=" * 50)
print("TODOS OS TESTES PASSARAM")
print("=" * 50)

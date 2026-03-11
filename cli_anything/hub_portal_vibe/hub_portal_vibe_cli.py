"""Hub Portal Vibe CLI - Agent-native interface for SomosAHub portal.

Usage:
    cli-anything-hub-portal-vibe turma list
    cli-anything-hub-portal-vibe turma info --codigo 1253
    cli-anything-hub-portal-vibe plano list --turma-id <id>
    cli-anything-hub-portal-vibe lote list --plano-id <id>
    cli-anything-hub-portal-vibe contrato list --turma-id <id>
    cli-anything-hub-portal-vibe adesao summary --turma-id <id>
"""
import json
import sys
import click
from cli_anything.hub_portal_vibe.core.adesao import (
    list_turmas, get_turma, get_turma_stats,
    list_planos, get_plano,
    list_lotes, get_lote_ativo, get_lote,
    list_contratos, get_contrato, get_contrato_parcelas,
    list_parcelas, list_participantes, get_participante_status,
    enrollment_summary,
)


def _output(data, use_json: bool):
    """Output data as JSON or human-readable."""
    if use_json:
        click.echo(json.dumps(data, indent=2, default=str, ensure_ascii=False))
    else:
        if isinstance(data, list):
            for item in data:
                _print_row(item)
        elif isinstance(data, dict):
            _print_row(data)


def _print_row(row: dict, indent: int = 0):
    """Pretty-print a dict row."""
    prefix = "  " * indent
    for key, val in row.items():
        if isinstance(val, dict):
            click.echo(f"{prefix}{click.style(key, fg='cyan')}: ")
            _print_row(val, indent + 1)
        elif isinstance(val, list) and val and isinstance(val[0], dict):
            click.echo(f"{prefix}{click.style(key, fg='cyan')}: ({len(val)} items)")
            for i, item in enumerate(val[:5]):
                click.echo(f"{prefix}  [{i}]")
                _print_row(item, indent + 2)
            if len(val) > 5:
                click.echo(f"{prefix}  ... and {len(val)-5} more")
        else:
            click.echo(f"{prefix}{click.style(key, fg='cyan')}: {val}")
    if indent == 0:
        click.echo("---")


def _fmt_money(val):
    """Format a number as BRL currency."""
    if val is None:
        return "N/A"
    return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# -- Main group --

@click.group(invoke_without_command=True)
@click.option("--json", "use_json", is_flag=True, help="Output in JSON format")
@click.pass_context
def cli(ctx, use_json):
    """Hub Portal Vibe CLI - SomosAHub portal management."""
    ctx.ensure_object(dict)
    ctx.obj["json"] = use_json
    if ctx.invoked_subcommand is None:
        ctx.invoke(repl)


# -- REPL --

@cli.command(hidden=True)
@click.pass_context
def repl(ctx):
    """Interactive REPL mode."""
    from cli_anything.hub_portal_vibe.utils.repl_skin import ReplSkin

    skin = ReplSkin("hub-portal", version="1.0.0")
    skin.print_banner()

    commands = {
        "turma list": "List all turmas",
        "turma info <codigo>": "Show turma details",
        "turma stats <turma_id>": "Show turma enrollment stats",
        "plano list <turma_id>": "List planos for a turma",
        "lote list <plano_id>": "List lotes for a plano",
        "lote ativo <plano_id>": "Show active lote for a plano",
        "contrato list [turma_id]": "List contratos",
        "contrato info <id>": "Show contrato details with parcelas",
        "adesao summary <turma_id>": "Full enrollment summary",
        "help": "Show this help",
        "quit / exit": "Exit the REPL",
    }
    skin.help(commands)

    pt_session = skin.create_prompt_session()

    while True:
        try:
            line = skin.get_input(pt_session)
            if not line:
                continue

            parts = line.strip().split()
            cmd = parts[0].lower()

            if cmd in ("quit", "exit", "q"):
                skin.print_goodbye()
                break
            elif cmd == "help":
                skin.help(commands)
            elif cmd == "turma":
                _repl_turma(skin, parts[1:])
            elif cmd == "plano":
                _repl_plano(skin, parts[1:])
            elif cmd == "lote":
                _repl_lote(skin, parts[1:])
            elif cmd == "contrato":
                _repl_contrato(skin, parts[1:])
            elif cmd == "adesao":
                _repl_adesao(skin, parts[1:])
            else:
                skin.error(f"Unknown command: {cmd}. Type 'help' for commands.")

        except (KeyboardInterrupt, EOFError):
            skin.print_goodbye()
            break
        except Exception as e:
            skin.error(str(e))


def _repl_turma(skin, args):
    if not args:
        skin.error("Usage: turma <list|info|stats> [args]")
        return
    sub = args[0]
    if sub == "list":
        turmas = list_turmas()
        headers = ["Codigo", "Nome", "Sede", "Status"]
        rows = [[t["codigo"], t["nome"], t["sede"], t["status"]] for t in turmas]
        skin.table(headers, rows)
        skin.info(f"{len(turmas)} turma(s) found")
    elif sub == "info":
        if len(args) < 2:
            skin.error("Usage: turma info <codigo>")
            return
        t = get_turma(codigo=args[1])
        if t:
            skin.status_block({
                "ID": t["id"],
                "Nome": t["nome"],
                "Codigo": t["codigo"],
                "Sede": t["sede"],
                "Status": t["status"],
                "Baile": t.get("data_prevista_baile") or "N/A",
            }, title="Turma")
        else:
            skin.warning(f"Turma '{args[1]}' not found")
    elif sub == "stats":
        if len(args) < 2:
            skin.error("Usage: turma stats <turma_id>")
            return
        stats = get_turma_stats(args[1])
        skin.status_block({
            "Participantes": str(stats["total_participantes"]),
            "Contratos": str(stats["total_contratos"]),
            "Ativos": str(stats["contratos_ativos"]),
        }, title="Enrollment Stats")


def _repl_plano(skin, args):
    if not args:
        skin.error("Usage: plano list [turma_id]")
        return
    sub = args[0]
    if sub == "list":
        turma_id = args[1] if len(args) > 1 else None
        planos = list_planos(turma_id=turma_id)
        headers = ["Nome", "Status", "Valor"]
        rows = [[p["nome_plano"], p.get("status", ""), _fmt_money(p.get("valor"))] for p in planos]
        skin.table(headers, rows)
        skin.info(f"{len(planos)} plano(s) found")


def _repl_lote(skin, args):
    if not args:
        skin.error("Usage: lote <list|ativo> <plano_id>")
        return
    sub = args[0]
    if sub == "list":
        plano_id = args[1] if len(args) > 1 else None
        lotes = list_lotes(plano_id=plano_id)
        headers = ["Nome", "Valor", "Vendidos", "Limite", "Status"]
        rows = [
            [l["nome_lote"], _fmt_money(l.get("valor")),
             str(l.get("quantidade_vendida", 0)), str(l.get("quantidade_limite", "")),
             l.get("status_venda", "")]
            for l in lotes
        ]
        skin.table(headers, rows)
    elif sub == "ativo":
        if len(args) < 2:
            skin.error("Usage: lote ativo <plano_id>")
            return
        lote = get_lote_ativo(args[1])
        if lote:
            skin.status_block({
                "ID": lote["id"],
                "Nome": lote["nome_lote"],
                "Valor": _fmt_money(lote.get("valor")),
                "Vendidos": str(lote.get("quantidade_vendida", 0)),
                "Limite": str(lote.get("quantidade_limite") or "ilimitado"),
                "Status": lote.get("status_venda", ""),
            }, title="Lote Ativo")
        else:
            skin.warning("No active lote found for this plano")


def _repl_contrato(skin, args):
    if not args:
        skin.error("Usage: contrato <list|info> [args]")
        return
    sub = args[0]
    if sub == "list":
        turma_id = args[1] if len(args) > 1 else None
        contratos = list_contratos(turma_id=turma_id)
        headers = ["Numero", "Status", "Valor Total", "Parcelas", "Assinado"]
        rows = [
            [c["numero_contrato"], c.get("status", ""),
             _fmt_money(c.get("valor_total")), str(c.get("numero_parcelas", "")),
             "Sim" if c.get("assinado") else "Nao"]
            for c in contratos[:20]
        ]
        skin.table(headers, rows)
        skin.info(f"{len(contratos)} contrato(s) found (showing max 20)")
    elif sub == "info":
        if len(args) < 2:
            skin.error("Usage: contrato info <contrato_id>")
            return
        c = get_contrato(args[1])
        if c:
            skin.status_block({
                "Numero": c["numero_contrato"],
                "Status": c.get("status", ""),
                "Valor Total": _fmt_money(c.get("valor_total")),
                "Valor Parcela": _fmt_money(c.get("valor_parcela")),
                "Parcelas": str(c.get("numero_parcelas", "")),
                "Dia Vencimento": str(c.get("dia_vencimento", "")),
                "1a Parcela": c.get("data_primeira_parcela", ""),
                "Assinado": "Sim" if c.get("assinado") else "Nao",
            }, title="Contrato")
        else:
            skin.warning(f"Contrato not found: {args[1]}")


def _repl_adesao(skin, args):
    if not args:
        skin.error("Usage: adesao summary <turma_id>")
        return
    sub = args[0]
    if sub == "summary":
        if len(args) < 2:
            skin.error("Usage: adesao summary <turma_id>")
            return
        data = enrollment_summary(args[1])
        if "error" in data:
            skin.error(data["error"])
            return
        t = data["turma"]
        s = data["stats"]
        skin.status_block({
            "Turma": f"{t['nome']} ({t['codigo']})",
            "Sede": t["sede"],
            "Status": t["status"],
            "Participantes": str(s["total_participantes"]),
            "Contratos": str(s["total_contratos"]),
            "Ativos": str(s["contratos_ativos"]),
        }, title="Enrollment Summary")
        skin.section("Planos")
        for p in data["planos"]:
            lote_info = ""
            if p["lote_ativo"]:
                l = p["lote_ativo"]
                lote_info = f" | Lote: {l['nome']} @ {_fmt_money(l['valor'])} ({l['vendidos']} vendidos)"
            skin.info(f"{p['nome']} [{p['status']}] - {_fmt_money(p['valor'])}{lote_info}")


# -- CLI subcommands --

@cli.group()
def turma():
    """Manage turmas (classes)."""
    pass


@turma.command("list")
@click.option("--status", help="Filter by status (ativa, inativa, etc.)")
@click.pass_context
def turma_list(ctx, status):
    """List all turmas."""
    data = list_turmas(status=status)
    _output(data, ctx.obj["json"])


@turma.command("info")
@click.option("--id", "turma_id", help="Turma ID")
@click.option("--codigo", help="Turma codigo")
@click.pass_context
def turma_info(ctx, turma_id, codigo):
    """Get turma details."""
    data = get_turma(turma_id=turma_id, codigo=codigo)
    if data:
        _output(data, ctx.obj["json"])
    else:
        click.echo("Turma not found", err=True)
        sys.exit(1)


@turma.command("stats")
@click.argument("turma_id")
@click.pass_context
def turma_stats(ctx, turma_id):
    """Get enrollment statistics for a turma."""
    data = get_turma_stats(turma_id)
    _output(data, ctx.obj["json"])


@cli.group()
def plano():
    """Manage planos (plans)."""
    pass


@plano.command("list")
@click.option("--turma-id", help="Filter by turma ID")
@click.pass_context
def plano_list(ctx, turma_id):
    """List planos."""
    data = list_planos(turma_id=turma_id)
    _output(data, ctx.obj["json"])


@plano.command("info")
@click.argument("plano_id")
@click.pass_context
def plano_info(ctx, plano_id):
    """Get plano details."""
    data = get_plano(plano_id)
    if data:
        _output(data, ctx.obj["json"])
    else:
        click.echo("Plano not found", err=True)
        sys.exit(1)


@cli.group()
def lote():
    """Manage lotes (batches/pricing tiers)."""
    pass


@lote.command("list")
@click.option("--plano-id", help="Filter by plano ID")
@click.option("--disponivel/--no-disponivel", default=None, help="Filter by availability")
@click.pass_context
def lote_list(ctx, plano_id, disponivel):
    """List lotes."""
    data = list_lotes(plano_id=plano_id, disponivel=disponivel)
    _output(data, ctx.obj["json"])


@lote.command("ativo")
@click.argument("plano_id")
@click.pass_context
def lote_ativo(ctx, plano_id):
    """Get the active lote for a plano."""
    data = get_lote_ativo(plano_id)
    if data:
        _output(data, ctx.obj["json"])
    else:
        click.echo("No active lote found", err=True)
        sys.exit(1)


@cli.group()
def contrato():
    """Manage contratos (contracts)."""
    pass


@contrato.command("list")
@click.option("--turma-id", help="Filter by turma ID")
@click.option("--user-id", help="Filter by user ID")
@click.option("--status", help="Filter by status")
@click.pass_context
def contrato_list(ctx, turma_id, user_id, status):
    """List contratos."""
    data = list_contratos(turma_id=turma_id, user_id=user_id, status=status)
    _output(data, ctx.obj["json"])


@contrato.command("info")
@click.argument("contrato_id")
@click.pass_context
def contrato_info(ctx, contrato_id):
    """Get contrato details with parcelas."""
    data = get_contrato(contrato_id)
    if data:
        parcelas = get_contrato_parcelas(contrato_id)
        data["parcelas"] = parcelas
        _output(data, ctx.obj["json"])
    else:
        click.echo("Contrato not found", err=True)
        sys.exit(1)


@cli.group()
def adesao():
    """Enrollment summary and management."""
    pass


@adesao.command("summary")
@click.argument("turma_id")
@click.pass_context
def adesao_summary(ctx, turma_id):
    """Get full enrollment summary for a turma."""
    data = enrollment_summary(turma_id)
    _output(data, ctx.obj["json"])


@adesao.command("run")
@click.argument("turma_code")
@click.option("--headless/--no-headless", default=False,
              help="Run browser in headless mode (default: visible)")
@click.option("--senha", default="369258Gt@", help="Password for the new account")
@click.option("--reports-dir", default=None, help="Directory for screenshots")
@click.option("--plano", "plano_index", type=int, default=None,
              help="Plan index to select (0=first, 1=second, etc.)")
@click.option("--parcelas", type=int, default=None,
              help="Number of installments (e.g. 12, 24, 36, 60)")
@click.option("--dia-vencimento", type=int, default=10,
              help="Due day for installments (1-28, default: 10)")
@click.option("--data-primeira-parcela", default=None,
              help="First installment date (YYYY-MM-DD, default: auto)")
@click.option("--estendido/--no-estendido", default=False,
              help="Enable extended installments (cartao parcelamento estendido)")
@click.option("--parcelas-estendido", type=int, default=None,
              help="Number of extended installments (requires --estendido)")
@click.option("--arrecadacao/--no-arrecadacao", default=True,
              help="Enable alternative collection - rifas (default: enabled)")
@click.option("--pular-recorrencia/--no-pular-recorrencia", default=True,
              help="Skip recurring payment setup (default: skip)")
@click.pass_context
def adesao_run(ctx, turma_code, headless, senha, reports_dir,
               plano_index, parcelas, dia_vencimento, data_primeira_parcela,
               estendido, parcelas_estendido, arrecadacao, pular_recorrencia):
    """Run full automated enrollment flow for a turma.

    Creates a temp email, navigates the portal, fills all forms,
    captures OTP codes, and completes the enrollment.

    \b
    Examples:
      # Basic - first plan, default options
      cli-anything-hub-portal-vibe adesao run FORMAE-99999

      # Choose second plan, 36 installments, due day 15
      cli-anything-hub-portal-vibe adesao run FORMAE-99999 --plano 1 --parcelas 36 --dia-vencimento 15

      # 24 installments + 6 extended, with alternative collection
      cli-anything-hub-portal-vibe adesao run FORMAE-99999 --parcelas 24 --estendido --parcelas-estendido 6

      # Disable alternative collection (rifas)
      cli-anything-hub-portal-vibe adesao run FORMAE-99999 --no-arrecadacao

      # Headless with JSON output
      cli-anything-hub-portal-vibe --json adesao run FORMAE-99999 --headless --parcelas 12
    """
    from cli_anything.hub_portal_vibe.core.adesao_flow import AdesaoFlow, AdesaoConfig

    use_json = ctx.obj["json"]

    # Build config from CLI options
    config = AdesaoConfig()
    config.plano_index = plano_index
    config.parcelas = parcelas
    config.dia_vencimento = dia_vencimento
    config.data_primeira_parcela = data_primeira_parcela
    config.parcelamento_estendido = estendido
    config.parcelas_estendido = parcelas_estendido
    config.arrecadacao_alternativa = arrecadacao
    config.pular_recorrencia = pular_recorrencia

    def on_step(num, desc, status, error=None):
        if not use_json:
            icon = click.style("[OK]", fg="green") if status == "passed" \
                else click.style("[FAIL]", fg="red")
            msg = f"  {icon} Step {num}: {desc}"
            if error:
                msg += f" - {click.style(error, fg='yellow')}"
            click.echo(msg)

    flow = AdesaoFlow(
        turma_code=turma_code,
        headless=headless,
        senha=senha,
        reports_dir=reports_dir,
        on_step=on_step if not use_json else None,
        config=config,
    )
    results = flow.run()

    if use_json:
        _output({
            "turma_code": turma_code,
            "email": flow.email,
            "cpf": flow.cpf,
            "config": {
                "plano_index": plano_index,
                "parcelas": parcelas,
                "dia_vencimento": dia_vencimento,
                "data_primeira_parcela": data_primeira_parcela,
                "estendido": estendido,
                "parcelas_estendido": parcelas_estendido,
                "arrecadacao": arrecadacao,
            },
            "steps": results,
            "passed": sum(1 for r in results if r["status"] == "passed"),
            "failed": sum(1 for r in results if r["status"] == "failed"),
        }, True)


# -- Replanejamento --

@cli.group()
def replanejamento():
    """Financial replanning (renegociacao)."""
    pass


@replanejamento.command("listar")
@click.option("--contrato-id", help="Filter by contract ID")
@click.option("--turma-id", help="Filter by turma ID")
@click.pass_context
def replanejamento_listar(ctx, contrato_id, turma_id):
    """List existing renegociacoes."""
    from cli_anything.hub_portal_vibe.core.replanejamento import list_renegociacoes
    data = list_renegociacoes(contrato_id=contrato_id, turma_id=turma_id)
    _output(data, ctx.obj["json"])


@replanejamento.command("simular")
@click.argument("contrato_id")
@click.option("--parcelas", type=int, default=12, help="Number of installments")
@click.option("--aa/--no-aa", "aa_ativa", default=True,
              help="Include arrecadacao alternativa (default: yes)")
@click.pass_context
def replanejamento_simular(ctx, contrato_id, parcelas, aa_ativa):
    """Simulate a replanning calculation for a contract."""
    from cli_anything.hub_portal_vibe.core.replanejamento import simular_replanejamento
    data = simular_replanejamento(contrato_id, parcelas, aa_ativa=aa_ativa)
    _output(data, ctx.obj["json"])


@replanejamento.command("run")
@click.argument("email")
@click.option("--senha", default="369258Gt@", help="Account password")
@click.option("--headless/--no-headless", default=False)
@click.option("--reports-dir", default=None, help="Directory for screenshots")
@click.option("--parcelas", type=int, default=None,
              help="Number of installments")
@click.option("--estendido/--no-estendido", default=False)
@click.option("--parcelas-estendido", type=int, default=None)
@click.option("--arrecadacao/--no-arrecadacao", default=True)
@click.pass_context
def replanejamento_run(ctx, email, senha, headless, reports_dir,
                        parcelas, estendido, parcelas_estendido, arrecadacao):
    """Run automated replanejamento flow via browser.

    EMAIL is the formando's account email (must have an active contract
    with overdue parcelas).

    \b
    Examples:
      cli-anything-hub-portal-vibe replanejamento run user@email.com
      cli-anything-hub-portal-vibe replanejamento run user@email.com --parcelas 12
    """
    from cli_anything.hub_portal_vibe.core.replanejamento_flow import (
        ReplanejamentoFlow, ReplanejamentoConfig,
    )

    use_json = ctx.obj["json"]

    config = ReplanejamentoConfig()
    config.num_parcelas = parcelas
    config.estendido = estendido
    config.parcelas_estendido = parcelas_estendido
    config.arrecadacao = arrecadacao

    def on_step(num, desc, status, error=None):
        if not use_json:
            icon = click.style("[OK]", fg="green") if status == "passed" \
                else click.style("[FAIL]", fg="red")
            msg = f"  {icon} Step {num}: {desc}"
            if error:
                msg += f" - {click.style(error, fg='yellow')}"
            click.echo(msg)

    flow = ReplanejamentoFlow(
        email=email, senha=senha, headless=headless,
        reports_dir=reports_dir,
        on_step=on_step if not use_json else None,
        config=config,
    )
    results = flow.run()

    if use_json:
        _output({
            "email": email,
            "config": {"parcelas": parcelas, "estendido": estendido,
                        "parcelas_estendido": parcelas_estendido,
                        "arrecadacao": arrecadacao},
            "steps": results,
            "passed": sum(1 for r in results if r["status"] == "passed"),
            "failed": sum(1 for r in results if r["status"] == "failed"),
        }, True)


# -- Rescisao --

@cli.group()
def rescisao():
    """Contract termination (rescisao)."""
    pass


@rescisao.command("listar")
@click.option("--contrato-id", help="Filter by contract ID")
@click.option("--turma-id", help="Filter by turma ID")
@click.pass_context
def rescisao_listar(ctx, contrato_id, turma_id):
    """List existing rescission requests."""
    from cli_anything.hub_portal_vibe.core.rescisao import list_rescisoes
    data = list_rescisoes(contrato_id=contrato_id, turma_id=turma_id)
    _output(data, ctx.obj["json"])


@rescisao.command("simular")
@click.argument("contrato_id")
@click.option("--valor-plano", type=float, required=True, help="Plan value (R$)")
@click.option("--retencao", type=float, default=30, help="Retention % (default: 30)")
@click.option("--desconto-admin", type=float, default=0, help="Admin discount (R$)")
@click.pass_context
def rescisao_simular(ctx, contrato_id, valor_plano, retencao, desconto_admin):
    """Simulate a rescisao calculation for a contract."""
    from cli_anything.hub_portal_vibe.core.rescisao import simular_rescisao
    # Simple single-rule simulation
    regras = [{"diasAntesUltimaParcela": "0", "tipoRetencao": "PERCENTUAL",
               "percentualRetencao": str(retencao)}]
    data = simular_rescisao(
        contrato_id, valor_plano=valor_plano,
        regras_retencao=regras,
        data_ultima_parcela="2028-12-01",
        desconto_admin=desconto_admin,
    )
    _output(data, ctx.obj["json"])


@rescisao.command("run")
@click.argument("email")
@click.option("--senha", default="369258Gt@", help="Account password")
@click.option("--headless/--no-headless", default=False)
@click.option("--reports-dir", default=None, help="Directory for screenshots")
@click.option("--motivo", default="Teste automatizado - rescisao via CLI",
              help="Reason for termination")
@click.pass_context
def rescisao_run(ctx, email, senha, headless, reports_dir, motivo):
    """Run automated rescisao flow via browser.

    EMAIL is the formando's account email (must have an active contract).

    \b
    Examples:
      cli-anything-hub-portal-vibe rescisao run user@email.com
      cli-anything-hub-portal-vibe rescisao run user@email.com --motivo "Mudanca de cidade"
    """
    from cli_anything.hub_portal_vibe.core.rescisao_flow import (
        RescisaoFlow, RescisaoConfig,
    )

    use_json = ctx.obj["json"]

    config = RescisaoConfig()
    config.motivo = motivo

    def on_step(num, desc, status, error=None):
        if not use_json:
            icon = click.style("[OK]", fg="green") if status == "passed" \
                else click.style("[FAIL]", fg="red")
            msg = f"  {icon} Step {num}: {desc}"
            if error:
                msg += f" - {click.style(error, fg='yellow')}"
            click.echo(msg)

    flow = RescisaoFlow(
        email=email, senha=senha, headless=headless,
        reports_dir=reports_dir,
        on_step=on_step if not use_json else None,
        config=config,
    )
    results = flow.run()

    if use_json:
        _output({
            "email": email,
            "motivo": motivo,
            "resultado": flow.resultado_rescisao,
            "steps": results,
            "passed": sum(1 for r in results if r["status"] == "passed"),
            "failed": sum(1 for r in results if r["status"] == "failed"),
        }, True)


# -- Upgrade --

@cli.group()
def upgrade():
    """Plan upgrade (mudanca para plano superior)."""
    pass


@upgrade.command("listar")
@click.option("--contrato-id", help="Filter by contract ID")
@click.option("--turma-id", help="Filter by turma ID")
@click.pass_context
def upgrade_listar(ctx, contrato_id, turma_id):
    """List plan change records."""
    from cli_anything.hub_portal_vibe.core.upgrade import list_mudancas_plano
    data = list_mudancas_plano(contrato_id=contrato_id, turma_id=turma_id, tipo="UPGRADE")
    _output(data, ctx.obj["json"])


@upgrade.command("simular")
@click.argument("contrato_id")
@click.option("--valor-atual", type=float, required=True, help="Current plan value (R$)")
@click.option("--valor-novo", type=float, required=True, help="New plan value (R$)")
@click.option("--parcelas", type=int, default=12, help="Number of installments (default: 12)")
@click.pass_context
def upgrade_simular(ctx, contrato_id, valor_atual, valor_novo, parcelas):
    """Simulate an upgrade calculation for a contract."""
    from cli_anything.hub_portal_vibe.core.upgrade import simular_upgrade
    data = simular_upgrade(contrato_id, valor_atual, valor_novo, parcelas)
    _output(data, ctx.obj["json"])


@upgrade.command("run")
@click.argument("email")
@click.option("--senha", default="369258Gt@", help="Account password")
@click.option("--headless/--no-headless", default=False)
@click.option("--reports-dir", default=None, help="Directory for screenshots")
@click.option("--parcelas", type=int, default=None,
              help="Number of installments")
@click.option("--estendido/--no-estendido", default=False)
@click.option("--parcelas-estendido", type=int, default=None)
@click.option("--arrecadacao/--no-arrecadacao", default=True)
@click.pass_context
def upgrade_run(ctx, email, senha, headless, reports_dir,
                parcelas, estendido, parcelas_estendido, arrecadacao):
    """Run automated upgrade flow via browser.

    EMAIL is the formando's account email (must have an active contract).

    \b
    Examples:
      cli-anything-hub-portal-vibe upgrade run user@email.com
      cli-anything-hub-portal-vibe upgrade run user@email.com --parcelas 24
    """
    from cli_anything.hub_portal_vibe.core.upgrade_flow import (
        UpgradeFlow, UpgradeConfig,
    )

    use_json = ctx.obj["json"]

    config = UpgradeConfig()
    config.parcelas = parcelas
    config.estendido = estendido
    config.parcelas_estendido = parcelas_estendido
    config.arrecadacao = arrecadacao

    def on_step(num, desc, status, error=None):
        if not use_json:
            icon = click.style("[OK]", fg="green") if status == "passed" \
                else click.style("[FAIL]", fg="red")
            msg = f"  {icon} Step {num}: {desc}"
            if error:
                msg += f" - {click.style(error, fg='yellow')}"
            click.echo(msg)

    flow = UpgradeFlow(
        email=email, senha=senha, headless=headless,
        reports_dir=reports_dir,
        on_step=on_step if not use_json else None,
        config=config,
    )
    results = flow.run()

    if use_json:
        _output({
            "email": email,
            "resultado": flow.resultado_upgrade,
            "config": {"parcelas": parcelas, "estendido": estendido,
                        "parcelas_estendido": parcelas_estendido,
                        "arrecadacao": arrecadacao},
            "steps": results,
            "passed": sum(1 for r in results if r["status"] == "passed"),
            "failed": sum(1 for r in results if r["status"] == "failed"),
        }, True)


# -- Downgrade --

@cli.group()
def downgrade():
    """Plan downgrade (mudanca para plano inferior)."""
    pass


@downgrade.command("listar")
@click.option("--contrato-id", help="Filter by contract ID")
@click.option("--turma-id", help="Filter by turma ID")
@click.pass_context
def downgrade_listar(ctx, contrato_id, turma_id):
    """List downgrade records."""
    from cli_anything.hub_portal_vibe.core.downgrade import list_mudancas_plano
    data = list_mudancas_plano(contrato_id=contrato_id, turma_id=turma_id)
    _output(data, ctx.obj["json"])


@downgrade.command("simular")
@click.argument("contrato_id")
@click.option("--valor-atual", type=float, required=True, help="Current plan value (R$)")
@click.option("--valor-novo", type=float, required=True, help="New (lower) plan value (R$)")
@click.option("--parcelas", type=int, default=12, help="Number of installments (default: 12)")
@click.pass_context
def downgrade_simular(ctx, contrato_id, valor_atual, valor_novo, parcelas):
    """Simulate a downgrade calculation for a contract."""
    from cli_anything.hub_portal_vibe.core.downgrade import simular_downgrade
    data = simular_downgrade(contrato_id, valor_atual, valor_novo, parcelas)
    _output(data, ctx.obj["json"])


@downgrade.command("run")
@click.argument("email")
@click.option("--senha", default="369258Gt@", help="Account password")
@click.option("--headless/--no-headless", default=False)
@click.option("--reports-dir", default=None, help="Directory for screenshots")
@click.option("--parcelas", type=int, default=None,
              help="Number of installments")
@click.pass_context
def downgrade_run(ctx, email, senha, headless, reports_dir, parcelas):
    """Run automated downgrade flow via browser.

    EMAIL is the formando's account email (must have an active contract).

    \b
    Examples:
      cli-anything-hub-portal-vibe downgrade run user@email.com
      cli-anything-hub-portal-vibe downgrade run user@email.com --parcelas 12
    """
    from cli_anything.hub_portal_vibe.core.downgrade_flow import (
        DowngradeFlow, DowngradeConfig,
    )

    use_json = ctx.obj["json"]

    config = DowngradeConfig()
    config.parcelas = parcelas

    def on_step(num, desc, status, error=None):
        if not use_json:
            icon = click.style("[OK]", fg="green") if status == "passed" \
                else click.style("[FAIL]", fg="red")
            msg = f"  {icon} Step {num}: {desc}"
            if error:
                msg += f" - {click.style(error, fg='yellow')}"
            click.echo(msg)

    flow = DowngradeFlow(
        email=email, senha=senha, headless=headless,
        reports_dir=reports_dir,
        on_step=on_step if not use_json else None,
        config=config,
    )
    results = flow.run()

    if use_json:
        _output({
            "email": email,
            "resultado": flow.resultado_downgrade,
            "config": {"parcelas": parcelas},
            "steps": results,
            "passed": sum(1 for r in results if r["status"] == "passed"),
            "failed": sum(1 for r in results if r["status"] == "failed"),
        }, True)


def main():
    cli(obj={})


if __name__ == "__main__":
    main()

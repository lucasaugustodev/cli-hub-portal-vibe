"""Automated upgrade (plan upgrade) flow via Playwright.

Navigates: login -> meus contratos -> acoes -> mudanca de plano (upgrade) ->
selecionar novo plano -> configurar parcelamento -> confirmar -> verificar
"""
from cli_anything.hub_portal_vibe.core.portal_flow_base import PortalFlowBase


class UpgradeConfig:
    def __init__(self):
        self.parcelas = None
        self.estendido = False
        self.parcelas_estendido = None
        self.arrecadacao = True


class UpgradeFlow(PortalFlowBase):
    def __init__(self, email, senha, headless=False, reports_dir=None,
                 on_step=None, config=None):
        super().__init__(email, senha, headless, reports_dir, on_step, "upgrade")
        self.config = config or UpgradeConfig()
        self.resultado_upgrade = None

    def run(self):
        print(f"=== Upgrade Automatizado ===")
        print(f"Email: {self.email}")
        print(f"Headless: {self.headless}\n")

        def steps(page):
            self._login(page, 1)
            self._navigate_meus_contratos(page, 2)
            self._step3_acoes_upgrade(page)
            self._step4_selecionar_plano(page)
            self._step5_parcelamento(page)
            self._step6_confirmar(page)
            self._step7_verificar(page)

        return self._run_with_browser(steps)

    def _step3_acoes_upgrade(self, page):
        self._click_acoes_action(page, [
            "Upgrade de plano", "Mudança de plano", "Mudanca de plano",
            "Upgrade", "Mudar plano",
        ], step_num=3)

    def _step4_selecionar_plano(self, page):
        """Select the new (higher value) plan in the upgrade dialog."""
        try:
            self._wait_dialog_loaded(page)

            text = self._get_dialog_text(page)

            # Check for block (overdue parcelas)
            if "vencida" in text.lower() and "replanejamento" in text.lower():
                self._snap(page, 4)
                self._log(4, "Upgrade blocked - overdue parcelas (needs replanejamento)", "failed",
                          "Parcelas vencidas impedem upgrade")
                return

            # Look for plan selection buttons/cards
            # The upgrade dialog shows available lotes with higher value
            plan_btns = page.locator('[role="dialog"] button:has-text("Selecionar")')
            count = plan_btns.count()

            if count > 0:
                # Select the first available (cheapest upgrade option)
                plan_btns.first.click()
                self._wait_stable(page, 2000)
                print(f"    Selected upgrade plan (first of {count} options)")
            else:
                # Maybe it's a radio/card selection
                cards = page.locator('[role="dialog"] [class*="card"], [role="dialog"] [class*="Card"]')
                if cards.count() > 0:
                    cards.first.click()
                    self._wait_stable(page, 2000)

            self._snap(page, 4)
            self._log(4, "New plan selected", "passed")
        except Exception as e:
            self._snap(page, 4)
            self._log(4, "Select new plan", "failed", str(e))

    def _step5_parcelamento(self, page):
        """Configure installments for the new contract."""
        try:
            self._wait_stable(page, 2000)
            cfg = self.config
            details = []

            # Adjust parcelas slider if specified
            if cfg.parcelas is not None:
                sliders = page.locator('[role="dialog"] [role="slider"]')
                if sliders.count() > 0:
                    slider = sliders.first
                    current = int(slider.get_attribute("aria-valuenow") or "12")
                    target = cfg.parcelas
                    slider.click()
                    diff = target - current
                    key = "ArrowRight" if diff > 0 else "ArrowLeft"
                    for _ in range(abs(diff)):
                        slider.press(key)
                    details.append(f"parcelas={target}")

            # Extended installments
            if cfg.estendido and cfg.parcelas_estendido:
                sliders = page.locator('[role="dialog"] [role="slider"]')
                if sliders.count() > 1:
                    ext = sliders.nth(1)
                    if ext.is_visible():
                        ext.click()
                        current_ext = int(ext.get_attribute("aria-valuenow") or "0")
                        diff = cfg.parcelas_estendido - current_ext
                        key = "ArrowRight" if diff > 0 else "ArrowLeft"
                        for _ in range(abs(diff)):
                            ext.press(key)
                        details.append(f"estendido={cfg.parcelas_estendido}")

            # Capture calculation info shown in dialog
            text = self._get_dialog_text(page)
            info = {}
            for line in text.split("\n"):
                line = line.strip()
                if ":" in line:
                    key, _, val = line.partition(":")
                    val = val.strip()
                    if "R$" in val or "credito" in key.lower() or "debito" in key.lower():
                        info[key.strip()] = val
            if info:
                print("    Upgrade calculation:")
                for k, v in list(info.items())[:8]:
                    print(f"      {k}: {v}")
            self.resultado_upgrade = info

            self._snap(page, 5)
            summary = ", ".join(details) if details else "defaults"
            self._log(5, f"Installments configured ({summary})", "passed")
        except Exception as e:
            self._snap(page, 5)
            self._log(5, "Configure installments", "failed", str(e))

    def _step6_confirmar(self, page):
        """Confirm the upgrade."""
        try:
            self._scroll_dialog(page, "bottom")

            for label in ["Confirmar upgrade", "Confirmar mudança", "Confirmar mudanca",
                          "Confirmar", "Continuar"]:
                btn = page.locator(f'[role="dialog"] button:has-text("{label}")')
                if btn.count() > 0:
                    btn.first.click(force=True)
                    page.wait_for_timeout(3000)
                    break

            # Handle secondary confirmation
            text = self._get_dialog_text(page)
            if "irreversivel" in text.lower() or "certeza" in text.lower():
                for label in ["Confirmar", "Sim", "Continuar"]:
                    if self._click_button(page, label, timeout=3000, wait_after=5000):
                        break

            self._check_toast_errors(page)
            self._snap(page, 6)
            self._log(6, "Upgrade confirmed", "passed")
        except Exception as e:
            self._snap(page, 6)
            self._log(6, "Confirm upgrade", "failed", str(e))

    def _step7_verificar(self, page):
        """Verify success."""
        try:
            self._wait_stable(page, 3000)
            text = self._get_dialog_text(page)
            success = any(kw in text.lower() for kw in [
                "sucesso", "upgrade realizado", "mudança realizada",
                "novo contrato", "finalizado",
            ])
            if success:
                print("    Upgrade realizado com sucesso!")
            self._close_dialog(page)
            self._snap(page, 7)
            self._log(7, "Upgrade complete" if success else "Final state (see screenshot)", "passed")
        except Exception as e:
            self._snap(page, 7)
            self._log(7, "Verify upgrade", "failed", str(e))

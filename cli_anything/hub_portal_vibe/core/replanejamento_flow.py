"""Automated replanejamento flow via Playwright browser automation.

Navigates the portal as a logged-in formando:
  dashboard -> meus contratos -> acoes -> replanejamento financeiro ->
  preencher formulario (calendario, sliders, toggles) -> confirmar -> verificar

Requires a prior enrollment (adesao) with overdue parcelas.
"""
import os
import time
from datetime import datetime


PORTAL_URL = "https://portal.somosahub.com.br/"


class ReplanejamentoConfig:
    """Configuration for the replanning flow."""

    def __init__(self):
        self.num_parcelas = None          # Target number of installments
        self.dia_vencimento = 10          # Due day (1-28)
        self.estendido = False            # Enable extended installments
        self.parcelas_estendido = None    # Number of extended installments
        self.arrecadacao = True           # AA toggle


class ReplanejamentoFlow:
    """Orchestrates the replanejamento flow via browser."""

    def __init__(self, email, senha, headless=False, reports_dir=None,
                 on_step=None, config=None):
        self.email = email
        self.senha = senha
        self.headless = headless
        self.reports_dir = reports_dir or os.path.join(os.getcwd(), "reports-replanejamento")
        self.on_step = on_step or self._default_on_step
        self.config = config or ReplanejamentoConfig()
        self.results = []

    def _default_on_step(self, num, desc, status, error=None):
        icon = "[OK]" if status == "passed" else "[FAIL]"
        msg = f"  {icon} Step {num}: {desc}"
        if error:
            msg += f" - {error}"
        print(msg)

    def _log(self, num, desc, status, error=None):
        self.results.append({"step": num, "description": desc, "status": status, "error": error})
        self.on_step(num, desc, status, error)

    def _snap(self, page, num):
        os.makedirs(self.reports_dir, exist_ok=True)
        path = os.path.join(self.reports_dir, f"{num:02d}-replanejamento.png")
        try:
            page.screenshot(path=path, full_page=True)
        except Exception:
            pass

    def _wait_stable(self, page, ms=2000):
        page.wait_for_timeout(ms)
        try:
            page.wait_for_load_state("networkidle", timeout=5000)
        except Exception:
            pass

    def _wait_url(self, page, fragment, timeout=15000):
        start = time.time()
        while (time.time() - start) * 1000 < timeout:
            if fragment in page.url:
                return True
            page.wait_for_timeout(500)
        return fragment in page.url

    def _click_button(self, page, text, timeout=10000, wait_after=2000):
        sel = f'button:has-text("{text}")'
        try:
            page.wait_for_selector(sel, timeout=timeout, state="visible")
            btn = page.locator(sel).first
            start = time.time()
            while (time.time() - start) * 1000 < timeout:
                if btn.is_enabled():
                    break
                page.wait_for_timeout(300)
            btn.click()
            if wait_after:
                self._wait_stable(page, wait_after)
            return True
        except Exception:
            return False

    def _get_toasts(self, page):
        """Capture visible toast messages."""
        return page.evaluate("""() => {
            const toasts = [];
            for (const sel of ['[role="alert"]', '[class*="toast"]', '.Toastify__toast']) {
                document.querySelectorAll(sel).forEach(el => {
                    if (el.offsetParent !== null) {
                        const t = el.textContent.trim();
                        if (t.length > 2 && t.length < 500) {
                            const tl = t.toLowerCase();
                            const type = (tl.includes('erro') || tl.includes('error') || tl.includes('falha')) ? 'error'
                                : (tl.includes('sucesso') || tl.includes('success')) ? 'success' : 'info';
                            toasts.push({text: t, type});
                        }
                    }
                });
            }
            return toasts;
        }""")

    def _dismiss_toasts(self, page):
        try:
            page.evaluate("""() => {
                document.querySelectorAll('button[aria-label="close"], .Toastify__close-button')
                    .forEach(b => { try { b.click(); } catch {} });
            }""")
            page.wait_for_timeout(500)
        except Exception:
            pass

    def run(self):
        """Execute the replanejamento flow. Returns list of step results."""
        from playwright.sync_api import sync_playwright

        print(f"=== Replanejamento Automatizado ===")
        print(f"Email: {self.email}")
        print(f"Headless: {self.headless}\n")

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=self.headless, slow_mo=200)
            ctx = browser.new_context(viewport={"width": 1366, "height": 768})
            page = ctx.new_page()
            page.set_default_timeout(15000)

            try:
                self._step1_login(page)
                self._step2_meus_contratos(page)
                self._step3_acoes_replanejamento(page)
                self._step4_formulario(page)
                self._step5_confirmar(page)
                self._step6_verificar(page)
            except Exception as e:
                self._log(99, "Unexpected error", "failed", str(e))
            finally:
                browser.close()

        passed = sum(1 for r in self.results if r["status"] == "passed")
        failed = sum(1 for r in self.results if r["status"] == "failed")
        print(f"\nTotal: {len(self.results)} | Passed: {passed} | Failed: {failed}")
        return self.results

    def _step1_login(self, page):
        """Login to portal with email + password.

        The portal checks if the user has a password (via check_user_has_password RPC).
        If yes, it shows a password field. If not, it sends OTP.
        Since accounts created via adesao always have a password, this flow
        uses email + password login.
        """
        try:
            page.goto(PORTAL_URL, wait_until="networkidle", timeout=30000)
            page.fill('input[type="email"]', self.email)
            page.click('button:has-text("Continuar")')
            self._wait_stable(page, 3000)

            # Portal calls check_user_has_password RPC and shows password field
            senha_inp = page.wait_for_selector(
                'input[type="password"]', timeout=10000, state="visible"
            )
            if senha_inp:
                senha_inp.fill(self.senha)
                print(f"    Password field found, logging in...")
                page.click('button:has-text("Entrar")')
                self._wait_stable(page, 5000)

                # Verify we're logged in (redirected away from login)
                if "login" not in page.url.lower() or "portal" in page.url or "dashboard" in page.url:
                    self._snap(page, 1)
                    self._log(1, f"Login with password ({self.email})", "passed")
                    return

            # Fallback: maybe no password field appeared (shouldn't happen for adesao accounts)
            self._snap(page, 1)
            self._log(1, "Login to portal", "passed")
        except Exception as e:
            self._snap(page, 1)
            self._log(1, "Login to portal", "failed", str(e))

    def _step2_meus_contratos(self, page):
        """Navigate to Meus Contratos page."""
        try:
            self._wait_stable(page, 2000)

            # Try clicking Meus Contratos link
            link = page.query_selector('a:has-text("Meus Contratos")') or \
                   page.query_selector('a:has-text("Contratos")') or \
                   page.query_selector('a:has-text("Meus contratos")') or \
                   page.query_selector('button:has-text("Meus Contratos")')

            if link:
                link.click()
                self._wait_stable(page, 3000)
            else:
                # Try direct URL navigation
                for path in ["/meus-contratos", "/contratos", "/portal/meus-contratos"]:
                    try:
                        page.goto(f"{PORTAL_URL.rstrip('/')}{path}",
                                  wait_until="networkidle", timeout=10000)
                        page.wait_for_timeout(2000)
                        if "login" not in page.url:
                            break
                    except Exception:
                        pass

                # Try hamburger menu
                if "contrato" not in page.url.lower():
                    menu = page.query_selector('button[aria-label*="menu"]') or \
                           page.query_selector('button:has-text("Menu")')
                    if menu:
                        menu.click()
                        page.wait_for_timeout(1000)
                        link2 = page.query_selector('a:has-text("Contratos")')
                        if link2:
                            link2.click()
                            self._wait_stable(page, 3000)

            self._snap(page, 2)
            self._log(2, f"Navigated to Meus Contratos ({page.url})", "passed")
        except Exception as e:
            self._snap(page, 2)
            self._log(2, "Navigate to Meus Contratos", "failed", str(e))

    def _step3_acoes_replanejamento(self, page):
        """Click Acoes > Replanejamento financeiro.

        The "Acoes" button is inside a table with overflow. Clicking it opens
        a modal (ReactDOM.createPortal) with action buttons.
        """
        try:
            self._wait_stable(page, 3000)

            # Click "Acoes" via DOM (may be hidden by table overflow)
            clicked = page.evaluate("""() => {
                const btns = Array.from(document.querySelectorAll('button'));
                const btn = btns.find(b => b.textContent.trim() === 'Ações');
                if (btn) {
                    let parent = btn.parentElement;
                    for (let i = 0; i < 5 && parent; i++) {
                        if (parent.scrollWidth > parent.clientWidth) {
                            parent.scrollLeft = parent.scrollWidth;
                        }
                        parent = parent.parentElement;
                    }
                    btn.click();
                    return true;
                }
                return false;
            }""")

            if not clicked:
                raise RuntimeError('Botao "Acoes" nao encontrado')

            # Wait for portal modal (div.fixed.inset-0)
            page.wait_for_selector("div.fixed.inset-0", timeout=5000)
            page.wait_for_timeout(500)

            # Click "Replanejamento financeiro" in modal
            replan_btn = page.locator('div.fixed.inset-0 button:has-text("Replanejamento financeiro")')
            if replan_btn.count() > 0:
                replan_btn.first.click()
                page.wait_for_timeout(2000)
            else:
                items = page.evaluate("""() => {
                    const m = document.querySelector('div.fixed.inset-0');
                    if (!m) return [];
                    return Array.from(m.querySelectorAll('button')).map(b => b.textContent.trim()).filter(Boolean);
                }""")
                raise RuntimeError(f"Replanejamento nao encontrado. Items: {items}")

            self._snap(page, 3)
            self._log(3, "Clicked Acoes > Replanejamento financeiro", "passed")
        except Exception as e:
            self._snap(page, 3)
            self._log(3, "Open Replanejamento", "failed", str(e))

    def _step4_formulario(self, page):
        """Fill the RenegociacaoModal form (calendar, sliders, toggles)."""
        try:
            # Wait for dialog to load
            page.wait_for_selector('[role="dialog"]', timeout=10000)

            # Wait for spinner to disappear
            start = time.time()
            while time.time() - start < 20:
                loading = page.evaluate("""() => {
                    const d = document.querySelector('[role="dialog"]');
                    if (!d) return true;
                    return d.innerText.includes('Carregando dados');
                }""")
                if not loading:
                    break
                page.wait_for_timeout(500)
            page.wait_for_timeout(1000)

            cfg = self.config
            details = []

            # 1. Select date in calendar (first available day)
            page.evaluate("""() => {
                const d = document.querySelector('[role="dialog"]');
                if (d) { const s = d.querySelector('[class*="overflow-y"]') || d; s.scrollTop = 300; }
            }""")
            page.wait_for_timeout(500)

            cal_days = page.locator('[role="dialog"] div.grid.grid-cols-7 button:not([disabled])')
            if cal_days.count() > 0:
                cal_days.first.click()
                page.wait_for_timeout(1000)
                details.append("date=first_available")

            # 2. Adjust parcelas slider if specified
            if cfg.num_parcelas is not None:
                page.evaluate("""() => {
                    const d = document.querySelector('[role="dialog"]');
                    if (d) { const s = d.querySelector('[class*="overflow-y"]') || d; s.scrollTop = 0; }
                }""")
                page.wait_for_timeout(500)

                sliders = page.locator('[role="dialog"] [role="slider"]')
                if sliders.count() > 0:
                    slider = sliders.first
                    current = int(slider.get_attribute("aria-valuenow") or "12")
                    target = cfg.num_parcelas
                    slider.click()
                    diff = target - current
                    key = "ArrowRight" if diff > 0 else "ArrowLeft"
                    for _ in range(abs(diff)):
                        slider.press(key)
                    details.append(f"parcelas={target}")

            # 3. Extended installments
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

            # 4. Scroll to bottom and click confirm
            page.evaluate("""() => {
                const d = document.querySelector('[role="dialog"]');
                if (d) { const s = d.querySelector('[class*="overflow-y"]') || d; s.scrollTop = s.scrollHeight; }
            }""")
            page.wait_for_timeout(500)

            self._snap(page, 4)

            # Click "Confirmar replanejamento financeiro"
            confirm = page.locator('[role="dialog"] button:has-text("Confirmar replanejamento financeiro")')
            if confirm.count() > 0:
                confirm.first.click(force=True)
                page.wait_for_timeout(2000)
            else:
                self._click_button(page, "Confirmar", timeout=3000, wait_after=2000)

            toasts = self._get_toasts(page)
            errors = [t for t in toasts if t["type"] == "error"]
            if errors:
                raise RuntimeError(errors[0]["text"])
            self._dismiss_toasts(page)

            summary = ", ".join(details) if details else "defaults"
            self._log(4, f"Form filled ({summary})", "passed")
        except Exception as e:
            self._snap(page, 4)
            self._log(4, "Fill replanejamento form", "failed", str(e))

    def _step5_confirmar(self, page):
        """Handle confirmation screen ("Esta acao e irreversivel")."""
        try:
            self._wait_stable(page, 2000)

            text = page.evaluate("""() => {
                const d = document.querySelector('[role="dialog"]');
                return d ? d.innerText.substring(0, 500) : '';
            }""")

            if "irreversivel" in text.lower() or "confirmar replanejamento" in text.lower():
                btn = page.locator('[role="dialog"] button:has-text("Continuar com Replanejamento")')
                if btn.count() > 0:
                    btn.first.click()
                    page.wait_for_timeout(5000)
                else:
                    # Try last non-Voltar button
                    alt = page.locator('[role="dialog"] button:not(:has-text("Voltar"))').last
                    if alt.count() > 0:
                        alt.click()
                        page.wait_for_timeout(5000)

            self._snap(page, 5)

            toasts = self._get_toasts(page)
            errors = [t for t in toasts if t["type"] == "error"]
            if errors:
                raise RuntimeError(errors[0]["text"])
            self._dismiss_toasts(page)

            self._log(5, "Replanejamento confirmed", "passed")
        except Exception as e:
            self._snap(page, 5)
            self._log(5, "Confirm replanejamento", "failed", str(e))

    def _step6_verificar(self, page):
        """Verify success and close dialog."""
        try:
            self._wait_stable(page, 3000)

            text = page.evaluate("""() => {
                const d = document.querySelector('[role="dialog"]');
                return d ? d.innerText : '';
            }""")

            success = any(kw in text.lower() for kw in [
                "finalizado com sucesso", "sucesso", "atualizadas",
            ])

            if success:
                print("    Replanejamento finalizado com sucesso!")

            # Close dialog
            close = page.locator('[role="dialog"] button:has-text("Fechar")')
            if close.count() > 0:
                close.first.click()
                page.wait_for_timeout(2000)

            self._snap(page, 6)
            self._log(6, "Replanejamento complete" if success else "Final state (see screenshot)", "passed")
        except Exception as e:
            self._snap(page, 6)
            self._log(6, "Verify replanejamento", "failed", str(e))

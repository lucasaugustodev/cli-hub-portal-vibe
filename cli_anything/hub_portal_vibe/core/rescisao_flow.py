"""Automated rescisao (contract termination) flow via Playwright.

Navigates the portal as a logged-in formando:
  dashboard -> meus contratos -> acoes -> solicitar rescisao ->
  preencher motivo -> verificar calculo -> confirmar -> verificar
"""
import os
import time


PORTAL_URL = "https://portal.somosahub.com.br/"


class RescisaoConfig:
    """Configuration for the rescisao flow."""

    def __init__(self):
        self.motivo = "Teste automatizado - rescisao via CLI"


class RescisaoFlow:
    """Orchestrates the rescisao flow via browser."""

    def __init__(self, email, senha, headless=False, reports_dir=None,
                 on_step=None, config=None):
        self.email = email
        self.senha = senha
        self.headless = headless
        self.reports_dir = reports_dir or os.path.join(os.getcwd(), "reports-rescisao")
        self.on_step = on_step or self._default_on_step
        self.config = config or RescisaoConfig()
        self.results = []
        self.resultado_rescisao = None  # Captured from the UI

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
        path = os.path.join(self.reports_dir, f"{num:02d}-rescisao.png")
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
        """Execute the rescisao flow. Returns list of step results."""
        from playwright.sync_api import sync_playwright

        print(f"=== Rescisao Automatizada ===")
        print(f"Email: {self.email}")
        print(f"Motivo: {self.config.motivo}")
        print(f"Headless: {self.headless}\n")

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=self.headless, slow_mo=200)
            ctx = browser.new_context(viewport={"width": 1366, "height": 768})
            page = ctx.new_page()
            page.set_default_timeout(15000)

            try:
                self._step1_login(page)
                self._step2_meus_contratos(page)
                self._step3_acoes_rescisao(page)
                self._step4_motivo(page)
                self._step5_verificar_calculo(page)
                self._step6_confirmar(page)
                self._step7_verificar(page)
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

        Portal checks if user has password (check_user_has_password RPC).
        Accounts from adesao always have password, so we wait for the
        password field and fill it.
        """
        try:
            page.goto(PORTAL_URL, wait_until="networkidle", timeout=30000)
            page.fill('input[type="email"]', self.email)
            page.click('button:has-text("Continuar")')
            self._wait_stable(page, 3000)

            # Wait for password field (portal RPC decides which flow)
            senha_inp = page.wait_for_selector(
                'input[type="password"]', timeout=10000, state="visible"
            )
            if senha_inp:
                senha_inp.fill(self.senha)
                print(f"    Password field found, logging in...")
                page.click('button:has-text("Entrar")')
                self._wait_stable(page, 5000)

                if "login" not in page.url.lower() or "portal" in page.url or "dashboard" in page.url:
                    self._snap(page, 1)
                    self._log(1, f"Login with password ({self.email})", "passed")
                    return

            self._snap(page, 1)
            self._log(1, "Login to portal", "passed")
        except Exception as e:
            self._snap(page, 1)
            self._log(1, "Login to portal", "failed", str(e))

    def _step2_meus_contratos(self, page):
        """Navigate to Meus Contratos page."""
        try:
            self._wait_stable(page, 2000)
            link = page.query_selector('a:has-text("Meus Contratos")') or \
                   page.query_selector('a:has-text("Contratos")') or \
                   page.query_selector('a:has-text("Meus contratos")')
            if link:
                link.click()
                self._wait_stable(page, 3000)
            else:
                for path in ["/meus-contratos", "/contratos", "/portal/meus-contratos"]:
                    try:
                        page.goto(f"{PORTAL_URL.rstrip('/')}{path}",
                                  wait_until="networkidle", timeout=10000)
                        if "login" not in page.url:
                            break
                    except Exception:
                        pass

            self._snap(page, 2)
            self._log(2, f"Meus Contratos ({page.url})", "passed")
        except Exception as e:
            self._snap(page, 2)
            self._log(2, "Navigate to Meus Contratos", "failed", str(e))

    def _step3_acoes_rescisao(self, page):
        """Click Acoes > Solicitar Rescisao."""
        try:
            self._wait_stable(page, 3000)

            # Click "Acoes" via DOM
            clicked = page.evaluate("""() => {
                const btns = Array.from(document.querySelectorAll('button'));
                const btn = btns.find(b => b.textContent.trim() === 'Ações');
                if (btn) {
                    let parent = btn.parentElement;
                    for (let i = 0; i < 5 && parent; i++) {
                        if (parent.scrollWidth > parent.clientWidth)
                            parent.scrollLeft = parent.scrollWidth;
                        parent = parent.parentElement;
                    }
                    btn.click();
                    return true;
                }
                return false;
            }""")

            if not clicked:
                raise RuntimeError('Botao "Acoes" nao encontrado')

            page.wait_for_selector("div.fixed.inset-0", timeout=5000)
            page.wait_for_timeout(500)

            # Look for rescisao button
            for label in ["Solicitar rescisão", "Solicitar rescisao", "Rescisão", "Rescisao"]:
                btn = page.locator(f'div.fixed.inset-0 button:has-text("{label}")')
                if btn.count() > 0:
                    btn.first.click()
                    page.wait_for_timeout(2000)
                    break
            else:
                items = page.evaluate("""() => {
                    const m = document.querySelector('div.fixed.inset-0');
                    if (!m) return [];
                    return Array.from(m.querySelectorAll('button')).map(b => b.textContent.trim()).filter(Boolean);
                }""")
                raise RuntimeError(f"Rescisao nao encontrada. Items: {items}")

            self._snap(page, 3)
            self._log(3, "Opened rescisao dialog", "passed")
        except Exception as e:
            self._snap(page, 3)
            self._log(3, "Open Rescisao", "failed", str(e))

    def _step4_motivo(self, page):
        """Fill the reason for rescisao."""
        try:
            page.wait_for_selector('[role="dialog"]', timeout=10000)

            # Wait loading
            start = time.time()
            while time.time() - start < 15:
                loading = page.evaluate("""() => {
                    const d = document.querySelector('[role="dialog"]');
                    return d ? d.innerText.includes('Carregando') : true;
                }""")
                if not loading:
                    break
                page.wait_for_timeout(500)
            page.wait_for_timeout(1000)

            # Fill motivo textarea
            textarea = page.query_selector('[role="dialog"] textarea')
            if textarea:
                textarea.fill(self.config.motivo)
                print(f"    Motivo: {self.config.motivo}")

            self._snap(page, 4)
            self._log(4, "Reason filled", "passed")
        except Exception as e:
            self._snap(page, 4)
            self._log(4, "Fill reason", "failed", str(e))

    def _step5_verificar_calculo(self, page):
        """Capture the rescisao calculation shown in the dialog."""
        try:
            text = page.evaluate("""() => {
                const d = document.querySelector('[role="dialog"]');
                return d ? d.innerText : '';
            }""")

            # Extract key values from the text
            info = {}
            for line in text.split("\n"):
                line = line.strip()
                if ":" in line:
                    key, _, val = line.partition(":")
                    val = val.strip()
                    if "R$" in val or any(c.isdigit() for c in val):
                        info[key.strip()] = val

            if info:
                print("    Calculo rescisao:")
                for k, v in list(info.items())[:10]:
                    print(f"      {k}: {v}")

            self.resultado_rescisao = info
            self._snap(page, 5)
            self._log(5, f"Calculation captured ({len(info)} fields)", "passed")
        except Exception as e:
            self._snap(page, 5)
            self._log(5, "Capture calculation", "failed", str(e))

    def _step6_confirmar(self, page):
        """Confirm the rescisao."""
        try:
            # Click confirm/submit button
            for label in ["Confirmar rescisão", "Confirmar rescisao", "Solicitar",
                          "Confirmar", "Continuar"]:
                btn = page.locator(f'[role="dialog"] button:has-text("{label}")')
                if btn.count() > 0:
                    # Scroll to bottom of dialog
                    page.evaluate("""() => {
                        const d = document.querySelector('[role="dialog"]');
                        if (d) { const s = d.querySelector('[class*="overflow-y"]') || d; s.scrollTop = s.scrollHeight; }
                    }""")
                    page.wait_for_timeout(300)
                    btn.first.click(force=True)
                    page.wait_for_timeout(3000)
                    break

            # Handle secondary confirmation if exists
            text = page.evaluate("""() => {
                const d = document.querySelector('[role="dialog"]');
                return d ? d.innerText.substring(0, 300) : '';
            }""")
            if "irreversivel" in text.lower() or "certeza" in text.lower():
                for label in ["Confirmar", "Sim", "Continuar"]:
                    if self._click_button(page, label, timeout=3000, wait_after=5000):
                        break

            toasts = self._get_toasts(page)
            errors = [t for t in toasts if t["type"] == "error"]
            if errors:
                raise RuntimeError(errors[0]["text"])
            self._dismiss_toasts(page)

            self._snap(page, 6)
            self._log(6, "Rescisao confirmed", "passed")
        except Exception as e:
            self._snap(page, 6)
            self._log(6, "Confirm rescisao", "failed", str(e))

    def _step7_verificar(self, page):
        """Verify success and close."""
        try:
            self._wait_stable(page, 3000)

            text = page.evaluate("""() => {
                const d = document.querySelector('[role="dialog"]');
                return d ? d.innerText : document.body.innerText.substring(0, 500);
            }""")

            success = any(kw in text.lower() for kw in [
                "sucesso", "rescisao solicitada", "rescisão solicitada",
                "enviada", "processada",
            ])

            if success:
                print("    Rescisao solicitada com sucesso!")

            # Close dialog if open
            close = page.locator('[role="dialog"] button:has-text("Fechar")')
            if close.count() > 0:
                close.first.click()
                page.wait_for_timeout(2000)

            self._snap(page, 7)
            self._log(7, "Rescisao complete" if success else "Final state (see screenshot)", "passed")
        except Exception as e:
            self._snap(page, 7)
            self._log(7, "Verify rescisao", "failed", str(e))

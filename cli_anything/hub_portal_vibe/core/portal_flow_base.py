"""Base class for portal browser automation flows.

Provides shared login, navigation, and utility methods used by
replanejamento, rescisao, upgrade, and downgrade flows.
"""
import os
import time

PORTAL_URL = "https://portal.somosahub.com.br/"


class PortalFlowBase:
    """Base class with common browser automation methods."""

    def __init__(self, email, senha, headless=False, reports_dir=None,
                 on_step=None, flow_name="flow"):
        self.email = email
        self.senha = senha
        self.headless = headless
        self.reports_dir = reports_dir or os.path.join(os.getcwd(), f"reports-{flow_name}")
        self.on_step = on_step or self._default_on_step
        self.flow_name = flow_name
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
        path = os.path.join(self.reports_dir, f"{num:02d}-{self.flow_name}.png")
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
                            const type = (tl.includes('erro') || tl.includes('error')) ? 'error'
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

    def _check_toast_errors(self, page):
        """Check for error toasts, raise if found."""
        toasts = self._get_toasts(page)
        errors = [t for t in toasts if t["type"] == "error"]
        self._dismiss_toasts(page)
        if errors:
            raise RuntimeError(errors[0]["text"])

    def _login(self, page, step_num=1):
        """Login to portal with email + password.

        Portal checks if user has password (check_user_has_password RPC).
        Accounts from adesao always have password.
        """
        try:
            page.goto(PORTAL_URL, wait_until="networkidle", timeout=30000)
            page.fill('input[type="email"]', self.email)
            page.click('button:has-text("Continuar")')
            self._wait_stable(page, 3000)

            senha_inp = page.wait_for_selector(
                'input[type="password"]', timeout=10000, state="visible"
            )
            if senha_inp:
                senha_inp.fill(self.senha)
                print(f"    Logging in with password...")
                page.click('button:has-text("Entrar")')
                self._wait_stable(page, 5000)

            self._snap(page, step_num)
            self._log(step_num, f"Login ({self.email})", "passed")
        except Exception as e:
            self._snap(page, step_num)
            self._log(step_num, "Login", "failed", str(e))

    def _navigate_meus_contratos(self, page, step_num=2):
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

            self._snap(page, step_num)
            self._log(step_num, f"Meus Contratos ({page.url})", "passed")
        except Exception as e:
            self._snap(page, step_num)
            self._log(step_num, "Navigate to Meus Contratos", "failed", str(e))

    def _click_acoes_action(self, page, action_label, step_num=3):
        """Click Acoes button in table, then select an action from the modal.

        action_label: text to find in the modal buttons (e.g. "Replanejamento financeiro")
        """
        try:
            self._wait_stable(page, 3000)

            # Click "Acoes" via DOM (may be hidden by table overflow)
            clicked = page.evaluate("""() => {
                const btns = Array.from(document.querySelectorAll('button'));
                const btn = btns.find(b => b.textContent.trim() === 'Ações');
                if (btn) {
                    let p = btn.parentElement;
                    for (let i = 0; i < 5 && p; i++) {
                        if (p.scrollWidth > p.clientWidth) p.scrollLeft = p.scrollWidth;
                        p = p.parentElement;
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

            # Try multiple label variants
            labels = [action_label] if isinstance(action_label, str) else action_label
            found = False
            for label in labels:
                btn = page.locator(f'div.fixed.inset-0 button:has-text("{label}")')
                if btn.count() > 0:
                    btn.first.click()
                    page.wait_for_timeout(2000)
                    found = True
                    break

            if not found:
                items = page.evaluate("""() => {
                    const m = document.querySelector('div.fixed.inset-0');
                    return m ? Array.from(m.querySelectorAll('button')).map(b => b.textContent.trim()).filter(Boolean) : [];
                }""")
                raise RuntimeError(f"Action not found. Available: {items}")

            self._snap(page, step_num)
            self._log(step_num, f"Acoes > {labels[0]}", "passed")
        except Exception as e:
            self._snap(page, step_num)
            self._log(step_num, f"Open {labels[0] if isinstance(labels, list) else action_label}", "failed", str(e))

    def _wait_dialog_loaded(self, page, timeout=20):
        """Wait for dialog to appear and loading to finish."""
        page.wait_for_selector('[role="dialog"]', timeout=10000)
        start = time.time()
        while time.time() - start < timeout:
            loading = page.evaluate("""() => {
                const d = document.querySelector('[role="dialog"]');
                if (!d) return true;
                return d.innerText.includes('Carregando dados') || d.innerText.includes('Carregando');
            }""")
            if not loading:
                break
            page.wait_for_timeout(500)
        page.wait_for_timeout(1000)

    def _get_dialog_text(self, page):
        """Get text content of the current dialog."""
        return page.evaluate("""() => {
            const d = document.querySelector('[role="dialog"]');
            return d ? d.innerText : '';
        }""")

    def _scroll_dialog(self, page, position="bottom"):
        """Scroll dialog content."""
        scroll_val = "scrollHeight" if position == "bottom" else "0"
        page.evaluate(f"""() => {{
            const d = document.querySelector('[role="dialog"]');
            if (d) {{
                const s = d.querySelector('[class*="overflow-y"]') || d;
                s.scrollTop = s.{scroll_val};
            }}
        }}""")
        page.wait_for_timeout(300)

    def _close_dialog(self, page):
        """Close dialog if open."""
        close = page.locator('[role="dialog"] button:has-text("Fechar")')
        if close.count() > 0:
            close.first.click()
            page.wait_for_timeout(2000)

    def _run_with_browser(self, steps_fn):
        """Run steps inside a browser session. Returns results list."""
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=self.headless, slow_mo=200)
            ctx = browser.new_context(viewport={"width": 1366, "height": 768})
            page = ctx.new_page()
            page.set_default_timeout(15000)

            try:
                steps_fn(page)
            except Exception as e:
                self._log(99, "Unexpected error", "failed", str(e))
            finally:
                browser.close()

        passed = sum(1 for r in self.results if r["status"] == "passed")
        failed = sum(1 for r in self.results if r["status"] == "failed")
        print(f"\nTotal: {len(self.results)} | Passed: {passed} | Failed: {failed}")
        return self.results

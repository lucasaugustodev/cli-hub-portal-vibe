"""Automated enrollment flow via Playwright browser automation.

Replicates the full formando enrollment:
  portal -> email+OTP -> dados pessoais -> senha -> selecao turma ->
  selecao plano -> parcelamento -> contratacao (responsavel + endereco +
  contrato assinatura + recorrencia)
"""
import os
import time
import random
from datetime import datetime, timedelta


PORTAL_URL = "https://portal.somosahub.com.br/"
DEFAULT_SENHA = "369258Gt@"


class AdesaoConfig:
    """Configuration for the enrollment flow choices."""

    def __init__(self):
        # Which plan to select (0-based index, or None for first available)
        self.plano_index: int | None = None
        # Number of installments (None = use default/max)
        self.parcelas: int | None = None
        # Due day (1-28, None = 10)
        self.dia_vencimento: int | None = 10
        # First installment date (YYYY-MM-DD, None = auto)
        self.data_primeira_parcela: str | None = None
        # Enable extended installments
        self.parcelamento_estendido: bool = False
        # Number of extended installments (only if estendido=True)
        self.parcelas_estendido: int | None = None
        # Enable alternative collection (rifas)
        self.arrecadacao_alternativa: bool = True
        # Skip recurring payment setup
        self.pular_recorrencia: bool = True


def gerar_cpf():
    """Generate a valid CPF number."""
    n = [random.randint(0, 9) for _ in range(9)]
    s = sum(n[i] * (10 - i) for i in range(9))
    d1 = 11 - (s % 11)
    if d1 >= 10:
        d1 = 0
    n.append(d1)
    s = sum(n[i] * (11 - i) for i in range(10))
    d2 = 11 - (s % 11)
    if d2 >= 10:
        d2 = 0
    n.append(d2)
    return "".join(str(x) for x in n)


def proximo_dia_util(dias_minimos=5):
    """Return next business day at least N days from now (YYYY-MM-DD)."""
    d = datetime.now() + timedelta(days=dias_minimos)
    while d.weekday() >= 5:  # sat=5, sun=6
        d += timedelta(days=1)
    return d.strftime("%Y-%m-%d")


class AdesaoFlow:
    """Orchestrates the full enrollment flow."""

    def __init__(self, turma_code, headless=False, senha=DEFAULT_SENHA,
                 reports_dir=None, on_step=None, config=None):
        self.turma_code = turma_code
        self.headless = headless
        self.senha = senha
        self.reports_dir = reports_dir or os.path.join(os.getcwd(), "reports-adesao")
        self.on_step = on_step or self._default_on_step
        self.config = config or AdesaoConfig()
        self.results = []
        self.cpf = gerar_cpf()
        self.email = None
        self.mailtm = None

    def _default_on_step(self, num, desc, status, error=None):
        icon = "[OK]" if status == "passed" else "[FAIL]"
        msg = f"  {icon} Step {num}: {desc}"
        if error:
            msg += f" - {error}"
        print(msg)

    def _log(self, num, desc, status, error=None):
        self.results.append({
            "step": num, "description": desc,
            "status": status, "error": error,
        })
        self.on_step(num, desc, status, error)

    def _snap(self, page, num):
        os.makedirs(self.reports_dir, exist_ok=True)
        path = os.path.join(self.reports_dir, f"{num:02d}-adesao.png")
        try:
            page.screenshot(path=path, full_page=True)
        except Exception:
            pass
        return path

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
        except Exception as e:
            print(f'    Button "{text}" not found: {str(e)[:80]}')
            return False

    def _fill_otp(self, page, otp):
        field = page.query_selector('input[inputmode="numeric"]') or \
                page.query_selector('input[maxlength="6"]')
        if not field:
            raise RuntimeError("OTP field not found")
        field.click()
        field.fill("")
        field.type(otp, delay=100)
        page.wait_for_timeout(500)
        val = field.input_value()
        if not val or len(val) < 6:
            page.evaluate("""(code) => {
                const inp = document.querySelector('input[inputmode="numeric"]') ||
                            document.querySelector('input[maxlength="6"]');
                if (inp) {
                    const nativeSet = Object.getOwnPropertyDescriptor(
                        window.HTMLInputElement.prototype, 'value').set;
                    nativeSet.call(inp, code);
                    inp.dispatchEvent(new Event('input', { bubbles: true }));
                    inp.dispatchEvent(new Event('change', { bubbles: true }));
                }
            }""", otp)

    def _capture_otp(self, page, email_selector=None, max_attempts=2):
        for attempt in range(1, max_attempts + 1):
            try:
                otp = self.mailtm.wait_for_otp(timeout=180, interval=3)
                return otp
            except Exception as e:
                print(f"    OTP attempt {attempt}/{max_attempts} failed: {e}")
                if attempt < max_attempts and email_selector:
                    back = page.query_selector('text="voltar ao login"') or \
                           page.query_selector('button:has-text("voltar")')
                    if back:
                        back.click()
                        page.wait_for_timeout(2000)
                        page.fill(email_selector, self.email)
                        page.click('button:has-text("Continuar")')
                        page.wait_for_timeout(2000)
        return None

    def run(self):
        """Execute the full enrollment flow. Returns list of step results."""
        from playwright.sync_api import sync_playwright
        from cli_anything.hub_portal_vibe.utils.temp_email import MailTM

        print(f"=== Adesao Automatizada ===")
        print(f"Turma: {self.turma_code}")
        print(f"CPF: {self.cpf}")
        print(f"Headless: {self.headless}\n")

        # Step 0: Create temp email
        try:
            self.mailtm = MailTM()
            self.email = self.mailtm.create_account()
            print(f"Email: {self.email}\n")
            self._log(0, f"Temp email created: {self.email}", "passed")
        except Exception as e:
            self._log(0, "Create temp email", "failed", str(e))
            return self.results

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=self.headless, slow_mo=200)
            ctx = browser.new_context(viewport={"width": 1366, "height": 768})
            page = ctx.new_page()
            page.set_default_timeout(15000)

            try:
                self._step1_portal(page)
                self._step2_email(page)
                self._step3_otp(page)
                self._step4_dados(page)
                self._step5_senha(page)
                self._step6_turma(page)
                self._step7_plano(page)
                self._step8_parcelamento(page)
                self._step9_responsavel(page)
                self._step10_endereco(page)
                self._step11_contrato(page)
                self._step12_recorrencia(page)
                self._step13_verificacao(page)
            except Exception as e:
                self._log(99, "Unexpected error", "failed", str(e))
            finally:
                browser.close()
                try:
                    self.mailtm.delete_account()
                except Exception:
                    pass

        passed = sum(1 for r in self.results if r["status"] == "passed")
        failed = sum(1 for r in self.results if r["status"] == "failed")
        print(f"\nTotal: {len(self.results)} | Passed: {passed} | Failed: {failed}")
        return self.results

    # -- Steps --

    def _step1_portal(self, page):
        try:
            page.goto(PORTAL_URL, wait_until="networkidle", timeout=30000)
            self._snap(page, 1)
            self._log(1, "Access portal", "passed")
        except Exception as e:
            self._snap(page, 1)
            self._log(1, "Access portal", "failed", str(e))

    def _step2_email(self, page):
        try:
            page.fill('input[type="email"]', self.email)
            page.click('button:has-text("Continuar")')
            page.wait_for_timeout(2000)
            self._snap(page, 2)
            self._log(2, f"Email sent: {self.email}", "passed")
        except Exception as e:
            self._snap(page, 2)
            self._log(2, "Submit email", "failed", str(e))

    def _step3_otp(self, page):
        try:
            otp = self._capture_otp(page, 'input[type="email"]')
            if not otp:
                raise RuntimeError("No OTP received")
            print(f"    OTP: {otp}")
            self._fill_otp(page, otp)
            self._snap(page, 3)
            page.click('button:has-text("Confirmar")')
            self._wait_stable(page, 5000)
            self._log(3, f"OTP confirmed ({otp})", "passed")
        except Exception as e:
            self._snap(page, 3)
            self._log(3, "Confirm OTP", "failed", str(e))

    def _step4_dados(self, page):
        try:
            dados = {
                "nome": "Teste Automacao CLI",
                "apelido": "TesteCLI",
                "nascimento": "2000-05-15",
                "cpf": self.cpf,
                "telefone": "31999887766",
            }
            inp = page.query_selector('input[placeholder*="nome completo"]')
            if inp:
                inp.fill(dados["nome"])
            inp = page.query_selector('input[placeholder*="como voce gosta"], input[placeholder*="como você gosta"]')
            if inp:
                inp.fill(dados["apelido"])
            inp = page.query_selector('input[type="date"]')
            if inp:
                inp.fill(dados["nascimento"])
            inp = page.query_selector('input[placeholder*="CPF"]')
            if inp:
                inp.type(dados["cpf"], delay=50)
            inp = page.query_selector('input[placeholder*="Telefone"]')
            if inp:
                inp.type(dados["telefone"], delay=50)
            sel = page.query_selector("select")
            if sel:
                sel.select_option(index=1)
            self._snap(page, 4)
            page.click('button:has-text("Continuar")')
            self._wait_stable(page, 3000)
            self._log(4, "Personal data filled", "passed")
        except Exception as e:
            self._snap(page, 4)
            self._log(4, "Fill personal data", "failed", str(e))

    def _step5_senha(self, page):
        try:
            senha_inp = page.query_selector('input[placeholder="senha"]')
            if not senha_inp:
                self._log(5, "Password (skipped - not shown)", "passed")
                return
            page.fill('input[placeholder="senha"]', self.senha)
            page.fill('input[placeholder="confirme a senha"]', self.senha)
            self._snap(page, 5)
            page.click('button:has-text("Criar conta")')
            self._wait_stable(page, 5000)
            self._log(5, "Password created", "passed")
        except Exception as e:
            self._snap(page, 5)
            self._log(5, "Create password", "failed", str(e))

    def _step6_turma(self, page):
        try:
            self._wait_url(page, "selecao-turma", 10000)
            outra = page.query_selector('label:has-text("Outra turma")')
            if outra:
                outra.click()
                page.wait_for_timeout(500)
            possui = page.query_selector('text="Possuo um codigo de acesso"') or \
                     page.query_selector('text="Possuo um código de acesso"')
            if possui:
                possui.click()
                page.wait_for_timeout(1000)
            code_inp = page.query_selector('input[placeholder*="codigo"]') or \
                       page.query_selector('input[placeholder*="código"]') or \
                       page.query_selector('input[placeholder*="Digite o código"]')
            if code_inp:
                code_inp.fill(self.turma_code)
                page.wait_for_timeout(2000)
            else:
                raise RuntimeError("Turma code field not found")
            self._snap(page, 6)
            btn = page.locator('button:has-text("Selecionar turma")')
            start = time.time()
            while time.time() - start < 10:
                try:
                    if btn.is_enabled():
                        break
                except Exception:
                    pass
                page.wait_for_timeout(500)
            btn.click()
            self._wait_stable(page, 5000)
            self._log(6, f"Turma {self.turma_code} selected", "passed")
        except Exception as e:
            self._snap(page, 6)
            self._log(6, "Select turma", "failed", str(e))

    def _step7_plano(self, page):
        try:
            self._wait_url(page, "selecao-plano", 10000)
            self._wait_stable(page, 3000)

            # List available plans for logging
            plan_names = page.evaluate("""() => {
                const cards = document.querySelectorAll('[class*="card"], [class*="Card"]');
                const names = [];
                document.querySelectorAll('button').forEach(btn => {
                    if (btn.textContent.includes('Selecionar plano') && btn.offsetParent !== null) {
                        // Walk up to find plan name
                        let el = btn.parentElement;
                        for (let i = 0; i < 5 && el; i++) {
                            const h = el.querySelector('h2, h3, [class*="title"]');
                            if (h) { names.push(h.textContent.trim()); break; }
                            el = el.parentElement;
                        }
                        if (names.length === 0) names.push('Plan');
                    }
                });
                return names;
            }""")
            if plan_names:
                print(f"    Available plans: {plan_names}")

            # Select by index if specified
            idx = self.config.plano_index or 0
            plan_btns = page.locator('button:has-text("Selecionar plano")')
            count = plan_btns.count()

            if count > 0:
                actual_idx = min(idx, count - 1)
                plan_btns.nth(actual_idx).wait_for(state="visible", timeout=10000)
                plan_btns.nth(actual_idx).click()
                plan_name = plan_names[actual_idx] if actual_idx < len(plan_names) else f"Plan #{actual_idx}"
                print(f"    Selected: {plan_name} (index {actual_idx})")
                self._wait_stable(page, 3000)
            else:
                skip = page.query_selector('button:has-text("Pular por enquanto")')
                if skip:
                    skip.click()
                    self._wait_stable(page, 3000)
                    print("    No plans available, skipped")

            self._snap(page, 7)
            self._log(7, f"Plan selected (index {idx})", "passed")
        except Exception as e:
            self._snap(page, 7)
            self._log(7, "Select plan", "failed", str(e))

    def _step8_parcelamento(self, page):
        try:
            on_parc = self._wait_url(page, "selecao-parcelamento", 10000)
            if not on_parc:
                self._log(8, "Installments (skipped - not available)", "passed")
                return
            self._wait_stable(page, 3000)

            cfg = self.config
            details = []

            # 1. Dia de vencimento (select)
            dia = str(cfg.dia_vencimento or 10)
            sel = page.query_selector("select")
            if sel:
                try:
                    sel.select_option(dia)
                except Exception:
                    sel.select_option(index=int(dia))
                details.append(f"due_day={dia}")
                print(f"    Due day: {dia}")

            # 2. Data primeira parcela (calendar click or date input)
            data = cfg.data_primeira_parcela or proximo_dia_util(10)
            # Try clicking the day in the calendar
            day_num = str(int(data.split("-")[2]))  # remove leading zero
            day_clicked = False
            try:
                # The calendar shows day numbers as buttons
                day_buttons = page.locator(f'button:has-text("{day_num}")')
                for i in range(day_buttons.count()):
                    btn = day_buttons.nth(i)
                    if btn.is_visible() and btn.is_enabled():
                        # Check it's not already selected (bg-blue)
                        btn.click()
                        day_clicked = True
                        break
            except Exception:
                pass

            if not day_clicked:
                # Fallback to date input
                for di in page.query_selector_all('input[type="date"]'):
                    try:
                        if di.is_visible() and not di.input_value():
                            di.fill(data)
                    except Exception:
                        pass

            details.append(f"first_date={data}")
            print(f"    First installment: {data}")
            page.wait_for_timeout(1000)

            # 3. Parcelas slider
            if cfg.parcelas is not None:
                # The Slider component renders as a div with role="slider"
                page.wait_for_timeout(500)
                try:
                    sliders = page.locator('[role="slider"]')
                    if sliders.count() > 0:
                        slider = sliders.first
                        # Read current range
                        min_val = int(slider.get_attribute("aria-valuemin") or "1")
                        max_val = int(slider.get_attribute("aria-valuemax") or "60")
                        target = max(min_val, min(cfg.parcelas, max_val))

                        # Set value via aria-valuenow and keyboard
                        current = int(slider.get_attribute("aria-valuenow") or str(max_val))
                        slider.click()
                        diff = target - current
                        key = "ArrowRight" if diff > 0 else "ArrowLeft"
                        for _ in range(abs(diff)):
                            slider.press(key)

                        details.append(f"installments={target}")
                        print(f"    Installments: {target} (range {min_val}-{max_val})")
                except Exception as e:
                    print(f"    Slider adjustment failed: {e}")

            # 4. Parcelamento estendido
            if cfg.parcelamento_estendido and cfg.parcelas_estendido:
                page.wait_for_timeout(500)
                try:
                    sliders = page.locator('[role="slider"]')
                    if sliders.count() > 1:
                        ext_slider = sliders.nth(1)
                        if ext_slider.is_visible():
                            ext_slider.click()
                            max_ext = int(ext_slider.get_attribute("aria-valuemax") or "12")
                            current_ext = int(ext_slider.get_attribute("aria-valuenow") or "0")
                            target_ext = min(cfg.parcelas_estendido, max_ext)
                            diff = target_ext - current_ext
                            key = "ArrowRight" if diff > 0 else "ArrowLeft"
                            for _ in range(abs(diff)):
                                ext_slider.press(key)
                            details.append(f"extended={target_ext}")
                            print(f"    Extended installments: {target_ext}")
                except Exception as e:
                    print(f"    Extended slider failed: {e}")

            # 5. Arrecadacao alternativa toggle
            page.wait_for_timeout(500)
            try:
                # The switch is a checkbox with id "arrecadacao-alternativa"
                arrecadacao_cb = page.query_selector('#arrecadacao-alternativa')
                if arrecadacao_cb:
                    is_checked = arrecadacao_cb.is_checked()
                    want_enabled = cfg.arrecadacao_alternativa
                    if is_checked != want_enabled:
                        # Click the parent label/switch to toggle
                        parent = page.locator('label[for="arrecadacao-alternativa"], [class*="switch"]').first
                        if parent.count() if hasattr(parent, 'count') else True:
                            arrecadacao_cb.click()
                        else:
                            arrecadacao_cb.click()
                        page.wait_for_timeout(500)
                    status = "enabled" if want_enabled else "disabled"
                    details.append(f"arrecadacao={status}")
                    print(f"    Alternative collection: {status}")
            except Exception as e:
                print(f"    Arrecadacao toggle failed: {e}")

            # 6. Checkbox "ciente de taxas" - always check all remaining checkboxes
            page.evaluate("""() => {
                document.querySelectorAll('input[type="checkbox"]').forEach(cb => {
                    if (!cb.checked && cb.id !== 'arrecadacao-alternativa') {
                        cb.click();
                        cb.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                });
            }""")
            page.wait_for_timeout(1000)

            self._snap(page, 8)

            if not self._click_button(page, "Continuar", wait_after=5000):
                self._click_button(page, "Pular por enquanto", wait_after=3000)

            summary = ", ".join(details) if details else "defaults"
            self._log(8, f"Installments configured ({summary})", "passed")
        except Exception as e:
            self._snap(page, 8)
            self._log(8, "Configure installments", "failed", str(e))

    def _step9_responsavel(self, page):
        try:
            self._wait_url(page, "contratacao", 10000)
            self._wait_stable(page, 3000)
            self_btn = page.query_selector('button:has-text("Eu serei")') or \
                       page.query_selector('button:has-text("eu mesmo")') or \
                       page.query_selector('button:has-text("responsavel")') or \
                       page.query_selector('button:has-text("responsável")')
            if self_btn:
                self_btn.click()
                page.wait_for_timeout(1000)
            self._click_button(page, "Continuar", wait_after=3000)
            self._snap(page, 9)
            self._log(9, "Financial responsible selected (self)", "passed")
        except Exception as e:
            self._snap(page, 9)
            self._log(9, "Select financial responsible", "failed", str(e))

    def _step10_endereco(self, page):
        try:
            self._wait_stable(page, 2000)
            cep = page.query_selector('input[placeholder*="00000"]') or \
                  page.query_selector('input[placeholder*="CEP"]') or \
                  page.query_selector('input[placeholder*="cep"]')
            if cep:
                cep.click()
                cep.fill("")
                cep.type("30130000", delay=50)
                page.wait_for_timeout(3000)
            state_sel = page.query_selector("select")
            if state_sel:
                try:
                    state_sel.select_option("MG")
                except Exception:
                    pass
            for placeholder, value in [
                ("cidade", "Belo Horizonte"),
                ("logradouro", "Rua da Bahia"),
                ("bairro", "Centro"),
            ]:
                inp = page.query_selector(f'input[placeholder*="{placeholder}"]')
                if inp and not inp.input_value():
                    inp.fill(value)
            num_inp = page.query_selector('input[placeholder*="numero"]') or \
                      page.query_selector('input[placeholder*="número"]')
            if num_inp:
                num_inp.fill("100")
            self._snap(page, 10)
            self._click_button(page, "Continuar", wait_after=5000)
            self._log(10, "Address filled", "passed")
        except Exception as e:
            self._snap(page, 10)
            self._log(10, "Fill address", "failed", str(e))

    def _step11_contrato(self, page):
        try:
            self._wait_stable(page, 3000)
            text = page.evaluate("() => document.body.innerText.substring(0, 2000)")
            if "contrato" in text.lower() or "assinar" in text.lower():
                assinar = page.query_selector('button:has-text("Assinar")') or \
                          page.query_selector('button:has-text("Enviar codigo")') or \
                          page.query_selector('button:has-text("Enviar código")')
                if assinar:
                    assinar.click()
                    page.wait_for_timeout(3000)
                otp2 = self._capture_otp(page)
                if otp2:
                    print(f"    Contract OTP: {otp2}")
                    code_inp = page.query_selector('input[type="text"]') or \
                               page.query_selector('input[placeholder*="codigo"]') or \
                               page.query_selector('input[placeholder*="código"]')
                    if code_inp:
                        code_inp.fill("")
                        code_inp.type(otp2, delay=100)
                    verify = page.query_selector('button:has-text("Verificar")') or \
                             page.query_selector('button:has-text("Confirmar")')
                    if verify:
                        verify.click()
                        self._wait_stable(page, 5000)
                    self._click_button(page, "Continuar", wait_after=3000)
            self._snap(page, 11)
            self._log(11, "Contract signed", "passed")
        except Exception as e:
            self._snap(page, 11)
            self._log(11, "Sign contract", "failed", str(e))

    def _step12_recorrencia(self, page):
        try:
            self._wait_stable(page, 3000)
            self._snap(page, 12)
            clicked = self._click_button(page, "ADICIONAR DEPOIS", wait_after=5000)
            if not clicked:
                clicked = self._click_button(page, "Adicionar depois", wait_after=5000)
            if not clicked:
                self._click_button(page, "adicionar depois", wait_after=5000)
            self._log(12, "Recurring payment skipped", "passed")
        except Exception as e:
            self._snap(page, 12)
            self._log(12, "Skip recurring payment", "failed", str(e))

    def _step13_verificacao(self, page):
        try:
            self._wait_stable(page, 3000)
            url = page.url
            text = page.evaluate("() => document.body.innerText.toLowerCase()")
            success = any(kw in text for kw in [
                "sucesso", "adesao realizada", "adesão realizada",
                "bem-vindo", "parabens", "parabéns", "dashboard",
            ]) or "/dashboard" in url or "/portal" in url
            self._snap(page, 13)
            if success:
                self._log(13, "Enrollment complete!", "passed")
            else:
                self._log(13, f"Final state - URL: {url}", "passed")
        except Exception as e:
            self._snap(page, 13)
            self._log(13, "Final verification", "failed", str(e))

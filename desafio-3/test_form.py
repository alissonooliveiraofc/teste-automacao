import json
import os
import time
import unittest
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


SITE_URL = "https://demoqa.com/automation-practice-form"
HEADLESS = os.environ.get("HEADLESS", "false").lower() == "true"

BASE_DIR = Path(__file__).parent
DATA_FILE = BASE_DIR / "data.json"
UPLOAD_FILE = BASE_DIR / "upload.png"
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", BASE_DIR))
SCREENSHOT_FILE = OUTPUT_DIR / "confirmation.png"


def load_data() -> dict:
    with open(DATA_FILE, encoding="utf-8") as f:
        return json.load(f)


def create_upload_image():
    """Cria uma imagem PNG mínima válida se não existir."""
    if UPLOAD_FILE.exists():
        return
    # PNG 1x1 pixel vermelho (bytes mínimos válidos)
    png_bytes = bytes([
        0x89,0x50,0x4E,0x47,0x0D,0x0A,0x1A,0x0A,0x00,0x00,0x00,0x0D,0x49,0x48,0x44,0x52,
        0x00,0x00,0x00,0x01,0x00,0x00,0x00,0x01,0x08,0x02,0x00,0x00,0x00,0x90,0x77,0x53,
        0xDE,0x00,0x00,0x00,0x0C,0x49,0x44,0x41,0x54,0x08,0xD7,0x63,0xF8,0xCF,0xC0,0x00,
        0x00,0x00,0x02,0x00,0x01,0xE2,0x21,0xBC,0x33,0x00,0x00,0x00,0x00,0x49,0x45,0x4E,
        0x44,0xAE,0x42,0x60,0x82,
    ])
    UPLOAD_FILE.write_bytes(png_bytes)


class TestPracticeForm(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        create_upload_image()
        cls.data = load_data()

        options = Options()
        if HEADLESS:
            options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-blink-features=AutomationControlled")

        service = Service(ChromeDriverManager().install())
        cls.driver = webdriver.Chrome(service=service, options=options)
        cls.driver.implicitly_wait(10)
        cls.wait = WebDriverWait(cls.driver, 15)

    @classmethod
    def tearDownClass(cls):
        time.sleep(2)
        if cls.driver:
            cls.driver.quit()

    def setUp(self):
        try:
            self.driver.get(SITE_URL)
        except Exception:
            # Sessão inativa (evita quebra entre testes)
            self.__class__.setUpClass()
            self.driver.get(SITE_URL)
        self._dismiss_ads()

    def _dismiss_ads(self):
        """Remove banners de anúncio que bloqueiam cliques no demoqa."""
        self.driver.execute_script("""
            ['#fixedban', 'footer', '.google-auto-placed'].forEach(sel => {
                document.querySelectorAll(sel).forEach(el => el.remove());
            });
        """)

    def _type_field(self, element, value: str):
        """Digita caractere a caractere para garantir compatibilidade com React."""
        element.click()
        element.clear()
        for char in value:
            element.send_keys(char)
            time.sleep(0.03)

    def _scroll_to(self, element):
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        time.sleep(0.3)

    # ------------------------------------------------------------------
    # TESTE 1 — Formulário completo
    # ------------------------------------------------------------------
    def test_01_submit_full_form(self):
        print("\n📋 Teste 1: Preenchendo formulário completo...")
        d = self.data

        # Nome e sobrenome
        self._type_field(self.driver.find_element(By.ID, "firstName"), d["first_name"])
        self._type_field(self.driver.find_element(By.ID, "lastName"), d["last_name"])

        # Email
        self._type_field(self.driver.find_element(By.ID, "userEmail"), d["email"])

        # Gênero
        gender_label = self.driver.find_element(
            By.XPATH, f"//label[normalize-space()='{d['gender']}']"
        )
        self._scroll_to(gender_label)
        self.driver.execute_script("arguments[0].click();", gender_label)

        # Telefone
        self._type_field(self.driver.find_element(By.ID, "userNumber"), d["mobile"])

        # Data de nascimento
        self._fill_date_of_birth(d["date_of_birth"])

        # Subjects (autocomplete)
        self._fill_subjects(d["subjects"])

        # Hobbies
        self._select_hobbies(d["hobbies"])

        # Upload de imagem
        upload_input = self.driver.find_element(By.ID, "uploadPicture")
        upload_input.send_keys(str(UPLOAD_FILE.resolve()))

        # Endereço
        self._type_field(
            self.driver.find_element(By.ID, "currentAddress"),
            d["current_address"]
        )

        # Estado e cidade (Dropdowns dinâmicos)
        self._select_react_dropdown("State", d["state"])
        self._select_react_dropdown("City", d["city"])

        # Submit
        submit_btn = self.driver.find_element(By.ID, "submit")
        self._scroll_to(submit_btn)
        self.driver.execute_script("arguments[0].click();", submit_btn)

        # Verificar modal
        self._verify_modal(d)

        # Screenshot
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        self.driver.save_screenshot(str(SCREENSHOT_FILE))
        print(f"   📸 Screenshot salvo em: {SCREENSHOT_FILE}")

    # ------------------------------------------------------------------
    # TESTE 2 (Bônus) — Submissão com formulário vazio
    # ------------------------------------------------------------------
    def test_02_submit_empty_form(self):
        print("\n⚠️  Teste 2 (Bônus): Submetendo formulário vazio...")

        submit_btn = self.driver.find_element(By.ID, "submit")
        self._scroll_to(submit_btn)
        self.driver.execute_script("arguments[0].click();", submit_btn)

        time.sleep(0.5)

        # Verificação do comportamento HTML5 "required"
        modal_present = len(self.driver.find_elements(By.ID, "example-modal-sizes-title-lg")) > 0
        self.assertFalse(modal_present, "Modal não deveria aparecer com formulário vazio")
        print("   ✅ Validação de formulário vazio confirmada! (Campos obrigatórios validados)")

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------
    def _fill_date_of_birth(self, dob: dict):
        date_input = self.driver.find_element(By.ID, "dateOfBirthInput")
        self._scroll_to(date_input)
        date_input.click()

        # Selecionar mês
        month_select = self.wait.until(
            EC.presence_of_element_located((By.CLASS_NAME, "react-datepicker__month-select"))
        )
        for option in month_select.find_elements(By.TAG_NAME, "option"):
            if option.text == dob["month"]:
                option.click()
                break

        # Selecionar ano
        year_select = self.driver.find_element(By.CLASS_NAME, "react-datepicker__year-select")
        for option in year_select.find_elements(By.TAG_NAME, "option"):
            if option.text == dob["year"]:
                option.click()
                break

        # Selecionar dia
        day_xpath = f"//div[contains(@class,'react-datepicker__day') and not(contains(@class,'outside-month')) and text()='{dob['day']}']"
        day_element = self.wait.until(EC.element_to_be_clickable((By.XPATH, day_xpath)))
        day_element.click()

    def _fill_subjects(self, subjects: list):
        subjects_input = self.driver.find_element(By.ID, "subjectsInput")
        self._scroll_to(subjects_input)

        for subject in subjects:
            subjects_input.click()
            self._type_field(subjects_input, subject[:3])
            time.sleep(0.5)
            suggestion = self.wait.until(
                EC.presence_of_element_located((By.XPATH, f"//div[contains(@class,'option') and contains(text(),'{subject}')]"))
            )
            suggestion.click()

    def _select_hobbies(self, hobbies: list):
        hobby_map = {"Sports": "hobbies-checkbox-1", "Reading": "hobbies-checkbox-2", "Music": "hobbies-checkbox-3"}
        for hobby in hobbies:
            if hobby in hobby_map:
                label = self.driver.find_element(
                    By.XPATH, f"//label[@for='{hobby_map[hobby]}']"
                )
                self._scroll_to(label)
                self.driver.execute_script("arguments[0].click();", label)

    def _select_react_dropdown(self, placeholder: str, value: str):
        """
        Método de Alta Confiabilidade para o React-Select.
        Mapeia o container correspondente, escreve o valor e simula o pressionamento do ENTER.
        obs: esse foi uma luta!
        """
        # Mapeia "State" para id "state" e "City" para id "city"
        element_id = "state" if placeholder == "State" else "city"
        
        dropdown = self.wait.until(EC.element_to_be_clickable((By.ID, element_id)))
        self._scroll_to(dropdown)
        
        # Abre o menu clicando no elemento pai
        self.driver.execute_script("arguments[0].click();", dropdown)
        time.sleep(0.5)
        
        # Localiza o input de texto real que o React-Select mantém oculto/focado para escrita
        input_el = dropdown.find_element(By.CSS_SELECTOR, "input")
        
        # Digita o valor e envia a tecla ENTER para selecionar automaticamente a correspondência
        input_el.send_keys(value)
        time.sleep(0.5)
        input_el.send_keys(Keys.ENTER)
        time.sleep(0.5)

    def _verify_modal(self, d: dict):
        modal_title = self.wait.until(
            EC.visibility_of_element_located((By.ID, "example-modal-sizes-title-lg"))
        )
        self.assertEqual(modal_title.text, "Thanks for submitting the form")
        print("   ✅ Modal de confirmação exibido!")

        # Extrair dados da tabela do modal
        rows = self.driver.find_elements(By.CSS_SELECTOR, ".table-responsive tbody tr")
        modal_data = {
            row.find_elements(By.TAG_NAME, "td")[0].text:
            row.find_elements(By.TAG_NAME, "td")[1].text
            for row in rows if len(row.find_elements(By.TAG_NAME, "td")) == 2
        }

        full_name = f"{d['first_name']} {d['last_name']}"
        self.assertIn(full_name, modal_data.get("Student Name", ""))
        self.assertIn(d["email"], modal_data.get("Student Email", ""))
        self.assertIn(d["gender"], modal_data.get("Gender", ""))
        self.assertIn(d["mobile"], modal_data.get("Mobile", ""))
        self.assertIn(d["state"], modal_data.get("State and City", ""))
        self.assertIn(d["city"], modal_data.get("State and City", ""))

        print("   ✅ Dados do modal verificados:")
        for label, value in modal_data.items():
            print(f"      {label}: {value}")


# ------------------------------------------------------------------
# EXECUÇÃO
# ------------------------------------------------------------------
def main():
    print("=" * 60)
    print("🤖 AUTOMAÇÃO — DemoQA Practice Form (Desafio 3)")
    print("=" * 60)

    loader = unittest.TestLoader()
    loader.sortTestMethodsUsing = lambda x, y: (x > y) - (x < y)
    suite = loader.loadTestsFromTestCase(TestPracticeForm)

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 60)
    print("📊 RESUMO DOS TESTES")
    print("=" * 60)
    passed = result.testsRun - len(result.failures) - len(result.errors)
    print(f"  ✅ Passaram:   {passed}")
    print(f"  ❌ Falharam:   {len(result.failures)}")
    print(f"  ⚠  Erros:     {len(result.errors)}")
    print("=" * 60)

    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    exit(main())
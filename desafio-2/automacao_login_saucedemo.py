import os
import time
import unittest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from webdriver_manager.chrome import ChromeDriverManager


SITE_URL = "https://www.saucedemo.com"
USERNAME = "standard_user"
PASSWORD = "secret_sauce"

HEADLESS = os.environ.get("HEADLESS", "false").lower() == "true"

# Script JS que usa o setter nativo do React para forçar atualização do onChange
REACT_SET_VALUE = """
    var setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
    setter.call(arguments[0], arguments[1]);
    arguments[0].dispatchEvent(new Event('input', { bubbles: true }));
    arguments[0].dispatchEvent(new Event('change', { bubbles: true }));
"""


class TestSauceDemoFlow(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        options = Options()

        if HEADLESS:
            options.add_argument("--headless=new")
            options.add_argument("--disable-gpu")

        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("prefs", {
            "credentials_enable_service": False,
            "profile.password_manager_enabled": False,
        })

        service = Service(ChromeDriverManager().install())
        cls.driver = webdriver.Chrome(service=service, options=options)
        cls.driver.implicitly_wait(10)
        cls.wait = WebDriverWait(cls.driver, 15)

    @classmethod
    def tearDownClass(cls):
        time.sleep(2)
        if cls.driver:
            cls.driver.quit()

    def test_01_login(self):
        print("\n🔐 Etapa 1: Realizando login...")

        self.driver.get(SITE_URL)

        username_input = self.wait.until(EC.presence_of_element_located((By.ID, "user-name")))
        username_input.clear()
        username_input.send_keys(USERNAME)

        password_input = self.driver.find_element(By.ID, "password")
        password_input.clear()
        password_input.send_keys(PASSWORD)

        self.driver.find_element(By.ID, "login-button").click()

        self.wait.until(EC.url_contains("/inventory.html"))
        self.assertIn("/inventory.html", self.driver.current_url)
        print("   ✅ Login realizado com sucesso!")

    def test_02_apply_filter(self):
        print("\n🔧 Etapa 2: Aplicando filtro Price (low to high)...")

        sort_dropdown = self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-test='product-sort-container']"))
        )
        Select(sort_dropdown).select_by_value("lohi")
        time.sleep(1)

        prices = self.driver.find_elements(By.CSS_SELECTOR, "[data-test='inventory-item-price']")
        price_values = [float(p.text.replace("$", "")) for p in prices]

        self.assertEqual(price_values, sorted(price_values))
        print(f"   ✅ Filtro aplicado! Preços: {price_values}")

    def test_03_add_to_cart(self):
        print("\n🛒 Etapa 3: Adicionando 3 produtos ao carrinho...")

        items = self.driver.find_elements(By.CSS_SELECTOR, "[data-test='inventory-item']")
        self.assertGreaterEqual(len(items), 3)

        products_added = []

        for i in range(3):
            item = items[i]
            name = item.find_element(By.CSS_SELECTOR, "[data-test='inventory-item-name']").text
            btn = item.find_element(By.CSS_SELECTOR, "button[data-test^='add-to-cart']")

            self.driver.execute_script("arguments[0].scrollIntoView(true);", btn)
            time.sleep(0.3)
            self.driver.execute_script("arguments[0].click();", btn)
            products_added.append(name)

            badge = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-test='shopping-cart-badge']"))
            )
            self.assertEqual(int(badge.text), i + 1)
            print(f"   📦 [{i+1}/3] {name} — Badge: {badge.text}")

        print(f"   ✅ {len(products_added)} produtos adicionados!")

    def test_04_checkout(self):
        print("\n💳 Etapa 4: Realizando checkout...")

        cart_link = self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-test='shopping-cart-link']"))
        )
        self.driver.execute_script("arguments[0].click();", cart_link)
        self.wait.until(EC.url_contains("/cart.html"))

        cart_items = self.driver.find_elements(By.CSS_SELECTOR, "[data-test='inventory-item']")
        self.assertEqual(len(cart_items), 3)
        print(f"   ✅ {len(cart_items)} itens no carrinho confirmados")

        checkout_button = self.wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-test='checkout']"))
        )
        self.driver.execute_script("arguments[0].click();", checkout_button)
        self.wait.until(EC.url_contains("/checkout-step-one.html"))

        print("   📝 Preenchendo dados pessoais...")
        time.sleep(1.5)

        for field_id, value in [
            ("first-name", "Alisson"),
            ("last-name", "Oliveira"),
            ("postal-code", "01001000"),
        ]:
            field = self.wait.until(EC.visibility_of_element_located((By.ID, field_id)))

            # Setter nativo do React — única forma confiável de atualizar o estado interno
            self.driver.execute_script(REACT_SET_VALUE, field, value)
            time.sleep(0.5)

            actual = field.get_attribute("value")
            self.assertEqual(actual, value, f"Campo '{field_id}' ficou '{actual}' em vez de '{value}'")
            print(f"   ✏️  {field_id}: {actual}")

        time.sleep(0.5)
        continue_btn = self.wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-test='continue']"))
        )
        self.driver.execute_script("arguments[0].scrollIntoView(true);", continue_btn)
        time.sleep(0.3)
        self.driver.execute_script("arguments[0].click();", continue_btn)

        try:
            self.wait.until(EC.url_contains("/checkout-step-two.html"))
        except Exception as e:
            errors = self.driver.find_elements(By.CSS_SELECTOR, "[data-test='error']")
            if errors:
                print(f"   ❌ Erro no formulário: {errors[0].text}")
            raise e

        total_label = self.driver.find_element(By.CSS_SELECTOR, "[data-test='total-label']")
        print(f"   📋 {total_label.text}")

        finish_button = self.wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "[data-test='finish']"))
        )
        self.driver.execute_script("arguments[0].scrollIntoView(true);", finish_button)
        time.sleep(0.3)
        self.driver.execute_script("arguments[0].click();", finish_button)

        self.wait.until(EC.url_contains("/checkout-complete.html"))
        complete_header = self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-test='complete-header']"))
        )
        self.assertEqual(complete_header.text, "Thank you for your order!")
        print("   ✅ Pedido finalizado com sucesso!")

    def test_05_logout(self):
        print("\n🚪 Etapa 5: Realizando logout...")

        menu_button = self.wait.until(
            EC.presence_of_element_located((By.ID, "react-burger-menu-btn"))
        )
        self.driver.execute_script("arguments[0].click();", menu_button)
        time.sleep(1)

        logout_link = self.wait.until(
            EC.presence_of_element_located((By.ID, "logout_sidebar_link"))
        )
        self.driver.execute_script("arguments[0].click();", logout_link)

        login_button = self.wait.until(
            EC.presence_of_element_located((By.ID, "login-button"))
        )
        self.assertTrue(login_button.is_displayed())
        print("   ✅ Logout confirmado — de volta à tela de login!")


def main():
    print("=" * 60)
    print("🤖 AUTOMAÇÃO — SauceDemo E-commerce")
    print("=" * 60)

    loader = unittest.TestLoader()
    loader.sortTestMethodsUsing = lambda x, y: (x > y) - (x < y)
    suite = loader.loadTestsFromTestCase(TestSauceDemoFlow)

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
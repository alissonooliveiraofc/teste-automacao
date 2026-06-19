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
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager


SITE_URL = "https://www.saucedemo.com"
USERNAME = "standard_user"
PASSWORD = "secret_sauce"

# False por padrão (abre o navegador). No Docker, a variável HEADLESS=true é setada automaticamente.
HEADLESS = os.environ.get("HEADLESS", "false").lower() == "true"


class TestSauceDemoFlow(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        chrome_options = Options()

        if HEADLESS:
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--disable-gpu")

        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")

        service = Service(ChromeDriverManager().install())
        cls.driver = webdriver.Chrome(service=service, options=chrome_options)
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

        username_input = self.wait.until(
            EC.presence_of_element_located((By.ID, "user-name"))
        )
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
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "[data-test='product-sort-container']")
            )
        )
        Select(sort_dropdown).select_by_value("lohi")
        time.sleep(1)

        prices = self.driver.find_elements(
            By.CSS_SELECTOR, "[data-test='inventory-item-price']"
        )
        price_values = [float(p.text.replace("$", "")) for p in prices]

        self.assertEqual(price_values, sorted(price_values))
        print(f"   ✅ Filtro aplicado! Preços: {price_values}")

    def test_03_add_to_cart(self):
        print("\n🛒 Etapa 3: Adicionando 3 produtos ao carrinho...")

        products_added = []

        for i in range(3):
            product_names = self.driver.find_elements(
                By.CSS_SELECTOR, "[data-test='inventory-item-name']"
            )
            product_name = product_names[i].text if i < len(product_names) else f"Produto {i+1}"

            add_buttons = self.driver.find_elements(
                By.CSS_SELECTOR, "button[data-test^='add-to-cart']"
            )
            if not add_buttons:
                break

            self.driver.execute_script("arguments[0].scrollIntoView(true);", add_buttons[0])
            time.sleep(0.4)
            self.driver.execute_script("arguments[0].click();", add_buttons[0])
            products_added.append(product_name)

            badge = self.wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "[data-test='shopping-cart-badge']")
                )
            )
            self.assertEqual(int(badge.text), i + 1)
            print(f"   📦 [{i+1}/3] {product_name} — Badge: {badge.text}")

        print(f"   ✅ {len(products_added)} produtos adicionados!")

    def test_04_checkout(self):
        print("\n💳 Etapa 4: Realizando checkout...")

        cart_link = self.wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "[data-test='shopping-cart-link']")
            )
        )
        self.driver.execute_script("arguments[0].click();", cart_link)
        self.wait.until(EC.url_contains("/cart.html"))

        cart_items = self.driver.find_elements(
            By.CSS_SELECTOR, "[data-test='inventory-item']"
        )
        self.assertEqual(len(cart_items), 3)
        print(f"   ✅ {len(cart_items)} itens no carrinho confirmados")

        checkout_button = self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-test='checkout']"))
        )
        self.driver.execute_script("arguments[0].click();", checkout_button)
        self.wait.until(EC.url_contains("/checkout-step-one.html"))

        print("   📝 Preenchendo dados pessoais...")
        time.sleep(1)

        for field_id, value in [("first-name", "Alisson"), ("last-name", "Oliveira"), ("postal-code", "01001-000")]:
            field = self.wait.until(EC.visibility_of_element_located((By.ID, field_id)))
            self.driver.execute_script(
                "arguments[0].value = ''; arguments[0].dispatchEvent(new Event('input', { bubbles: true }));",
                field
            )
            field.click()
            for char in value:
                field.send_keys(char)
                time.sleep(0.05)

        time.sleep(0.3)
        continue_button = self.wait.until(EC.element_to_be_clickable((By.ID, "continue")))
        continue_button.click()

        try:
            self.wait.until(EC.url_contains("/checkout-step-two.html"))
        except Exception as e:
            errors = self.driver.find_elements(By.CSS_SELECTOR, "[data-test='error']")
            if errors:
                print(f"   ❌ Erro no formulário: {errors[0].text}")
            raise e

        print("   📋 Resumo do pedido:")
        total_label = self.driver.find_element(By.CSS_SELECTOR, "[data-test='total-label']")
        print(f"   💰 {total_label.text}")

        finish_button = self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-test='finish']"))
        )
        self.driver.execute_script("arguments[0].scrollIntoView(true);", finish_button)
        time.sleep(0.3)
        self.driver.execute_script("arguments[0].click();", finish_button)

        self.wait.until(EC.url_contains("/checkout-complete.html"))
        complete_header = self.wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "[data-test='complete-header']"))
        )
        self.assertEqual(complete_header.text, "Thank you for your order!")
        print("   ✅ Pedido finalizado!")

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
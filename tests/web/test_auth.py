from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import time
import pytest
import chromedriver_autoinstaller
import psycopg2
from psycopg2.extras import RealDictCursor

DATABASE_URL = "postgresql://filmadmin:mycoolpassword123@localhost:6432/filmdb"

def update_user_role(email: str, role: str):
    try:
        conn = psycopg2.connect(DATABASE_URL)
        conn.set_session(autocommit=True)
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "UPDATE filmuser SET role = %s WHERE email = %s",
                (role, email)
            )
    except Exception as e:
        print(f"Error updating user role: {e}")
        raise
    finally:
        if 'conn' in locals():
            conn.close()

@pytest.fixture
def driver():
    try:
        # Remove the ChromeDriverManager and use only chromedriver_autoinstaller
        chromedriver_autoinstaller.install()  # This will install the correct version
        
        # Настройка Chrome
        chrome_options = Options()
        # chrome_options.add_argument('--headless')  # Раскомментируйте для запуска без GUI
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        # Инициализация драйвера без Service
        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(10)
        
        yield driver
    except Exception as e:
        print(f"Error initializing WebDriver: {e}")
        raise
    finally:
        if 'driver' in locals():
            driver.quit()

def test_registration(driver):
    driver.get("http://localhost:3000/")
    driver.get("http://localhost:3000/register")
    
    # Fill registration form
    driver.find_element(By.ID, "name").send_keys("Test User")
    driver.find_element(By.ID, "email").send_keys("test@example.com")
    driver.find_element(By.ID, "password").send_keys("testpass123")
    
    # Select gender
    driver.find_element(By.ID, "gender").click()
    male = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "li[data-value='male']"))
    )
    male.click()
    
    # Handle DatePicker with exact selectors
    date_picker = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 
            "input.MuiInputBase-input.MuiOutlinedInput-input.MuiInputBase-inputAdornedEnd[placeholder='DD.MM.YYYY']"))
    )
    date_picker.click()
    # date_picker.clear()  # Clear any existing value
    time.sleep(1)
    date_picker.send_keys("01011990")
    time.sleep(1)

    # Submit form
    driver.find_element(By.CLASS_NAME, "MuiButton-containedPrimary").click()
    
    # Wait for redirect
    WebDriverWait(driver, 1000).until(
        EC.url_to_be("http://localhost:3000/login")
    )
    
    # Update user role to filmadmin
    update_user_role("test@example.com", "filmadmin")
    time.sleep(2)  # Wait for database transaction to complete


def test_login(driver):
    driver.get("http://localhost:3000/login")
    
    # Fill login form
    driver.find_element(By.ID, "email").send_keys("test@example.com")
    driver.find_element(By.ID, "password").send_keys("testpass123")
    
    # Submit form
    driver.find_element(By.CLASS_NAME, "MuiButton-containedPrimary").click()
    
    # Wait for redirect
    WebDriverWait(driver, 100).until(
        EC.url_to_be("http://localhost:3000/")
    ) 
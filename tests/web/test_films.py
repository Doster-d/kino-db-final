from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .test_auth import driver, test_login
import chromedriver_autoinstaller
import time

chromedriver_autoinstaller.install()

# get main page and sear for film here

def test_search_film(driver):
    driver.get("http://localhost:3000/")
    driver.get("http://localhost:3000/films")
    
    # Search film
    search_input = driver.find_element(By.ID, ":r0:")
    search_input.send_keys("Жизнь")
    
    # Using a single class from the button's class list
    driver.find_element(By.CLASS_NAME, "MuiButton-fullWidth").click()
    
    time.sleep(3)

    # Wait for results with the correct class
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "MuiLink-root"))
    )
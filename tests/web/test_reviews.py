from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .test_auth import driver, test_login
import chromedriver_autoinstaller
import time
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains


chromedriver_autoinstaller.install()


def test_add_review(driver):
    # First login
    test_login(driver)

    driver.get("http://localhost:3000/")
    driver.get("http://localhost:3000/films")
    
    # Redirect to first film
    first_film = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "MuiLink-root"))
    )
    first_film.click()
    
    # Add review through textarea
    review_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 
            "textarea.MuiInputBase-input.MuiOutlinedInput-input.MuiInputBase-inputMultiline"))
    )
    review_input.send_keys("Great film!")
    
    # Set rating (for example, 5 stars)
    rating_label = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 
            'label[for^=":r"][class="css-ykqdxu"]:nth-child(9)'))  # 5-я звезда
    )
    driver.execute_script("arguments[0].click();", rating_label)
    
    # Submit review through specific button
    submit_button = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 
            "button.MuiButton-containedPrimary[style*='margin-top: 1rem']"))
    )
    submit_button.click()
    
    # Wait for review to appear in table and check text
    review_cell = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 
            "tbody.MuiTableBody-root tr td.MuiTableCell-root:nth-child(2)"))
    )
    assert review_cell.text == "Great film!", f"Expected review text 'Great film!', but got '{review_cell.text}'"
    
    # Check username
    user_cell = driver.find_element(By.CSS_SELECTOR, 
        "tbody.MuiTableBody-root tr td.MuiTableCell-root:nth-child(1)")
    assert user_cell.text == "Test User", f"Expected username 'Test User', but got '{user_cell.text}'"

def test_edit_review(driver):
    # First login
    test_login(driver)
    
    driver.get("http://localhost:3000/films")
    
    # Redirect to first film
    first_film = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "MuiLink-root"))
    )
    first_film.click()
    
    # Find review editing field
    review_input = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 
            "textarea.MuiInputBase-input.MuiOutlinedInput-input.MuiInputBase-inputMultiline"))
    )
    
    # Clear text in several ways
    review_input.clear()
    driver.execute_script("arguments[0].value = '';", review_input)  # Clear through JavaScript
    review_input.click()  # Focus on field
    ActionChains(driver).key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).perform()  # Select all
    review_input.send_keys(Keys.DELETE)  # Delete selected
    time.sleep(1)  # Small pause
    review_input.send_keys("Updated review!")
    
    # Set new rating (for example, 7 stars)
    rating_label = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 
            'label[for^=":r"][class="css-ykqdxu"]:nth-child(13)'))  # 7-я звезда
    )
    driver.execute_script("arguments[0].click();", rating_label)
    
    # Submit form through specific button
    submit_button = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 
            "button.MuiButton-containedPrimary[style*='margin-top: 1rem']"))
    )
    submit_button.click()
    
    time.sleep(3)

    # Wait for update in table and check text
    review_cell = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, 
            "tbody.MuiTableBody-root tr td.MuiTableCell-root:nth-child(2)"))
    )
    assert review_cell.text == "Updated review!", f"Expected review text 'Updated review!', but got '{review_cell.text}'"
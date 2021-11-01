# selenium functions used to manipulate web browser
from selenium.webdriver import Chrome
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.remote.webelement import BaseWebElement
from webdriver_manager.chrome import ChromeDriverManager

# helper functions to mask automated scrape
from review.utils import literal_search, random_delay


def initiate_driver() -> Chrome:
    # create chrome driver instance and start
    s = Service(ChromeDriverManager().install())
    driver = Chrome(service=s)
    return driver


def start_session(driver: Chrome) -> Chrome:
    # start up the browser and go to Google Maps
    driver.get("https://www.google.co.uk/maps")
    # prevents detection as bot by setting driver implicit wait time
    driver.implicitly_wait(6)
    # find google button and click
    try:
        driver.find_element(By.XPATH, "//span[contains(text(),'I agree')]").click()
        return driver
    except NoSuchElementException:
        print("Unable to find button to accept terms")
        return driver


def search_maps(driver: Chrome, search_term: str) -> Chrome:
    while True:
        # find search bar and clear it
        search_bar: BaseWebElement = driver.find_element(By.NAME, "q")
        search_bar.clear()
        # create a delay in sending the keys to avoid
        for letter in search_term:
            random_delay(0.2, 0.1)
            search_bar.send_keys(letter)
        # 'press enter'
        search_bar.send_keys(Keys.RETURN)
        # check if input is equal to entered
        input_new = (
            driver.find_element(By.TAG_NAME, "title")
            .get_attribute("innerHTML")
            .split("-")[0]
            .strip()
        )
        if input_new == search_term:
            # if so then delay and correct to be exact
            random_delay(3)
            literal_search(driver)
            break
        else:
            # else we're done so wait then return
            random_delay(3)
            pass
    return driver

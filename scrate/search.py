# selenium functions used to manipulate web browser
from selenium.webdriver import Chrome
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.remote.webelement import BaseWebElement
from webdriver_manager.chrome import ChromeDriverManager


# helper functions to mask automated scrape
from scrate import get_module_logger, get_root_dir
from scrate.scrape import scrape_location
from scrate.utils import get_geo, literal_search, random_delay

# set logger for this module
logger = get_module_logger(__name__)


def initiate_driver() -> Chrome:
    # create chrome driver instance and start
    logger.info("Starting Chrome driver sessions, installing...")
    s = Service(ChromeDriverManager().install())
    # add headless window arguments
    # chrome_options = Options()
    # chrome_options.add_argument("--headless")
    # chrome_options.add_argument("--window-size={}".format("1920,1080"))
    driver = Chrome(service=s)
    logger.info("Chrome driver service installed, ready to go")
    return driver


def start_session(driver: Chrome) -> Chrome:
    # start up the browser and go to Google Maps
    logger.info("Directing to Google Maps and agree to terms")
    driver.get("https://www.google.co.uk/maps")
    # prevents detection as bot by setting driver implicit wait time
    driver.implicitly_wait(6)
    # find google button and click
    try:
        span_id = "//span[contains(text(),'I agree')]"
        driver.find_element(By.XPATH, span_id).click()
        logger.info("Terms accepted, ready to search location")
    except NoSuchElementException:
        logger.error("Unable to find accept terms button")
    return driver


def search_maps(driver: Chrome, search_term: str) -> Chrome:
    while True:
        # find search bar and clear it
        search_bar: BaseWebElement = driver.find_element(By.NAME, "q")
        search_bar.clear()
        # create a delay in sending the keys to avoid
        logger.info("Searching for {} in search bar".format(search_term))
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
    logger.info("Search for {} complete".format(search_term))
    return driver


def start_searched_session(place_name: str, place_type: str) -> Chrome:

    # initiate a chrome instance
    driver = initiate_driver()
    # start session
    driver = start_session(driver)
    # search maps for the location of where we want to scan
    driver = search_maps(driver, place_name)
    # search maps for the type of place we want e.g. cafe
    driver = search_maps(driver, place_type)
    return driver


def search_location(
    place_name: str,
    place_type: str,
    max_results: int = 100,
    max_reviews: int = 100,
    max_distance: float = 0.2,
) -> dict:

    # start chrome driver, nav to google, search place and type
    driver: Chrome = start_searched_session(place_name, place_type)
    # get original coords to prevent search straying too far
    orig_coords = get_geo(driver)
    random_delay(2)

    # try to identify raw results elements using url to gmaps data
    gmaps_xp = "//*[contains(@href,'https://www.google.co.uk/maps/place/')]"
    gmaps_results = driver.find_elements(By.XPATH, gmaps_xp)

    # if no results, report, close driver, return empty dict
    if len(gmaps_results) == 0:
        logger.error("No results for {} in: {}".format(place_type, place_name))
        # close
        driver.close()
        return {}
    else:
        # else we must have results so let's get scraping them
        logger.info("Results found, starting scraping")
        random_delay(2)

    # scrape results and return
    results = scrape_location(
        driver, max_results, max_reviews, orig_coords, max_distance
    )
    return results


if __name__ == "__main__":

    results = search_location(
        "granada", "restaurant", max_results=250, max_reviews=0
    )
    import pickle

    with open(get_root_dir() + "/reviews.pickle", "wb") as handle:
        pickle.dump(results, handle, protocol=pickle.HIGHEST_PROTOCOL)

from review import get_module_logger, get_root_dir
from typing import Tuple

# selenium functions used to manipulate web browser
from selenium.webdriver import Chrome
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.remote.webelement import BaseWebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


# helper functions to mask automated scrape
from review.popular_times import scrape_popular_times
from review.scrape import scrape_general_info, scrape_reviews
from review.utils import (
    back_to_results,
    click_element,
    get_geo,
    literal_search,
    random_delay,
    scroll_down_results,
)

# set logger for this module
logger = get_module_logger(__name__)


def initiate_driver() -> Chrome:
    # create chrome driver instance and start
    logger.info("Starting Chrome driver sessions, installing...")
    s = Service(ChromeDriverManager().install())
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


def scrape_location(
    driver: Chrome,
    max_res: int,
    max_revs: int,
    orig_coords: Tuple[float, float],
    max_distance: float,
) -> dict:

    # vars to keep track of our results
    results = {}
    page_results_processed = 0
    close_enough = True

    logger.info(
        "Scraping for {} results and {} reviews".format(max_res, max_revs)
    )
    # while still need more data and close enough
    while len(results.keys()) < max_res and close_enough:

        # fetch place results
        places_xp = (
            "//*[contains(@href,'https://www.google.co.uk/maps/place/')]"
        )
        gmaps_results = driver.find_elements(By.XPATH, places_xp)
        logger.info(
            "{} current results, {} processed".format(
                len(gmaps_results), page_results_processed
            )
        )
        # grab the singular result we are interested in currently
        r = gmaps_results[page_results_processed]
        logger.info("Starting processing {}".format(r))
        # open specific result to scrape
        click_element(driver, r)
        # wait until it has loaded properly
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.XPATH, "//tr[contains(@aria-label,'stars')]")
            )
        )

        # we have clicked on specific place, now to start scraping
        # first we check it is not too far away from initial search location
        place_coords = get_geo(driver)
        lat_diff = abs(place_coords[0] - orig_coords[0])
        lng_diff = abs(place_coords[1] - orig_coords[1])

        # check if we are too far away
        if lat_diff > max_distance or lng_diff > max_distance:
            # then we're too far
            logger.info("Too far from original query, going back")
            # exit loop as too far
            close_enough = False
            # update page res count so know to go to next page at 20
            page_results_processed += 1
            logger.info("Going back to paginated results")
            logger.info("------------------------------------")
            back_to_results(driver)
            # update so we have the recent count of results
            gmaps_results = driver.find_elements(By.XPATH, places_xp)
        else:
            # within distance, start scraping
            general_info = scrape_general_info(driver)
            # scrape popular times data that forms the busyness bar chart
            popular_times = scrape_popular_times(driver)
            # scrape the reviews data
            # if we don't want any or there aren't any then don't bother
            max_rev_count = min(general_info["review_count"], max_revs)
            if max_rev_count == 0:
                reviews = []
            else:
                reviews = scrape_reviews(driver, max_rev_count)

            # stick data in dictionary and return to results
            # use id from selenium element as unique ref
            pid = r.id
            results[pid] = {
                "general": general_info,
                "popular_times": popular_times,
                "reviews": reviews,
            }
            logger.info("Info scraped for r: {}".format(r))
            logger.info("Going back to paginated results")
            logger.info("------------------------------------")
            # update page results inspected so we know to go to next page at 20
            page_results_processed += 1
            back_to_results(driver)
            # update so we have the recent count of results
            gmaps_results = driver.find_elements(By.XPATH, places_xp)

        # if we've processed all our results
        if len(gmaps_results) <= page_results_processed:
            # if we have processed all results on this page
            if page_results_processed == 20:
                # go to the next page and reset our processed results counter
                logger.info("Loading new page of 20 results")
                # then we need to head on over to the next page of results
                next_button = driver.find_element(
                    By.XPATH, "//button[@aria-label=' Next page ']"
                )
                click_element(driver, next_button)
                page_results_processed = 0
                # grab our first set of new results
                random_delay(3)
                gmaps_results = driver.find_elements(By.XPATH, places_xp)
            else:
                # else we need to scroll down a bit to get new results
                while len(gmaps_results) <= page_results_processed:
                    logger.info("Scrolling to load new results")
                    logger.info(
                        "Have {} results but processed {}".format(
                            len(gmaps_results), page_results_processed
                        )
                    )
                    # scroll down, wait, then grab new results
                    results_xp = "//div[contains(@aria-label, 'Results for')]"
                    scroll_down_results(driver, results_xp)
                    random_delay(2)
                    gmaps_results = driver.find_elements(By.XPATH, places_xp)

    return results


def search_location(
    place_name: str,
    place_type: str,
    max_results: int = 100,
    max_reviews: int = 100,
    max_distance: float = 0.2,
) -> dict:

    # initiate a chrome instance
    driver = initiate_driver()
    # start session
    driver = start_session(driver)
    # search maps for the location of where we want to scan
    driver = search_maps(driver, place_name)
    # search maps for the type of place we want e.g. cafe
    driver = search_maps(driver, place_type)
    orig_coords = get_geo(driver)
    random_delay(2)

    # try to identify raw results elements using url to gmaps data
    gmaps_xp = "//*[contains(@href,'https://www.google.co.uk/maps/place/')]"
    gmaps_results = driver.find_elements(By.XPATH, gmaps_xp)

    # if no results, report, close driver, return empty list
    if len(gmaps_results) == 0:
        logger.error("No results for {} in: {}".format(place_type, place_name))
        # close
        driver.close()
        return {}
    else:
        # else we must have results so let's get scraping them
        logger.info("Results found, starting scraping")
        random_delay(3)

    # scrape results
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

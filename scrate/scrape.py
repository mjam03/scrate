# import usuals
from bs4 import BeautifulSoup
from typing import Tuple

# import selenium functions for chrome driver manipulation
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver import Chrome
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# helper functions to mask automated scrape
from scrate import get_module_logger
from scrate.popular_times import scrape_popular_times
from scrate.utils import (
    back_to_results,
    click_element,
    get_element_al_by_xpath,
    get_element_text_by_css,
    get_geo,
    random_delay,
    scroll_down_results,
    scroll_down_section,
)

# set logger for this module
logger = get_module_logger(__name__)


def get_rating_dist(soup: BeautifulSoup) -> list:

    rating_dist = []
    # get all divs
    for doc in soup.findAll("div"):
        # if div id is the pane
        if doc.get("id") == "pane":
            # then find all table elements in the pane
            # as the review distribution data is in a table
            for tr in doc.findAll("tr"):
                # print('tr is {}'.format(tr))
                # if table element has an aria label
                # and stars is in it
                if tr.get("aria-label") and "stars" in tr.get("aria-label"):
                    # then append this to dist
                    # print('tr label is {}'.format(tr.get('aria-label')))
                    rating_dist.append(tr.get("aria-label"))
    # return the dist
    return rating_dist


def scrape_general_info(driver: Chrome) -> dict:

    # storing dict
    general_info = {}

    # create bs4 object to help with parsing
    page_content: str = driver.page_source
    soup: BeautifulSoup = BeautifulSoup(page_content, "lxml")

    # strip place name from tab title
    try:
        general_info["name"] = soup.findAll("title")[0].text.replace(
            " - Google Maps", ""
        )
    except IndexError:
        general_info["name"] = ""
    # get place category
    cat_css = 'button[jsaction="pane.rating.category"]'
    general_info["category"] = get_element_text_by_css(driver, cat_css)
    # get price as count
    price_css = 'span[aria-label*="Price"]'
    general_info["price"] = len(get_element_text_by_css(driver, price_css))
    # get review count
    rc_css = 'button[jsaction="pane.rating.moreReviews"]'
    rc_raw: str = get_element_text_by_css(driver, rc_css)
    if rc_raw == "":
        rc = 0
    else:
        rc = int(
            rc_raw.replace(" reviews", "")
            .replace(" review", "")
            .replace(",", "")
        )
    general_info["review_count"] = rc
    # get overall rating
    rating_xp = "//ol[contains(@aria-label,'stars')]"
    rating_raw = get_element_al_by_xpath(driver, rating_xp)
    if rating_raw == "":
        rating = 0.0
    else:
        rating = float(rating_raw.replace("stars", "").replace(" ", ""))
        general_info["rating"] = rating
    # get rating distribution
    general_info["rating_dist"] = get_rating_dist(soup)
    # get opening hours
    op_hours_xp = "//div[contains(@aria-label, 'Saturday')]"
    op_hours_raw = get_element_al_by_xpath(driver, op_hours_xp)
    if op_hours_raw == "":
        general_info["opening_hours"] = []
    else:
        op_hours = op_hours_raw.split(".")[0].split(";")
        general_info["opening_hours"] = op_hours
    # return our data
    return general_info


def scrape_reviews(driver: Chrome, max_reviews: int) -> list:

    try:
        # wait until page has loaded the more reviews button
        reviews_button = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.XPATH, "//button[contains(@aria-label, 'More reviews')]")
            )
        )
        # click it
        click_element(driver, reviews_button)
    except NoSuchElementException:
        logger.error("Unable to locate the 'More reviews' button")

    # now we have clicked it, scroll down until can id enough reviews
    # check we have some reviews loaded
    reviews_exist = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located(
            (By.XPATH, "//div[contains(@jsan, 'data-review-id')]")
        )
    )
    reviews = []
    review_elements: list = []
    if reviews_exist:
        # fetch review elements
        review_elements = driver.find_elements(
            By.XPATH, "//div[contains(@jsan, 'data-review-id')]"
        )
        # while we haven't got enough reviews
        while len(review_elements) < max_reviews:
            # scroll down to load more
            scroll_down_section(driver, "div[class*='section-scrollbox']")
            # wait a bit
            random_delay(1)
            # grab our new set of reviews
            review_elements = driver.find_elements(
                By.XPATH, "//div[contains(@jsan, 'data-review-id')]"
            )
        # now we have enough reviews let's grab the data we want from them
        review_elements = review_elements[:max_reviews]
        for r in review_elements:
            review = {}
            review_data = r.text.split("\n")
            review["age"] = review_data[2]
            reviewer_review_count = (
                review_data[1]
                .replace("Local Guide ·", "")
                .replace("reviews", "")
                .replace("review", "")
                .replace(" ", "")
            )
            # if '1' in reviewer_review_count:
            #     review['reviewer_count'] = 1
            # else:
            review["reviewer_count"] = int(reviewer_review_count)
            rt_xp = "//span[contains(@aria-label, 'stars')]"
            rt = get_element_al_by_xpath(driver, rt_xp)
            rt = rt.replace("stars", "").replace(" ", "")
            review["rating"] = int(rt)
            reviews.append(review)

    # now let's go back out of the reviews section
    back_to_results(driver)
    return reviews


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
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//tr[contains(@aria-label,'stars')]")
                )
            )
            # we have clicked on specific place, now to start scraping
            # first check it is not too far away from initial search location
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
                # use url as pid
                pid = driver.current_url
                results[pid] = {
                    "general": general_info,
                    "popular_times": popular_times,
                    "reviews": reviews,
                }
                logger.info("Info scraped for r: {}".format(r))
                logger.info("Going back to paginated results")
                logger.info("------------------------------------")
                # update pg results inspected so know to go to next pg at 20
                page_results_processed += 1
                back_to_results(driver)
                # update so we have the recent count of results
                gmaps_results = driver.find_elements(By.XPATH, places_xp)

        except TimeoutException:
            # either it hasn't loaded
            # or it has no stars as no reviews
            # either way let's ditch it and move on
            page_results_processed += 1
            logger.info("Going back to paginated results")
            logger.info("------------------------------------")
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
                random_delay(2)
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
                    random_delay(1)
                    gmaps_results = driver.find_elements(By.XPATH, places_xp)

    return results

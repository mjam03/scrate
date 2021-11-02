# import usuals
from bs4 import BeautifulSoup
import logging

# import selenium functions for chrome driver manipulation
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver import Chrome
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# import helper functions for ease of web page navigation
from review.utils import (
    back_to_results,
    click_element,
    get_element_al_by_xpath,
    get_element_text_by_css,
    random_delay,
    scroll_down_section,
)

# set logger for this module
logger = logging.getLogger(__name__)


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
        rc = int(rc_raw.replace(" reviews", "").replace(",", ""))
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
            random_delay(2)
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

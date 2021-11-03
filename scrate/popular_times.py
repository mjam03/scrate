from bs4 import BeautifulSoup
from bs4.element import Tag
import datetime as dt

from selenium.webdriver import Chrome
from selenium.webdriver.common.by import By


def parse_popular_times(div: Tag, day_dict: dict) -> list:

    pop_data: list = []
    # get day as word from index
    day: str = day_dict[div.get("jsinstance")]
    # parse through busyness data
    for d in div.findAll("div"):
        # if aria-label exists and busy is in it
        if d.get("aria-label") and "busy" in d.get("aria-label"):
            # then parse it
            b_div = d.get("aria-label").split("% busy at ")
            if len(b_div) == 2:
                try:
                    dte = dt.datetime.strptime(b_div[1][:-1], "%I %p")
                    t = dte.time()
                    pop_data.append(
                        {
                            "Day": day,
                            "Time String": b_div[1][:-1],
                            "Time": t,
                            "Busyness": int(b_div[0]),
                        }
                    )
                except ValueError:
                    pass
    return pop_data


def scrape_popular_times(driver: Chrome) -> list:

    # check if popular times data exists on the page
    popular_times_elements: list = driver.find_elements(
        By.XPATH, "//div[contains(@aria-label, 'Popular times at')]"
    )

    data = []
    # if so then let's get going
    if len(popular_times_elements) > 0:

        # use beautiful soup to parse
        page_content: str = driver.page_source
        soup: BeautifulSoup = BeautifulSoup(page_content, "lxml")

        # define day dictionary
        day_dict = {
            "0": "Sun",
            "1": "Mon",
            "2": "Tue",
            "3": "Wed",
            "4": "Thu",
            "5": "Fri",
            "*6": "Sat",
        }
        d_ind = day_dict.keys()

        # obtain the part of the html we want
        for d in soup.findAll("div"):
            # only get the left hand pane
            if d.get("id") == "pane":
                # iterate through divs in the pane
                for pd in d.findAll("div"):
                    # if pane_div has aria-label and it is what we want
                    pt_txt = "Popular times at"
                    if pd.get("aria-label") and pt_txt in pd.get("aria-label"):
                        # then for each div in here
                        for pop_div in pd.findAll("div"):
                            # if jsinstance is one of our day indices
                            if (
                                pop_div.get("jsinstance")
                                and pop_div.get("jsinstance") in d_ind
                            ):
                                # then let's parse it
                                day_data: list = parse_popular_times(
                                    pop_div, day_dict
                                )
                                data.append(day_data)
    return data

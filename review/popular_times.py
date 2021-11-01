from bs4 import BeautifulSoup
import datetime as dt

from selenium.webdriver.common.by import By


def parse_popular_times(div, day_dict):

    pop_data = []

    # get day as word from index
    day = day_dict[div.get('jsinstance')]
    # parse through busyness data
    for busy_data in div.findAll('div'):
        # if aria-label exists and busy is in it
        if busy_data.get('aria-label') and 'busy' in busy_data.get('aria-label'):
            # then parse it
            hour_data = busy_data.get('aria-label').split('% busy at ')
            if len(hour_data) == 2:
                try:
                    pop_data.append({'Day': day,
                                     'Time String': hour_data[1][:-1],
                                     'Time': dt.datetime.strptime(hour_data[1][:-1], '%I %p').time(),
                                     'Busyness': int(hour_data[0])
                                     })
                except ValueError:
                    pass

    return pop_data


def scrape_popular_times(driver):

    # check if popular times data exists on the page
    popular_times_elements = driver.find_elements(
        By.XPATH, "//div[contains(@aria-label, 'Popular times at')]")

    # if so then let's get going
    if len(popular_times_elements) > 0:
        data = []

        # use beautiful soup to parse
        page_content = driver.page_source
        soup = BeautifulSoup(page_content, "lxml")

        # define day dictionary
        day_dict = {'0': 'Sun',
                    '1': 'Mon',
                    '2': 'Tue',
                    '3': 'Wed',
                    '4': 'Thu',
                    '5': 'Fri',
                    '*6': 'Sat'
                    }

        # obtain the part of the html we want
        for div in soup.findAll('div'):
            # only get the left hand pane
            if div.get('id') == 'pane':
                # iterate through divs in the pane
                for pane_div in div.findAll('div'):
                    # if pane_div has aria-label and it is what we want
                    if pane_div.get('aria-label') and 'Popular times at' in pane_div.get('aria-label'):
                        # then for each div in here
                        for pop_div in pane_div.findAll('div'):
                            # if jsinstance is one of our day indices
                            if pop_div.get('jsinstance') and pop_div.get('jsinstance') in day_dict.keys():
                                # then let's parse it
                                day_data = parse_popular_times(
                                    pop_div, day_dict)
                                data.append(day_data)
        return data

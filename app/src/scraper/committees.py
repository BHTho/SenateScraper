from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from datetime import date, datetime
import hashlib
import re
import json
import csv
import os
import time
# from app.src.utils import get_dynamodb
# from botocore.exceptions import NoCredentialsError, ClientError

class CommitteeScraper:
    def __init__(self, **kwargs):
        print(kwargs)
        self.base_url = "https://www.senate.gov"
        self._init_homepage_css()


    def _init_homepage_css(self):
        self.committee_urls = []
        self.committee_table_url = "/committees/index.htm"
        self.committee_link_starting_href = "/general/committee_membership/"
        self.href_cell = "tbody tr td:nth-child(4) a"


    def _scrape_links(self, driver):
        wait = WebDriverWait(driver, 2)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, self.committee_table_selector)))
        a_list = driver.find_elements(By.CSS_SELECTOR, self.href_cell)
        for elem in a_list:
            href = elem.get_attribute('href')
            if href.startswith(self.committee_link_starting_href):
                self.committee_urls.append(href)


    def scrape(self):
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        driver = None
        try:
            driver = webdriver.Chrome(options=chrome_options)
            print("Driver started...")
            driver.get(self.base_url)
            self._scrape_links(driver)
        except Exception as e:
            print("Scrape error:", repr(e))
            import traceback
            traceback.print_exc()
        finally:
            if driver:
                driver.quit()


scraper = CommitteeScraper()
scraper.scrape()

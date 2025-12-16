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
        self._init_committee_page_css()


    def _init_homepage_css(self):
        self.committee_urls = []
        self.committee_table_selector = "#listOfCommittees"
        self.committee_table_url = "/committees/index.htm"
        self.committee_link_starting_href = "/general/committee_membership/"
        self.href_cell = "tbody tr td:nth-child(4) a"


    def _init_committee_page_css(self):
        self.committee_name_selector = ".contenttitle"
        self.members_selector = "tbody:first-of-type tr:nth-child(2)"


    def _scrape_links(self, driver):
        driver.get(self.base_url+self.committee_table_url)
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, self.committee_table_selector)))
        a_list = driver.find_elements(By.CSS_SELECTOR, self.href_cell)
        for elem in a_list:
            href = elem.get_attribute('href')
            self.committee_urls.append(href)
        self.committee_urls = list(set(self.committee_urls))
        print(self.committee_urls)


    def _clean_committee_name(self, name: str) -> str:
        prefixes = [
            "Committee on ",
            "Joint Committee on ",
            "Joint Committee of ",
            "Select Committee on ",
            "Special Committee on "
        ]
        for prefix in prefixes:
            if name.startswith(prefix):
                name = name[len(prefix):]
                break
        name = name.replace(" and ", " & ")
        name = name.replace(" for ", " ")
        name = name.replace(" of ", " ")
        name = name.replace(",", "")
        name = name.replace(" ", "_")
        name = re.sub(r'[^a-zA-Z0-9_]', '', name)
        return name


    def _scrape_members(self, driver):
        for link in self.committee_urls:
            driver.get(link)
            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, self.members_selector)))
            members = driver.find_element(By.CSS_SELECTOR, self.members_selector)
            committee_name = driver.find_element(By.CSS_SELECTOR, self.committee_name_selector)
            print(self._clean_committee_name(committee_name.text))
            member_list = members.text.replace(',', ' ').split('\n')
            for member in member_list:
                print(member.split()[0:2])

            # store as : "senator_name, committees{}"


    def scrape(self):
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        driver = None
        try:
            driver = webdriver.Chrome(options=chrome_options)
            print("Driver started...")
            self._scrape_links(driver)
            self._scrape_members(driver)
        except Exception as e:
            print("Scrape error:", repr(e))
            import traceback
            traceback.print_exc()
        finally:
            if driver:
                driver.quit()


scraper = CommitteeScraper()
scraper.scrape()

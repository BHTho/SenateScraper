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
from app.src.utils import get_dynamodb
from botocore.exceptions import NoCredentialsError, ClientError


class SenateScraper:
    def __init__(self, **kwargs):
        print(kwargs)
        self._parse_user_args(kwargs)
        self.base_url = "https://efdsearch.senate.gov"
        self.start_url = f"{self.base_url}/search/home"
        self.agreeCheckbox_selector = "#agree_statement"
        self.senatorFiler_selector = "input.senator_filer"
        self.fromDate_field_selector = "#fromDate"
        self.searchButton_selector = "button.btn.btn-primary"
        self.resultsTable_selector = 'tbody'
        self.nextPageButton_selector = "#filedReports_next"
        self.links = []
        self.data = []
        self.used_ids = {}
        self._credentials_check()


    def _parse_user_args(self, kwargs):
        self.fromDate = kwargs.get('start_date', None)
        self.fromDate = self.fromDate.replace('-', '/')
        self.aws_region = os.getenv('AWS_REGION', None)
        self.dynamodb_table_name = os.getenv('DYNAMO_TABLE_NAME', None)
        self.verbose = kwargs.get('verbose', False)
        self.visible = kwargs.get('visible', False)
        self.output_aws = kwargs.get('output_aws', False)
        self.output_csv = kwargs.get('output_csv', False)


    def _credentials_check(self):
        if self.output_aws:
            assert self.aws_region, "AWS_REGION not set"
            assert self.dynamodb_table_name, "DYNAMO_TABLE_NAME not set"
            assert os.getenv('AWS_ACCESS_KEY', None), "AWS_ACCESS_KEY not set"
            assert os.getenv('AWS_SECRET_KEY', None), "AWS_SECRET_KEY not set"
        assert self.fromDate, "START_DATE not set"
        assert re.match(r'^\d{2}/\d{2}/\d{4}$', self.fromDate), "START_DATE must be in MM/DD/YYYY format"
        parsed_date = datetime.strptime(self.fromDate, "%m/%d/%Y").date()
        assert parsed_date <= date.today(), "START_DATE cannot be in the future"
        assert parsed_date >= date(2015, 1, 1), "START_DATE cannot be before 2015-01-01"


    def _is_next_enabled(self, driver):
        next_button = driver.find_element(By.CSS_SELECTOR, self.nextPageButton_selector)
        class_attr = next_button.get_attribute("class")
        return "disabled" not in class_attr


    def _get_id(self, record_dict: dict) -> str:
        dedupe_fields = (x for x in record_dict.keys() if x != 'id')
        dedupe_dict = {k: record_dict[k] for k in dedupe_fields}
        record_str = json.dumps(dedupe_dict, sort_keys=True).encode('utf-8')
        return hashlib.md5(record_str).hexdigest()


    def _agreeToTerms(self, driver):
        wait = WebDriverWait(driver, 10)
        checkbox = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, self.agreeCheckbox_selector)))
        checkbox.click()


    def _filterSearch(self, driver):
        wait = WebDriverWait(driver, 10)
        # Senator CheckBox
        senator_checkbox = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, self.senatorFiler_selector)))
        senator_checkbox.click()
        # Date Filter
        date_field = driver.find_element(By.CSS_SELECTOR, self.fromDate_field_selector)
        date_field.clear()
        date_field.send_keys(self.fromDate)
        # Execute Search
        search_button = driver.find_element(By.CSS_SELECTOR, self.searchButton_selector)
        search_button.click()


    def _getLinks(self, driver):
        import time
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, self.resultsTable_selector)))
        
        links = driver.find_elements(By.CSS_SELECTOR, f"{self.resultsTable_selector} a")
        for link in links:
            href = link.get_attribute("href")
            if href and href.startswith(f"{self.base_url}/search/view/ptr"):
                self.links.append(href)
        
        if self._is_next_enabled(driver):
            next_button = driver.find_element(By.CSS_SELECTOR, self.nextPageButton_selector)
            next_button.click()
            time.sleep(2)
            self._getLinks(driver)


    def _formatDate(self, date_str: str) -> str:
        month, day, year = date_str.split('/')
        return f"{year}-{int(month):02d}-{int(day):02d}"


    def _scrapePages(self, driver):
        import time
        wait = WebDriverWait(driver, 10)
        
        for link in self.links:
            driver.get(link)
            print(link)
            time.sleep(1)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, self.resultsTable_selector)))
            
            filer = driver.find_element(By.CSS_SELECTOR, "h2.filedReport")
            table_rows = driver.find_elements(By.CSS_SELECTOR, f"{self.resultsTable_selector} tr")
            
            for row in table_rows:
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) < 9:
                    continue
                    
                result = {
                    'id': None,
                    'Filer': re.search(r'\((.*?)\)', filer.text).group(1),
                    'Date': self._formatDate(cells[1].text),
                    'Owner': cells[2].text,
                    'Ticker': None if cells[3].text == '--' else cells[3].text,
                    'Asset_Name': cells[4].text,
                    'Asset_Type': cells[5].text,
                    'Tx_Type': cells[6].text,
                    'Amount': cells[7].text,
                    'Comment': None if cells[8].text == '--' else cells[8].text,
                }
                id = self._get_id(result)
                if self.used_ids.get(id, False):
                    if self.verbose:
                        print("Duplicate record found, skipping:", result)
                    continue
                self.used_ids[id] = True
                result['id'] = id
                if self.verbose:
                    print("Scraped result:", result)
                self.data.append(result)


    def _saveCSV(self):
        if not self.data:
            return
        keys = self.data[0].keys()
        with open('senate_disclosures.csv', 'w', newline='', encoding='utf-8') as output_file:
            dict_writer = csv.DictWriter(output_file, fieldnames=keys)
            dict_writer.writeheader()
            dict_writer.writerows(self.data)


    def _saveToAWS(self):
        print("Saving results to AWS DynamoDB...")
        if not self.data:
            print("No data to save, skipping AWS save.")
            return
        dynamodb = get_dynamodb()
        table = dynamodb.Table(self.dynamodb_table_name)
        with table.batch_writer() as batch:
            for item in self.data:
                try:
                    batch.put_item(Item=item)
                except (NoCredentialsError, ClientError) as e:
                    print("AWS save error:", repr(e))
                    return
        print(f"Saved {len(self.data)} records to DynamoDB table {self.dynamodb_table_name}.")


    def saveResults(self):
        if not self.data:
            return
        if self.output_csv:
            self._saveCSV()
        if self.output_aws:
            self._saveToAWS()


    def scrape(self):
        chrome_options = Options()
        if not self.visible:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        driver = None
        try:
            driver = webdriver.Chrome(options=chrome_options)
            print("Driver started, hunting down links...")
            driver.get(self.start_url)
            self._agreeToTerms(driver)
            self._filterSearch(driver)
            import time
            time.sleep(3)
            self._getLinks(driver)
            self.links = list(set(self.links))
            if not self.links:
                print("No links found, stopping scrape.")
                return
            print(f"Found {len(self.links)} links, scraping pages...")
            self._scrapePages(driver)
            print(f"Scraped {len(self.data)} records.")
        except Exception as e:
            print("Scrape error:", repr(e))
            import traceback
            traceback.print_exc()
        finally:
            if driver:
                driver.quit()

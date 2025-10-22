from seleniumbase import SB
from datetime import date, timedelta
import hashlib
import re
import json
import csv
import os
import boto3
from botocore.exceptions import NoCredentialsError, ClientError


class SenateScraper:
    def __init__(self):
        self.base_url = "https://efdsearch.senate.gov"
        self.start_url = f"{self.base_url}/search/home"
        self.agreeCheckbox_selector = "#agree_statement"
        self.senatorFiler_selector = "input.senator_filer"
        self.fromDate_field_selector = "#fromDate"
        self.searchButton_selector = "button.btn.btn-primary"
        # self.fromDate = self._getFromDate()
        self.fromDate = "01/01/2015"
        self.resultsTable_selector = 'tbody'
        self.nextPageButton_selector = "#filedReports_next"
        self.links = []
        self.data = []
        self.used_ids = {}
        self.aws_region = os.getenv('AWS_REGION', None)
        self.dynamodb_table_name = os.getenv('DYNAMO_TABLE_NAME', None)
        self._credentials_check()


    def _credentials_check(self):
        if os.getenv('OUTPUT_AWS', '0') == '1':
            assert self.aws_region, "AWS_REGION not set"
            assert self.dynamodb_table_name, "DYNAMO_TABLE_NAME not set"
            assert os.getenv('AWS_ACCESS_KEY', None), "AWS_ACCESS_KEY not set"
            assert os.getenv('AWS_SECRET_KEY', None), "AWS_SECRET_KEY not set"


    # def _getFromDate(self):
    #     today = date.today()
    #     one_day_ago = today - timedelta(days=1)
    #     return one_day_ago.strftime("%m/%d/%Y")


    def _is_next_enabled(self, sb: SB):
        next_button = sb.find_element(self.nextPageButton_selector)
        class_attr = next_button.get_attribute("class")
        return "disabled" not in class_attr


    def _get_id(self, record_dict: dict) -> str:
        dedupe_fields = (x for x in record_dict.keys() if x != 'id')
        dedupe_dict = {k: record_dict[k] for k in dedupe_fields}
        record_str = json.dumps(dedupe_dict, sort_keys=True).encode('utf-8')
        return hashlib.md5(record_str).hexdigest()


    def _agreeToTerms(self, sb: SB):
        sb.wait_for_element(self.agreeCheckbox_selector, timeout=10)
        sb.assert_element(self.agreeCheckbox_selector)
        sb.click(self.agreeCheckbox_selector)


    def _filterSearch(self, sb: SB):
        # Senator CheckBox
        sb.wait_for_element(self.senatorFiler_selector, timeout=10)
        sb.assert_element(self.senatorFiler_selector)
        sb.click(self.senatorFiler_selector)
        # Date Filter
        sb.assert_element(self.fromDate_field_selector)
        sb.fill(self.fromDate_field_selector, self.fromDate)
        # Execute Search
        sb.assert_element(self.searchButton_selector)
        sb.click(self.searchButton_selector)


    def _getLinks(self, sb: SB):
        sb.assert_element(self.resultsTable_selector)
        links = sb.find_elements(f"{self.resultsTable_selector} a")
        for link in links:
            if link.get_attribute("href").startswith(f"{self.base_url}/search/view/ptr"):
                self.links.append(link.get_attribute("href"))
        if self._is_next_enabled(sb):
            sb.click(self.nextPageButton_selector)
            sb.wait(2)
            self._getLinks(sb)


    def _formatDate(self, date_str: str) -> str:
        month, day, year = date_str.split('/')
        return f"{year}-{int(month):02d}-{int(day):02d}"


    def _scrapePages(self, sb: SB):
        verbose = os.getenv('VERBOSE', '0')
        for link in self.links:
            sb.open(link)
            sb.wait(1)
            sb.assert_element(self.resultsTable_selector)
            table_rows = sb.find_elements(f"{self.resultsTable_selector} tr")
            for row in table_rows:
                filer = sb.find_element("h2.filedReport")
                cells = row.find_elements("css selector", "td")
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
                    if verbose == '1':
                        print("Duplicate record found, skipping:", result)
                    continue
                self.used_ids[id] = True
                result['id'] = id
                if verbose == '1':
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
        dynamodb = boto3.resource(
            'dynamodb',
            region_name=self.aws_region,
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY'),
            aws_secret_access_key=os.getenv('AWS_SECRET_KEY')
        )
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
        if os.getenv('OUTPUT_CSV', '0') == '1':
            self._saveCSV()
        if os.getenv('OUTPUT_AWS', '0') == '1':
            self._saveToAWS()


    def scrape(self):
        try:
            with SB(uc=True, test=True, headless=True) as sb:
                print("SB started, hunting down links...")
                sb.open(self.start_url)
                self._agreeToTerms(sb)
                self._filterSearch(sb)
                sb.wait(3)
                self._getLinks(sb)
                self.links = list(set(self.links))
                if not self.links:
                    print("No links found, stopping scrape.")
                    return
                print(f"Found {len(self.links)} links, scraping pages...")
                self._scrapePages(sb)
                print(f"Scraped {len(self.data)} records.")
        except Exception as e:
            print("Scrape error:", repr(e))

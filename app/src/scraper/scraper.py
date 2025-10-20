from seleniumbase import SB
from datetime import date, timedelta
import re
import uuid


class SenateScraper:
    def __init__(self):
        self.base_url = "https://efdsearch.senate.gov"
        self.start_url = f"{self.base_url}/search/home"
        self.agreeCheckbox_selector = "#agree_statement"
        self.senatorFiler_selector = "input.senator_filer"
        self.fromDate_field_selector = "#fromDate"
        self.searchButton_selector = "button.btn.btn-primary"
        # self.fromDate = self._getFromDate()
        self.fromDate = "10/01/2025" # hardcoded for testing
        self.resultsTable_selector = 'tbody'
        self.nextPageButton_selector = "#filedReports_next"
        self.links = []
        self.data = []

    # def _getFromDate(self):
    #     today = date.today()
    #     one_week_ago = today - timedelta(weeks=1)
    #     return one_week_ago.strftime("%m/%d/%Y")

    def _is_next_enabled(self, sb: SB):
        next_button = sb.find_element(self.nextPageButton_selector)
        class_attr = next_button.get_attribute("class")
        return "disabled" not in class_attr


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
        for link in self.links:
            sb.open(link)
            sb.wait(1)
            sb.assert_element(self.resultsTable_selector)
            table_rows = sb.find_elements(f"{self.resultsTable_selector} tr")
            for row in table_rows:
                filer = sb.find_element("h2.filedReport")
                cells = row.find_elements("css selector", "td")
                result = {
                    'id': str(uuid.uuid4()),
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
                print("Scraped result:", result)
                self.data.append(result)


    def scrape(self):
        try:
            with SB(uc=True, test=True, headless=True) as sb:
                print("SB started, opening page:", self.start_url)
                sb.open(self.start_url)
                self._agreeToTerms(sb)
                self._filterSearch(sb)
                sb.wait(3)
                self._getLinks(sb)
                self.links = list(set(self.links))
                if not self.links:
                    return
                self._scrapePages(sb)
        except Exception as e:
            print("Scrape error:", repr(e))

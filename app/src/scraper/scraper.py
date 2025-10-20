from seleniumbase import SB
from datetime import date, timedelta


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

    # def _getFromDate(self):
    #     today = date.today()
    #     one_week_ago = today - timedelta(weeks=1)
    #     return one_week_ago.strftime("%m/%d/%Y")

    def scrape(self):
        try:
            with SB(uc=True, test=True, headless=True) as sb:
                print("SB started, opening page:", self.start_url)
                sb.open(self.start_url)
                sb.wait_for_element(self.agreeCheckbox_selector, timeout=10)
                sb.click(self.agreeCheckbox_selector)
                sb.wait_for_element(self.senatorFiler_selector, timeout=10)
                sb.click(self.senatorFiler_selector)
                sb.fill(self.fromDate_field_selector, self.fromDate)
                sb.click(self.searchButton_selector)
                sb.wait(2)
                print(sb.get_page_source())
        except Exception as e:
            print("Scrape error:", repr(e))
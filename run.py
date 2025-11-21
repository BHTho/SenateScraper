import sys
import os

curr_dir = os.path.dirname(os.path.abspath(__file__))
if curr_dir not in sys.path:
    sys.path.insert(0, curr_dir)

import argparse
from app.src.scraper.scraper import SenateScraper
from dotenv import load_dotenv

load_dotenv()

def scrape(**kwargs):
    print("Scraping started...")
    scraper = SenateScraper(**kwargs)
    scraper.scrape()
    scraper.saveResults()
    print("Scraping finished.")


def main():
    parser = argparse.ArgumentParser(description="Senate Scraper")
    parser.add_argument("--start-date", type=str, help="Start date for scraping (MM-DD-YYYY)")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    parser.add_argument("--output-aws", action="store_true", help="Save results to AWS DynamoDB")
    parser.add_argument("--output-csv", action="store_true", help="Save results to CSV file")
    parser.add_argument("--visible", action="store_true", help="Run scraper with visible browser window")
    args = parser.parse_args()

    assert args.start_date is not None, "Start date must be provided using --start-date"
    assert args.output_aws or args.output_csv, "At least one output method must be specified (--output-aws or --output-csv)"
    scrape(**vars(args))

if __name__ == "__main__":
    main()
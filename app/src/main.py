import asyncio
from scraper.scraper import SenateScraper


async def scrape():
    print("Scraping started...")
    scraper = SenateScraper()
    scraper.scrape()
    scraper.saveResults()
    print("Scraping finished.")


if __name__ == "__main__":
    asyncio.run(scrape())

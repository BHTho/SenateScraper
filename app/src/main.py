import asyncio


async def scrape():
    print("Scraping started...")
    await asyncio.sleep(2)
    print("Scraping finished.")


if __name__ == "__main__":
    asyncio.run(scrape())
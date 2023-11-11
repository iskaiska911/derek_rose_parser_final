from parser import max_page_derek,scrape_items
from decouple import config
import queue
from scrapfly import ScrapeApiResponse, ScrapeConfig, ScrapflyClient
import numpy as np
import time
import threading
from tools import post_products
import asyncio

link_selector='product-item>div>a'
base_url='https://www.derek-rose.com/'

SERVER_NUMBER = int(config('SERVER_NUMBER'))
NUM_PROCESSES = int(config('NUM_PROCESSES'))


SCRAPFLY = ScrapflyClient(key=config('SCRAPFLY_KEY'), max_concurrency=20)
BASE_CONFIG = {
    "asp": True,
    "country":"US"
}


def get_scrapfly_key(url):
    # Add your logic to determine the key based on the URL here
    if "nflshop.com" in url:
        return ScrapflyClient(key=config('SCRAPFLY_KEY_NFL'), max_concurrency=20)  # Change this to the appropriate config key
    if "shop.nhl.com" in url:
        return ScrapflyClient(key=config('SCRAPFLY_KEY_NHL'), max_concurrency=20)
    if "mlbshop.com" in url:
        return ScrapflyClient(key=config('SCRAPFLY_KEY_MLB'), max_concurrency=20)
    else:
        return ScrapflyClient(key=config('SCRAPFLY_KEY'), max_concurrency=20)

def run_async_scrape_item(url, result_queue):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    # loop = asyncio.get_event_loop()
    time.sleep(0.4)
    product = loop.run_until_complete(scrape_items(url,SCRAPFLY))
    result_queue.put(product)


def scarpe_item_links():
    pages_amount, items_amount=max_page_derek("https://www.derek-rose.com/collections/all?sort_by=title-ascending&filter.p.m.custom.global_market_availability=1",SCRAPFLY)

    item_links=[]

    for i in range(0,pages_amount+1):
        print(f'page {i} out of {pages_amount+1}')
        links=SCRAPFLY.scrape(ScrapeConfig(url=(f"https://www.derek-rose.com/collections/all?sort_by=title-ascending&filter.p.m.custom.global_market_availability=1&page={i}")))
        item_links.append(['https://www.derek-rose.com'+i.attrs['href'] for i in links.soup.select(link_selector)])
    item_links = list(set([item for sublist in item_links for item in sublist]))

    values = np.array_split(item_links, len(item_links) / NUM_PROCESSES)
    return values

async def scrape_all_items(formatted_items_links):
    for items_link_parts in formatted_items_links:
        result_queue = queue.Queue()
        threads = []
        for i in items_link_parts:
            thread = threading.Thread(target=run_async_scrape_item, args=(i, result_queue))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()
        results = []
        while not result_queue.empty():
            results.append(result_queue.get())

        post_products(base_url,results)
        print("All treads have completed successfully")

async def run_scrape_all_items(values):
    await scrape_all_items(values)

if __name__ == "__main__":
    #base_url=sys.argv[1]
    SCRAPFLY = get_scrapfly_key(base_url)
    values=scarpe_item_links()
    asyncio.run(run_scrape_all_items(values))









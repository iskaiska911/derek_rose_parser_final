import asyncio
import sys
import threading
import time
import threading
from parser import parse_companies,get_filters,get_pages,scrape_items
from pathlib import Path
import numpy as np
from decouple import config
import queue
from scrapfly import ScrapeApiResponse, ScrapeConfig, ScrapflyClient
#import stockx
from tools import post_products
import httpx
import asyncio
from time import time,sleep
from loguru import logger as log


output = Path(__file__).parent / "results"
output.mkdir(exist_ok=True)

SERVER_NUMBER = int(config('SERVER_NUMBER'))
NUM_PROCESSES = int(config('NUM_PROCESSES'))

SCRAPFLY = ScrapflyClient(key=config('SCRAPFLY_KEY'), max_concurrency=20)
BASE_CONFIG = {
    "asp": True,
    "country":"US"
}


price_selector = 'div[class="layout-row pdp-price"]>div.price-card>div>div>span>span>span.money-value>span.sr-only'
title_selector = 'h1[data-talos="labelPdpProductTitle"]'
size_selector = 'a.size-selector-button.available'
image_selector = 'div[class="carousel-container large-pdp-image"]>div>img'

#base_url="https://shop.nhl.com/"

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
    sleep(0.4)
    product = loop.run_until_complete(scrape_items(url,SCRAPFLY))
    result_queue.put(product)


async def scrape_company(base_url:str,company:str, SCRAPFLY,BASE_CONFIG):
    final_items_links=[]
    _first_start=time()
    filters = list(set(get_filters(base_url,company,SCRAPFLY)))
    filters=[i for i in filters if i[1] in ['Bags',
                                            'Dresses',
                                            'Footwear',
                                            'Hats',
                                            'Hoodies & Sweatshirts',
                                            'Jackets',
                                            'Jerseys',
                                            'Pants',
                                            'Polos',
                                            'Shirts & Sweaters',
                                            'Shorts',
                                            'Sleepwear & Underwear',
                                            'Swim Collection',
                                            'T-Shirts',]]
    for filter_element in filters:
        filter_name=filter_element[1]
        filter_index = filters.index(filter_element)
        max_page = get_pages(base_url,filter_element[0],SCRAPFLY)
        items_links = []
        for i in range(1, max_page+1):
            print(f"scraping filter {filter_index} out of {len(filters)}\n"
                  f"page {i} out of {max_page} by filter {filter_name}")
            _start = time()
            url = base_url + filter_element[0] + "?pageSize=72&pageNumber={}&sortOption=TopSellers".format(i)
            try:
                items_links.append(await SCRAPFLY.async_scrape(ScrapeConfig(url=url)))
            except Exception as e:
                log.info(e)
                continue
            print(f"finished scraping page number {i} in {time() - _start:.2f} seconds")
            final_items_links.append([base_url +
                                      items_links[i].soup.select('div.product-image-container>a')[j].attrs['href']+'@#$'+filter_name for i
                                      in
                                      range(0, len(items_links)) for j in
                                      range(0, len(items_links[i].soup.select('div.product-image-container>a')))]) ### '@#$' - колхозное решение с разделителем передаваемым в урл
            print(f"sum of items by company {len(final_items_links)}")
    print(f"finished scraping links by one company in {((time() - _first_start) / 60):.2f} mins")

    final_items_links = list(set([item for sublist in final_items_links for item in sublist]))
    print(f"###############----amount of requests {len(final_items_links)}----###############")

    formatted_items_links = np.array_split(final_items_links, len(final_items_links) / NUM_PROCESSES)
    return formatted_items_links


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


async def run_scrape_commands(base_url,BASE_CONFIG):
    companies=parse_companies(base_url,SCRAPFLY)
    print(f"############ number of commands {len(companies)}#########################")
    thread_companies=[scrape_company(base_url,i,SCRAPFLY,BASE_CONFIG) for i in companies[0:4]]
    values = await asyncio.gather(*thread_companies)
    values = [str(item) for sublist1 in values for sublist2 in sublist1 for item in sublist2]
    values=np.array_split(values, len(values) / NUM_PROCESSES)
    return values


async def run_scrape_all_items(values):
    await scrape_all_items(values)




if __name__ == "__main__":
    base_url='https://www.nflshop.com/'
    #base_url=sys.argv[1]
    SCRAPFLY = get_scrapfly_key(base_url)
    values=asyncio.run(run_scrape_commands(base_url,BASE_CONFIG))
    asyncio.run(run_scrape_all_items(values))

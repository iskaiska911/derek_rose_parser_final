import json
import math
import time
from typing import Dict, List

import requests
from loguru import logger as log
from nested_lookup import nested_lookup
from scrapfly import ScrapeApiResponse, ScrapeConfig, ScrapflyClient
import re
import bs4 as bs

from decouple import config
from tools import get_unique_pairs


#base_url="https://shop.nhl.com/"
company_selector = 'li.entity-item>a'
filter_selector= 'a.side-nav-facet-item.hide-radio-button'
amount_selector='[data-talos="itemCount"]'
#filter_text_selector='ul.filter-selector>li>a'


def parse_companies(base_url,scrapfly: ScrapflyClient):
    result = scrapfly.scrape(ScrapeConfig(url=base_url))
    companies = [result.soup.select(company_selector)[i].attrs['href'] for i in
             range(0, len(result.soup.select(company_selector)))]
    log.info(f"scraping commands {len(companies)}", base_url)
    return companies


def get_filters(base_url,company_link, scrapfly: ScrapflyClient):
    log.info("scraping company filters {}", company_link)
    company_page=scrapfly.scrape(ScrapeConfig(url=base_url + company_link))

    filters = get_unique_pairs([[company_page.soup.select(filter_selector)[j].attrs['href'],company_page.soup.select(filter_selector)[j].text ] for j
               in range(len(company_page.soup.select(filter_selector)))])



    return filters

def get_pages(base_url,filter,scrapfly: ScrapflyClient):
    try:
        pattern = r'\d+'
        page_content = scrapfly.scrape(ScrapeConfig(url=base_url + filter))
        amount = page_content.soup.select(amount_selector)[0].text,
        amount = int(re.findall(pattern, amount[0])[-1])
        page = math.ceil(amount / 72)
        return page
    except Exception as e:
        log.info(e)
        return 1

def parse_items(base_url,filter,page,scrapfly: ScrapflyClient) -> List:
    items = []
    try:
        for i in range(0,page):
            items.append(scrapfly.scrape(ScrapeConfig(url=base_url+filter +"?pageSize=72&pageNumber={}&sortOption=TopSellers".format(page))))
    except Exception as e:
        log.info(e)
    return items


async def scrape_items(url,scrapfly: ScrapflyClient):
    log.info("scraping item {}", url)
    result = await scrapfly.async_scrape(ScrapeConfig(str(url)))
    log.info(f"Requesting {url} result Status {result.status_code}")
    product = {"urs":url,
                    "name":result.soup.select('h1.product-meta__title.heading')[0].text,
                    "slug": result.soup.select("span.breadcrumb__link")[0].text,
                    "price": result.soup.select('span.price.price--large')[0].text.replace('\n',' '),
                    "last_sale":"",
                    "filter": "",
                    "brand":"derek rose",
                   }
    try:
        product["description"] =result.soup.select('div.product-tabs__content>div')[0].text.replace('Size Chart','')
    except:
        product["description"] = ""
    try:
        category_list=[i.text for i in result.soup.select('''a.breadcrumb__link''')]
        product["category"] = category_list
    except:
        product["category"] = ""
    try:
        product["characteristics"] = result.soup.select('div.product-tabs__content>div')[1].text
    except:
        product["characteristics"] = ""
    try:
        product["images"] = [i.contents[1].attrs['src'] for i in result.soup.select('div[class="product__media-image-wrapper aspect-ratio aspect-ratio--natural"]')]
    except:
        product["images"] = ""
    try:
        product['variants'] = [i.text.replace('\n','') for i in result.soup.select('div[class="block-swatch"]')]
    except:
        product['variants'] = ""
    else:
        pass

    if 'Women' in product["category"]:
        product["Gender"]="Women"
    elif 'Men' in product["category"]:
        product["Gender"] = "Men"
    else:
        product["Gender"] = ""

    return product



def max_page_derek(base_url,scrapfly: ScrapflyClient):
    req= scrapfly.scrape(ScrapeConfig(url=base_url))
    page_products=16
    soup = req.soup.select("span[class='product-facet__meta-bar-item product-facet__meta-bar-item--count']")[0].text
    product_amount = int(''.join(filter(str.isdigit, soup)))
    max_page = math.ceil(product_amount / page_products)
    return max_page,product_amount
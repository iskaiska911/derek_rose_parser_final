import json
import datetime
from itertools import combinations
import requests
from loguru import logger as log

def post_products(base_url,products_formatted):
    shops = ['mlb', 'nfl', 'nhl', 'nba','leather','derek-rose']
    for shop in shops:
        if shop in base_url:
            filename=shop

    filename=f"results/"+filename+str(datetime.datetime.now().strftime("%Y_%m_%d-%I_%M_%S_%p")+'.json')
    with open(filename, 'w') as f:
        json.dump(products_formatted, f)


def get_unique_pairs(list_of_lists):
    unique_pairs = set()
    for sublist in list_of_lists:
        for pair in combinations(sublist, 2):
            unique_pairs.add(tuple(sorted(pair)))

    return list(unique_pairs)
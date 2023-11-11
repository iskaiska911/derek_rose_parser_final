import re

# Define the URLs
url = "https://shop.nhl.com/"

# Regular expression pattern to match the desired parts
pattern = r"https://(?:www\.)?(mlb|nhl|nfl)"

# Iterate through the URLs and extract the parts
shops=['mlb','nfl','nhl','nba']
for shop in shops:
    if shop in url:
        print(shop)



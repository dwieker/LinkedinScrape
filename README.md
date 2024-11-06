# Linkedin Scraper

This repo contains 2 scripts:

### search_google_multi_thread.py
Accepts a CSV file containing a `name` and `extra_info` column and searches Google to find the best matching linkedin profile page. `extra_info` should contain all known relevant information to narrow the search, such as hometown, specialty, etc.

Append a `profile_url` column to the provided input CSV file. If this field is already populated, skip it -- this allows the script to be stopped and restarted without redundantly re-searching the same people.

Google excels at catching scripted searches, so I rely on a paid subscription to https://developers.oxylabs.io/scraper-apis/web-scraper-api to handle the google queries. There is a free trial available, but once that ends the running cost is still very small. You must create a web scraper API username and password.
  
### scrape_linkedin.py
Accepts a list of linkedin profile urls (which can be generated using the previous script, or through any other means) and scrapes their recent post activity. The output CSV will contain one row per post, with the schema:
- `profile_url`
- `name`
- `bio`
- `followers`
- `likes`
- `reposts`
- `comments`
- `post_age`
- `text`
- `is_repost`
- `post_type`
- `post_id`

This script relies on selenium + chrome to surf linkedin.

Linkedin excels at bot detection, so the script is careful to run the scrape slowly, and will take long periodic breaks. The break duration can be configured through the command line arguments -- for now, I've left decent default values.

## Dependencies
Install dependencies with `pip install -r requirements.txt`

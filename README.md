# Linkedin Scraper

This repo contains 2 scripts:

### search_google_multi_thread.py
Accepts a CSV file containing a `name` and `extra_info` column. Executes a google search for each row with the form **"linkedin {name} {extra info}"** and writes the top linkedin profile search result back to the input CSV file in a `profile_url` column.

`extra_info` should contain all known relevant information to narrow the search, such as hometown, specialty, etc.

When the `profile_url` field is already populated, skip the row -- this allows the script to be stopped and restarted without redundantly re-searching the same people.

Not all searches yield a linkedin profile. Write `NOT FOUND` in these cases.

Google excels at catching scripted searches, so I rely on a paid subscription to https://developers.oxylabs.io/scraper-apis/web-scraper-api to handle Google queries. There is a free trial available, but once that ends the running cost is still very small. You must create a web scraper API username and password and provide them as command line arguments.
  
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

Linkedin excels at bot detection, so the scrape executes slowly and will takes long periodic breaks. The break duration can be configured through the command line arguments -- for now, I've left decent default values.

Note you may need to provide a --chrome-version command line argument depending on your current chrome version. Try running the script first and you may see an error containing the chrome version you need to provide.

## Dependencies
Install dependencies with `pip install -r requirements.txt`

import json
import logging
import random
import time
from argparse import ArgumentParser

import pandas
from selenium import webdriver

from src.linkedin_post_scraper import LinkedinPostScraper

if __name__ == "__main__":
    arg_parser = ArgumentParser()
    arg_parser.add_argument("--email", required=True, help="Linkedin Email")
    arg_parser.add_argument("--password", required=True, help="Linkedin Password")
    arg_parser.add_argument(
        "--input",
        required=True,
        help="CSV containing a profile_url column. URLs should be of the form https://www.linkedin.com/in/profile_id",
    )
    arg_parser.add_argument(
        "--output",
        required=True,
        help="Output CSV path. If it already exists, append results to it, unless --override is provided",
    )
    arg_parser.add_argument(
        "--save-every", type=int, default=3, help="Save to disk every N profiles"
    )
    arg_parser.add_argument(
        "--headless", default=False, action="store_true", help="Do not display browser"
    )
    arg_parser.add_argument(
        "--break-after-n-profiles",
        default=30,
        type=int,
        help="Take a long break after N profiles. Required to avoid detection",
    )
    arg_parser.add_argument(
        "--break-time",
        default=1.5 * 60 * 60,
        type=int,
        help="Length of break in between scraping sessions, in seconds.",
    )
    arg_parser.add_argument(
        "--max-fails-in-a-row",
        default=3,
        type=int,
        help="Retry after exceptions unless there are N failures in a row",
    )
    arg_parser.add_argument(
        "--override",
        default=False,
        action="store_true",
        help="Override all results in the output CSV instead of skipping already scraped profiles",
    )
    arg_parser.add_argument(
        "--chrome-version",
        default=130,
        required=False,
        type=int,
        help="""
            Which version of chrome is currently installed. Update this if you run into: 
            'This version of ChromeDriver only supports Chrome version X'
        """,
    )
    args = arg_parser.parse_args()

    df_in = pandas.read_csv(args.input, index_col=None).sample(frac=1.0)
    assert (
        "profile_url" in df_in
    ), "input csv must contain profile_url column contain linkedin profiles. Of the form https://www.linkedin.com/in/profile_id"

    try:
        df_out = pandas.read_csv(args.output)
    except FileNotFoundError:
        logging.info("No existing output CSV found -- starting a new one.")
        df_out = pandas.DataFrame(
            columns=[
                "profile_url",
                "followers",
                "likes",
                "reposts",
                "comments",
                "post_age",
                "text",
                "is_repost",
                "post_type",
                "post_id",
            ]
        )

    scraper = LinkedinPostScraper(
        email=args.email,
        password=args.password,
        chrome_version=args.chrome_version,
        headless=args.headless,
    )

    completed = 0
    failed_in_a_row = 0
    for i, profile_url in enumerate(df_in.profile_url.unique()):
        if (completed + 1) % args.break_after_n_profiles == 0:
            logging.info("Taking a very long break to avoid detection.")
            logging.info(f"Sleeping for {args.break_time} seconds...")
            scraper.driver.quit()
            time.sleep(args.break_time)

            scraper = LinkedinPostScraper(
                email=args.email,
                password=args.password,
                chrome_version=args.chrome_version,
                headless=args.headless,
            )

        parsed_url = LinkedinPostScraper.extract_linkedin_profile(profile_url)

        if not parsed_url:
            logging.error(f"{profile_url} is malformed, skipping...")
            continue

        if not args.override and df_out.profile_url.str.contains(parsed_url).any():
            logging.info(f"{parsed_url} already scraped, skipping ...")
            continue

        logging.info(parsed_url)

        try:
            post_data = scraper.scrape_profile(parsed_url)
            failed_in_a_row = 0
        except Exception as e:
            failed_in_a_row += 1

            if failed_in_a_row >= args.max_fails_in_a_row:
                logging.error("Failed too many times in a row. Stopping.")
                raise e

            logging.exception(e)
            logging.error(f"Failed {profile_url}, skipping...")
            continue

        logging.info(json.dumps(post_data, indent=4))

        df_out = df_out[df_out.profile_url != profile_url]
        df_out = df_out.append(post_data, ignore_index=True)

        if (i + 1) % args.save_every == 0:
            df_out.to_csv(args.output, index=False)

        completed += 1

        wait_time = random.uniform(15, 20)
        logging.info(f"Pausing for {int(wait_time)} seconds...")
        time.sleep(wait_time)

    df_out.to_csv(args.output, index=False)
    logging.info("Done!")

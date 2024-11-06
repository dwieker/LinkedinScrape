import requests
from argparse import ArgumentParser
import pandas
import logging
from itertools import cycle
import time
import warnings
import concurrent.futures
import threading

warnings.filterwarnings("ignore")
logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)


def search_linkedin_profile(index, first_name: str, last_name: str, affiliation: str):
    # You will need to sign up for the SERP Scraper API
    # https://dashboard.oxylabs.io/en/
    response = requests.post(
        "https://realtime.oxylabs.io/v1/queries",
        auth=("<username>", "<password>"),
        json={
            "source": "google_search",
            "query": f"linkedin {first_name} {last_name} {affiliation}",
            "parse": True,
        },
    )
    for result in response.json()["results"][0]["content"]["results"]["organic"]:
        url = result["url"]
        if "linkedin.com/in/" not in url:
            continue
        else:
            logging.info(f"{first_name} {last_name} - {affiliation} - {url}")
            return index, url

    logging.info(f"{first_name} {last_name} - {affiliation} - NOT FOUND")
    return index, "NOT FOUND"


def main():
    arg_parse = ArgumentParser()
    arg_parse.add_argument("--input", required=True)
    arg_parse.add_argument("--save-every", type=int, default=20)
    arg_parse.add_argument("--threads", type=int, default=5)
    args = arg_parse.parse_args()

    df = pandas.read_csv(args.input, index_col=None)

    if "profile_url" not in df:
        df["profile_url"] = None

    assert "HCP First Name" in df
    assert "HCP Last Name" in df
    assert "Affiliation" in df

    rows_to_process = df[df.profile_url.isnull()].iterrows()

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.threads) as executor:
        futures = []
        for index, row in rows_to_process:
            first_name = row["HCP First Name"]
            last_name = row["HCP Last Name"]
            affiliation = row["Affiliation"]

            future = executor.submit(
                search_linkedin_profile, index, first_name, last_name, affiliation
            )
            futures.append(future)

        for i, future in enumerate(concurrent.futures.as_completed(futures)):
            if future.exception():
                logging.error(future.exception())
                continue

            index, profile_url = future.result()
            df.loc[index, "profile_url"] = profile_url

            if (i + 1) % args.save_every == 0:
                df.to_csv(args.input, index=False)
                logging.info(f"Saved progress after processing {i + 1} profiles")

    df.to_csv(args.input, index=False)


if __name__ == "__main__":
    main()

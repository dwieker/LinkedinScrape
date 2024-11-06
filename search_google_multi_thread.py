import concurrent.futures
import logging
import warnings
from argparse import ArgumentParser

import pandas
import requests

warnings.filterwarnings("ignore")
logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)


def search_linkedin_profile(index, username: str, password: str, query: str):
    response = requests.post(
        "https://realtime.oxylabs.io/v1/queries",
        auth=(username, password),
        json={
            "source": "google_search",
            "query": f"linkedin {query}",
            "parse": True,
        },
        timeout=10,
    )
    for result in response.json()["results"][0]["content"]["results"]["organic"]:
        url = result["url"]

        if "linkedin.com/in/" not in url:
            continue

        logging.info(f"{query}: {url}")
        return index, url

    logging.info(f"{query}: NOT FOUND")
    return index, "NOT FOUND"


def main():
    arg_parse = ArgumentParser()
    arg_parse.add_argument(
        "--input",
        required=True,
        help="CSV file containing a 'name' column and 'extra_info' column which will be used for search.",
    )
    arg_parse.add_argument("--username", required=True, help="oxylabs username")
    arg_parse.add_argument("--password", required=True, help="oxylabs password")
    arg_parse.add_argument("--save-every", type=int, default=20)
    arg_parse.add_argument(
        "--threads",
        type=int,
        default=5,
        help="Number of concurrent searches, limited by the oxylabs subscription plan.",
    )
    args = arg_parse.parse_args()

    df = pandas.read_csv(args.input, index_col=None)

    if "profile_url" not in df:
        df["profile_url"] = None

    assert "name" in df, "Add a name column to the CSV"
    assert (
        "extra_info" in df
    ), "Add an extra_info column to the CSV with any helpful identifying information"

    rows_to_process = df[df.profile_url.isnull()].iterrows()

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.threads) as executor:
        futures = []
        for index, row in rows_to_process:
            future = executor.submit(
                search_linkedin_profile,
                index,
                args.username,
                args.password,
                row["name"] + " " + row["extra_info"],
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

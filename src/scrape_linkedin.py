from selenium import webdriver
import undetected_chromedriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from argparse import ArgumentParser
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse
import pandas
import random
import logging
import time
import re

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)


class LinkedinPostScraper:
    def __init__(
        self, chrome_options: webdriver.ChromeOptions, email: str, password: str
    ):
        self.driver = undetected_chromedriver.Chrome(options=chrome_options)
        self.login(email, password)

    def login(self, email: str, password: str):
        self.driver.get("https://www.linkedin.com/login")

        email_field = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "username"))
        )
        email_field.send_keys(email)

        password_field = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "password"))
        )
        password_field.send_keys(password)

        password_field.submit()

        WebDriverWait(self.driver, 60).until(
            EC.url_matches("https://www.linkedin.com/feed")
        )

    def int_cast(s: str) -> int:
        return int(s.strip().replace(",", ""))

    def scroll_down(self, batches: int):
        scroll_height = 0
        for i in range(batches):
            total_height = int(
                self.driver.execute_script("return document.body.scrollHeight")
            )
            if total_height != scroll_height:
                scroll_height = total_height
                self.driver.execute_script(f"window.scrollTo(0, {total_height});")
                time.sleep(random.uniform(2, 4))
            else:
                logging.info("Reached the end of the feed...")
                return

    def find_posts(soup):
        return soup.find_all("div", class_="feed-shared-update-v2")

    def extract_post_age(post):
        post_age = post.find(
            "a",
            class_=re.compile("update-components-actor__sub-description-link"),
        )
        if post_age:
            return post_age.find_all("span")[-1].text.strip()
        else:
            return ""

    def extract_likes(post) -> int:
        likes = post.find(
            "span",
            class_=re.compile("social-details-social-counts__reactions-count"),
        )
        if likes:
            return LinkedinPostScraper.int_cast(likes.text)
        else:
            return 0

    def extract_reposts(post) -> int:
        reposts = post.find(
            "button",
            class_=re.compile("social-details-social-counts__link"),
        )
        if reposts:
            return LinkedinPostScraper.int_cast(reposts.text.strip().split()[0])
        else:
            return 0

    def extract_comments(post) -> int:
        reposts = post.find(
            "li",
            class_=re.compile("social-details-social-counts__comments"),
        )
        if reposts:
            return LinkedinPostScraper.int_cast(reposts.text.strip().split()[0])
        else:
            return 0

    def extract_text(post) -> str:
        text = post.find("div", class_=re.compile("feed-shared-inline-show-more-text"))
        if text:
            return text.find("span", class_=re.compile("break-words")).text.strip()
        else:
            return ""

    def extract_is_repost(post) -> bool:
        return (
            post.find("div", class_="feed-shared-update-v2__update-content-wrapper")
            is not None
        )

    def extract_post_type(post) -> str:
        if post.find("div", class_="update-components-linkedin-video") is not None:
            return "Video"
        elif post.find("div", class_="update-components-image") is not None:
            return "Image"
        elif (
            post.find("div", class_=re.compile("update-components-article")) is not None
        ):
            return "Article"
        else:
            return "Text"

    def extract_followers(soup) -> int:
        for span in soup.find_all("span"):
            if span.get_text(strip=True).endswith("followers"):
                return LinkedinPostScraper.int_cast(
                    span.get_text(strip=True).split()[0]
                )

        return 0

    def extract_name(soup) -> str:
        return soup.find(
            "h1", class_="text-heading-xlarge inline t-24 v-align-middle break-words"
        ).text.strip()

    def extract_mini_bio(soup) -> str:
        return soup.find("div", class_="text-body-medium break-words").text.strip()

    def scrape_profile(self, url: str):
        self.driver.get(url)
        time.sleep(3)
        soup = BeautifulSoup(self.driver.page_source)

        followers = LinkedinPostScraper.extract_followers(soup)
        name = LinkedinPostScraper.extract_name(soup)
        bio = LinkedinPostScraper.extract_mini_bio(soup)

        time.sleep(random.uniform(3, 6))

        self.driver.get(url + "/recent-activity/all/")
        WebDriverWait(self.driver, 20).until(
            EC.presence_of_element_located((By.CLASS_NAME, "scaffold-layout__main"))
        )
        time.sleep(random.uniform(3, 6))

        self.scroll_down(batches=8)

        soup = BeautifulSoup(self.driver.page_source)
        posts = LinkedinPostScraper.find_posts(soup)

        with open("activity2.html", "w", encoding="utf-8") as f:
            f.write(self.driver.page_source)

        if not posts:
            return [
                {
                    "profile_url": profile_url,
                    "name": name,
                    "bio": bio,
                    "followers": followers,
                }
            ]
        else:
            return [
                {
                    "profile_url": profile_url,
                    "name": name,
                    "bio": bio,
                    "followers": followers,
                    "likes": LinkedinPostScraper.extract_likes(post),
                    "reposts": LinkedinPostScraper.extract_reposts(post),
                    "comments": LinkedinPostScraper.extract_comments(post),
                    "post_age": LinkedinPostScraper.extract_post_age(post),
                    "text": LinkedinPostScraper.extract_text(post),
                    "is_repost": LinkedinPostScraper.extract_is_repost(post),
                    "post_type": LinkedinPostScraper.extract_post_type(post),
                }
                for post in posts
            ]

    @classmethod
    def extract_linkedin_profile(cls, url: str) -> str:
        if "linkedin.com/in/" in url:
            parsed_url = urlparse(url)
            path_components = parsed_url.path.split("/")
            username_index = path_components.index("in") + 1

            if path_components[username_index]:
                return (
                    parsed_url.scheme
                    + "://"
                    + parsed_url.netloc
                    + "/".join(path_components[: username_index + 1])
                )


if __name__ == "__main__":
    arg_parser = ArgumentParser()
    arg_parser.add_argument("--password", required=True)
    arg_parser.add_argument("--email", required=True)
    arg_parser.add_argument("--input", required=True)
    arg_parser.add_argument("--output", required=True)
    arg_parser.add_argument("--save-every", type=int, default=3)
    arg_parser.add_argument("--headless", default=False, action="store_true")
    arg_parser.add_argument("--n-profiles", default=30, type=int)
    args = arg_parser.parse_args()

    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--start-maximized")

    if args.headless:
        logging.info(
            "Headless mode. Note this won't work if there is a bot checkpoint at login"
        )
        chrome_options.add_argument("--headless")

    df_in = pandas.read_csv(args.input, index_col=None).sample(frac=1.0)
    assert "linkedin_url" in df_in, "input csv must contain linkedin_url column"

    try:
        df_out = pandas.read_csv(args.output)
    except FileNotFoundError:
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
            ]
        )

    scraper = LinkedinPostScraper(chrome_options, args.email, args.password)

    completed = 0
    failed_in_a_row = 0
    for i, profile_url in enumerate(df_in.linkedin_url):
        if completed >= args.n_profiles:
            break

        parsed_url = LinkedinPostScraper.extract_linkedin_profile(profile_url)

        if not parsed_url:
            logging.error(f"{profile_url} is malformed, skipping...")
            continue

        if df_out.profile_url.str.contains(parsed_url).any():
            logging.info(f"{parsed_url} already scraped, skipping ...")
            continue

        logging.info(parsed_url)

        try:
            post_data = scraper.scrape_profile(parsed_url)
            failed_in_a_row = 0
        except Exception as e:
            failed_in_a_row += 1
            if failed_in_a_row >= 1:
                logging.error("Failed 3 times in a row. Stopping.")
                raise e
            else:
                logging.error("Failed, skipping...")
                continue

        logging.info(post_data)

        df_out = df_out.append(post_data, ignore_index=True)

        if (i + 1) % args.save_every == 0:
            df_out.to_csv(args.output, index=False)

        completed += 1

        wait_time = random.uniform(15, 20)
        logging.info(f"Pausing for {int(wait_time)} seconds...")
        time.sleep(wait_time)

    df_out.to_csv(args.output, index=False)
    logging.info("Done!")

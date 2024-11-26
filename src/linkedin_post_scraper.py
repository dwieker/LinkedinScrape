import os
import pickle
import random
import logging
import time
import re
from typing import Optional
from urllib.parse import urlparse

from selenium import webdriver
import undetected_chromedriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup

logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S",
)


class LinkedinPostScraper:
    COOKIES_FILE_PATH = "/tmp/linkedin_cookies.pkl"

    def __init__(
        self,
        email: str,
        password: str,
        chrome_version: int,
        headless: bool = False,
    ):
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--log-level=3")
        chrome_options.add_argument("--start-maximized")

        if headless:
            logging.info(
                "Headless mode. Note this won't work if there is a bot checkpoint at login"
            )
            chrome_options.add_argument("--headless")

        self.driver = undetected_chromedriver.Chrome(
            options=chrome_options, version_main=chrome_version
        )
        self.login(email, password)

    def login(self, email: str, password: str):
        self.driver.get("https://www.linkedin.com/login")

        email_field = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "username"))
        )
        password_field = WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.ID, "password"))
        )

        if os.path.exists(self.COOKIES_FILE_PATH):
            try:
                logging.info(
                    f"Cookies found at {self.COOKIES_FILE_PATH} -- adding them to current session."
                )

                self.load_cookies_to_session()

                WebDriverWait(self.driver, 3).until(
                    EC.url_matches("https://www.linkedin.com/feed")
                )
                return
            except Exception as e:
                logging.info("Cookies expired, logging in with email and password.")

        email_field.send_keys(email)
        password_field.send_keys(password)

        password_field.submit()

        WebDriverWait(self.driver, 60).until(
            EC.url_matches("https://www.linkedin.com/feed")
        )

        self.save_cookies()

    def load_cookies_to_session(self):
        for cookie in pickle.load(open(self.COOKIES_FILE_PATH, "rb")):
            self.driver.add_cookie(cookie)

        self.driver.refresh()

    def save_cookies(self):
        cookies = self.driver.get_cookies()
        pickle.dump(cookies, open(self.COOKIES_FILE_PATH, "wb"))

    @staticmethod
    def int_cast(s: str) -> int:
        return int(s.strip().replace(",", ""))

    @staticmethod
    def find_posts(soup):
        return soup.find_all("div", class_="feed-shared-update-v2")

    @staticmethod
    def extract_post_age(post):
        post_age = post.find(
            "a",
            class_=re.compile("update-components-actor__sub-description-link"),
        )
        return post_age.find_all("span")[-1].text.strip()

    @staticmethod
    def extract_likes(post) -> int:
        likes = post.find(
            "span",
            class_=re.compile("social-details-social-counts__reactions-count"),
        )
        if likes:
            return LinkedinPostScraper.int_cast(likes.text)
        else:
            return 0

    @staticmethod
    def extract_reposts(post) -> int:
        for element in post.find_all(
            "button",
            class_=re.compile("social-details-social-counts__link"),
        ):
            if "repost" in element.text:
                return LinkedinPostScraper.int_cast(element.text.strip().split()[0])

        return 0

    @staticmethod
    def extract_comments(post) -> int:
        reposts = post.find(
            "li",
            class_=re.compile("social-details-social-counts__comments"),
        )
        if reposts:
            return LinkedinPostScraper.int_cast(reposts.text.strip().split()[0])
        else:
            return 0

    @staticmethod
    def extract_text(post) -> str:
        text = post.find("div", class_=re.compile("feed-shared-inline-show-more-text"))
        if text:
            return text.find("span", class_=re.compile("break-words")).text.strip()
        else:
            return ""

    @staticmethod
    def extract_is_repost(post) -> bool:
        return (
            post.find("div", class_="feed-shared-update-v2__update-content-wrapper")
            is not None
        )

    @staticmethod
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

    @staticmethod
    def extract_followers(soup) -> int:
        for span in soup.find_all("span"):
            if span.get_text(strip=True).endswith("followers"):
                return LinkedinPostScraper.int_cast(
                    span.get_text(strip=True).split()[0]
                )

        return 0

    @staticmethod
    def extract_name(soup) -> str:
        pattern = re.compile(r"/in/[a-zA-Z0-9\-]+/overlay/about-this-profile/.*")
        return soup.find("a", href=pattern).text.strip()

    @staticmethod
    def extract_mini_bio(soup) -> str:
        return soup.find("div", class_="text-body-medium break-words").text.strip()

    @staticmethod
    def extract_post_id(soup) -> str:
        return soup["data-urn"]

    @staticmethod
    def extract_linkedin_profile(url: str) -> Optional[str]:
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

    @staticmethod
    def extract_post_age_years(post):
        post_age = LinkedinPostScraper.extract_post_age(post)

        if "year" not in post_age:
            return False

        return int(post_age.split()[0])

    def scrape_profile(
        self, url: str, max_post_age_years: int = 5, max_posts: int = 30
    ):
        self.driver.get(url)
        time.sleep(3)
        soup = BeautifulSoup(self.driver.page_source, features="lxml")

        followers = LinkedinPostScraper.extract_followers(soup)
        name = LinkedinPostScraper.extract_name(soup)
        bio = LinkedinPostScraper.extract_mini_bio(soup)

        time.sleep(random.uniform(3, 6))

        self.driver.get(url + "/recent-activity/all/")
        WebDriverWait(self.driver, 20).until(
            EC.presence_of_element_located((By.CLASS_NAME, "feed-shared-update-v2"))
        )
        time.sleep(random.uniform(3, 6))

        scroll_height = 0
        while True:
            total_height = int(
                self.driver.execute_script("return document.body.scrollHeight")
            )

            soup = BeautifulSoup(self.driver.page_source, features="lxml")
            posts = LinkedinPostScraper.find_posts(soup)

            if not posts:
                logging.info("No posts found...")
                return [
                    {
                        "profile_url": url,
                        "name": name,
                        "bio": bio,
                        "followers": followers,
                    }
                ]

            if len(posts) > max_posts:
                logging.info("Max posts reached...")
                break

            if (
                LinkedinPostScraper.extract_post_age_years(posts[-1])
                >= max_post_age_years
            ):
                logging.info("Post ages exceed max-post-age-years...")
                break

            if total_height == scroll_height:
                logging.info("Reached the end of the feed...")
                break

            scroll_height = total_height
            self.driver.execute_script(f"window.scrollTo(0, {total_height});")
            time.sleep(random.uniform(5, 6))

        return [
            {
                "profile_url": url,
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
                "post_id": LinkedinPostScraper.extract_post_id(post),
            }
            for post in posts[:max_posts]
            if self.extract_post_age_years(post) <= max_post_age_years
        ]

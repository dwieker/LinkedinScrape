from selenium import webdriver
import undetected_chromedriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse
import pandas
import random
import logging
import time
from typing import Optional
import re
import os
import pickle

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
        chrome_options: webdriver.ChromeOptions,
        chrome_version: int,
    ):
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
            except:
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
                time.sleep(random.uniform(5, 6))
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
        return post_age.find_all("span")[-1].text.strip()

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
        for element in post.find_all(
            "button",
            class_=re.compile("social-details-social-counts__link"),
        ):
            if "repost" in element.text:
                return LinkedinPostScraper.int_cast(element.text.strip().split()[0])

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
        pattern = re.compile(r"/in/[a-zA-Z0-9\-]+/overlay/about-this-profile/.*")
        return soup.find("a", href=pattern).text.strip()

    def extract_mini_bio(soup) -> str:
        return soup.find("div", class_="text-body-medium break-words").text.strip()

    def extract_post_id(soup) -> str:
        return soup["data-urn"]

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

        self.scroll_down(batches=10)

        soup = BeautifulSoup(self.driver.page_source)
        posts = LinkedinPostScraper.find_posts(soup)

        if not posts:
            return [
                {
                    "profile_url": url,
                    "name": name,
                    "bio": bio,
                    "followers": followers,
                }
            ]

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
            for post in posts
        ]

    @classmethod
    def extract_linkedin_profile(cls, url: str) -> Optional[str]:
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

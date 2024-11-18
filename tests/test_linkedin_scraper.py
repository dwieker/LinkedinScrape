from pathlib import Path

import pytest
from bs4 import BeautifulSoup

from src.linkedin_post_scraper import LinkedinPostScraper


@pytest.fixture
def activity_soup():
    with open(Path(__file__).parent / "activity.html", encoding="utf-8") as f:
        return BeautifulSoup(f.read(), "html.parser")


@pytest.fixture
def profile_soup():
    with open(Path(__file__).parent / "profile.html", encoding="utf-8") as f:
        return BeautifulSoup(f.read(), "html.parser")


@pytest.fixture
def posts(activity_soup):
    return LinkedinPostScraper.find_posts(activity_soup)


@pytest.mark.parametrize(
    "url, expected_result",
    [
        (
            "https://www.linkedin.com/in/johndoe/some-other-stuff",
            "https://www.linkedin.com/in/johndoe",
        ),
        (
            "https://www.linkedin.com/in/janedoe1234/?utm_source=linkedin",
            "https://www.linkedin.com/in/janedoe1234",
        ),
        ("https://www.linkedin.com/company/linkedin/", None),  # Incorrect format
        ("https://example.com/in/johndoe", None),  # Not LinkedIn URL
        ("https://www.linkedin.com/johndoe", None),  # Missing '/in/'
        ("https://www.linkedin.com/in/", None),  # Missing username
    ],
)
def test_extract_linkedin_profile(url, expected_result):
    assert LinkedinPostScraper.extract_linkedin_profile(url) == expected_result


def test_extract_post_age(posts):
    assert LinkedinPostScraper.extract_post_age(posts[0]) == "7 months ago"


def test_extract_post_id(posts):
    assert len(posts) == 3
    _id = LinkedinPostScraper.extract_post_id(posts[0])
    assert _id == "urn:li:activity:7183990472795672576"


def test_extract_reposts(posts):
    assert LinkedinPostScraper.extract_reposts(posts[0]) == 5


def test_extract_comments(posts):
    assert LinkedinPostScraper.extract_comments(posts[0]) == 28


def test_extract_name(profile_soup):
    assert LinkedinPostScraper.extract_name(profile_soup) == "Veronica Ramos"


@pytest.mark.parametrize(
    "url, expected_result",
    [(3, "4 years", True), (2, "4 years", False), (1, "3 months", False)],
)
def test_max_lookback_years(years, post_age_string, expected):
    assert (
        LinkedinPostScraper.is_post_before_lookback_period(years, post_age_string)
        == expected
    )

import pytest
from src.scrape_linkedin import LinkedinPostScraper
from bs4 import BeautifulSoup

with open("activity2.html", encoding="utf-8") as f:
    soup = BeautifulSoup(f.read())


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


def test_extract_post_age():
    posts = LinkedinPostScraper.find_posts(soup)
    assert LinkedinPostScraper.extract_post_age(posts[0]) == "1 month ago"

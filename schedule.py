import subprocess
import time
from datetime import datetime


def run_subprocess():
    try:
        result = subprocess.run(
            [
                "python3",
                "src/scrape_linkedin.py",
                "--email",
                "devin.wieker@gmail.com",
                "--password",
                "4MQ7g!fe99zv",
                "--input",
                "hcp.csv",
                "--output",
                "linkedin_scraped.csv",
            ],
            text=True,
            check=True,
        )
        print(f"Subprocess output: {result.stdout}")
    except subprocess.CalledProcessError as e:
        print(f"Subprocess error: {e.stderr}")


def main():
    interval = 2 * 60 * 60  # 2 hours in seconds

    while True:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"Running subprocess at {current_time}")

        run_subprocess()

        print(f"Sleeping for {interval} seconds...")
        time.sleep(interval)


if __name__ == "__main__":
    main()

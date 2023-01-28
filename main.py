import subprocess
import time
from selenium.common.exceptions import NoSuchElementException
import os
import argparse
from slugify import slugify
import tqdm

import scrape_utils
import ffmpeg_utils


def main():

    args = argparse.ArgumentParser()
    args.add_argument(
        "--url",
        type=str,
        help="Panopto url to download. Can be a single video or a list of videos.",
    )
    args.add_argument(
        "--debug",
        default=False,
        action="store_true",
        help="Whether or not the driver should be headless.",
    )
    args.add_argument(
        "--create-folder",
        type=int,
        default=1,
        choices=[0, 1],
        help="create-folder = True if you want to create a subfolder in the export folder.",
    )
    args.add_argument(
        "--no-video", default=False, action="store_true", help="Skip video download."
    )
    args.add_argument(
        "--skip-existing",
        default=False,
        action="store_true",
        help="Skip video if folder already exists.",
    )
    args.add_argument(
        "--download-type",
        default="mp4",
        choices=["mp4", "mp3"],
        help="The file type to download the video as.",
    )

    args = args.parse_args()

    url = args.url.strip()
    if not scrape_utils.verify_url(url):
        print("Invalid url - please check the url and try again!")
        return

    # Start the driver.
    driver = scrape_utils.start_driver(headless=not args.debug)

    # Login to Panopto. Driver is returned as None if login fails.
    driver = scrape_utils.login_to_panopto(driver)
    if driver is None:
        print("Login failed.")
        return

    if "List.aspx" in url:
        IDs = scrape_utils.extract_urls_from_list(driver, url)
        urls = [
            f"https://panopto.dtu.dk/Panopto/Pages/Viewer.aspx?id={ID}" for ID in IDs
        ]
    else:
        urls = [url]

    # --- Start the for loop here ---
    for i, url in tqdm.tqdm(enumerate(urls), desc="Scraping videos", total=len(urls)):
        # Extract the Panopto ID from the url.
        panopto_id = scrape_utils.extract_panopto_id(url)

        if args.skip_existing:
            dst = os.path.join("./export/", panopto_id)
            if os.path.isdir(dst):
                if len(os.listdir(dst)) > 0:
                    # Skip the folder because it's populated.
                    continue

        # Delete driver requests.
        del driver.requests
        driver.get(url)

        # Load next page, give it some time to load.
        time.sleep(2)

        if args.create_folder:
            dst = os.path.join("./export/", panopto_id)
            if not os.path.isdir(dst):
                os.mkdir(dst)
        else:
            dst = "./export/"

        info = scrape_utils.scrape_metadata(driver)

        # Change the title to a slugified version.
        title = slugify(info["title"])

        scrape_utils.scrape_subtitles(driver, out_dir=dst, title=title)

        # Scrape the m3u8 file/files in case there are multiple videos on the page.
        m3u8_paths = scrape_utils.scrape_m3u8(driver, out_dir=dst, title=title)

        # Download the video to whichever format is specified.
        for m3u8_path in m3u8_paths:
            ffmpeg_utils.download(
                m3u8_path=m3u8_path, out_format=f".{args.download_type}"
            )

        # Extract the video duration from the m3u8 file.
        info["video_duration"] = scrape_utils.extract_video_duration(m3u8_paths[0])

        # Save the info.json file.
        scrape_utils.save_info(info, out_dir=dst, title=title)

    # Quit the driver.
    driver.quit()


if __name__ == "__main__":
    main()

from getpass import getpass

from seleniumwire import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException

import logging
from retry import retry
import tqdm

import time
import os
import json

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def start_driver(headless: bool = True) -> webdriver.Chrome:
    """
    Starts the chrome driver.

    Args:
        headless: whether or not the driver should be headless.
    Returns:
        webdriver.Chrome: chrome driver
    """

    options = webdriver.ChromeOptions()
    if headless:
        options.add_argument("--headless")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )

    driver.maximize_window()

    return driver


@retry(tries=3, delay=2, logger=logger)
def login_to_panopto(driver: webdriver.Chrome) -> webdriver.Chrome:
    """
    Logs into https://panopto.dtu.dk using the credentials provided by the user.

    Args:
        driver: chrome driver
    Returns:
        driver: chrome driver
    """

    # Go to Panopto
    driver.get("https://panopto.dtu.dk/Panopto/Pages/Sessions/List.aspx#")

    logged_in = False
    while not logged_in:

        # Prompt the user for credentials.
        username = input("Please enter studynumber: ").strip().lower()
        password = getpass("Please enter password: ").strip()

        driver.find_element(by="xpath", value='//*[@id="loginButton"]').click()
        time.sleep(0.5)
        driver.find_element(
            by="xpath", value='//*[@id="loginControl_externalLoginButton"]'
        ).click()
        time.sleep(2)

        # Set the wait.
        wait = WebDriverWait(driver, 5)

        try:
            elem_username = wait.until(
                EC.visibility_of_element_located((By.XPATH, '//*[@id="userNameInput"]'))
            )
            elem_password = wait.until(
                EC.visibility_of_element_located((By.XPATH, '//*[@id="passwordInput"]'))
            )
        except:
            raise NoSuchElementException(msg="Error finding login fields...")

        elem_username.clear()
        elem_username.send_keys(username)

        elem_password.clear()
        elem_password.send_keys(password)
        elem_password.send_keys(Keys.RETURN)

        time.sleep(0.5)
        try:
            elem = driver.find_element(by="xpath", value='//*[@id="error"]')
            print("Wrong username or password. Please try again.")
            driver.refresh()
        except:
            del username
            del password
            logged_in = True

    return driver


@retry(tries=3, delay=5, logger=logger)
def extract_urls_from_list(driver: webdriver.Chrome, url: str) -> list[str]:
    """
    Extract a list of urls from list.

    Args:
        driver: chrome driver
        url: url to the list of videos.
    Returns:
        IDs: list containing all of the Panopto IDs.
    """

    # Go to the url.
    driver.get(url)

    # Make sure the page is loaded entirely.
    time.sleep(5)

    # Get the current url and extract all the arguments.
    base_url, args = url.split("#")
    args = args.split("&")

    def keep_argument(arg):
        if "isSubscriptionsPage" in arg:
            return True
        elif "folderID" in arg:
            return True

        return False

    # Remove the non-important arguments.
    args = [x for x in args if keep_argument(x)]

    # Add the 'maxResults=250' argument and the 'view=0' and start at 'page=0'.
    args += ["maxResults=250", "view=0"]

    # Find the total number of videos in the list (can be found in the bottom right of the webpage.)
    number_of_videos = driver.find_element(
        by="xpath", value='//*[@id="pageRange"]'
    ).text.replace("of", "af")

    # Calculate the number of pages.
    number_of_videos = int(number_of_videos.split("af")[-1].strip())
    number_of_pages = int(number_of_videos / 250) + 1

    # Loop through the video pages and grab the table.
    IDs = []
    for k in tqdm.tqdm(
        range(number_of_pages), desc="Extracting urls from list", total=number_of_pages
    ):
        url = base_url + "#" + "&".join(args) + f"&page={k}"
        driver.get(url)
        time.sleep(5)

        html = driver.find_element(
            by="xpath", value='//*[@id="listTable"]/tbody'
        ).get_attribute("outerHTML")
        IDs += [
            x.strip().split(" ")[1].replace("id=", "").replace('"', "")
            for x in html.splitlines()
            if ("tr id=" in x and "rowPlaceholder" not in x)
        ]

    # If the number of videos do not match the number of videos in the list, raise an error.
    assert (
        len(IDs) == number_of_videos
    ), "The number of videos does not match the number of videos in the list."

    return IDs


def extract_panopto_id(url: str) -> str:
    """
    Extract the Panopto ID from the url.

    Args:
        url: Panopto url.
    Returns:
        panopto_id: Panopto ID.
    """

    # Extract the Panopto ID.
    arguments = url.split("?")[1].split("&")
    for arg in arguments:
        if arg.startswith("id="):
            panopto_id = arg.split("=")[1]
            return panopto_id

    return


def scrape_m3u8(driver: webdriver.Chrome, out_dir: str, title: str) -> list[str]:
    """
    Scrape the current driver.requests for m3u8 files and download them.

    Args:
        out_dir: the folder that the m3u8 files should be saved to.
        title: the title of the video.
    Returns:
        m3u8_paths: list containing the paths to the m3u8 files.
    """

    m3u8_paths = []
    n_found = 0

    for request in driver.requests:
        if request.url.endswith("/index.m3u8") and "subtitles" not in request.url:
            n_found += 1

            s = request.response.body.decode("utf-8")

            s = s.splitlines()

            prefix = request.url.replace("index.m3u8", "")
            s = [prefix + x if x.endswith(".ts") else x for x in s]

            # Write to index.m3u8
            m3u8_path = os.path.join(out_dir, f"{title}_{n_found:02d}.m3u8")
            with open(m3u8_path, "w") as f:
                f.write("\n".join(s))

            m3u8_paths.append(m3u8_path)

    # Generate titles for the videos.
    if len(m3u8_paths) == 0:
        raise Exception("No m3u8 files found. Something went wrong.")
    elif len(m3u8_paths) == 1:
        os.rename(m3u8_paths[0], os.path.join(out_dir, f"{title}.m3u8"))
        m3u8_paths = [os.path.join(out_dir, f"{title}.m3u8")]
    else:
        pass

    return m3u8_paths


def verify_url(url: str) -> bool:
    """
    Verifies that the url is a valid Panopto url.

    Args:
        url: the url to verify.
    Returns:
        bool: True if the url is valid, False otherwise.
    """

    if "panopto.dtu.dk" in url and (("Viewer.aspx?id=" in url) or ("List.aspx" in url)):
        return True

    return False


@retry(tries=3, delay=5, logger=logger)
def scrape_metadata(driver: webdriver.Chrome) -> dict:
    """
    Scrape the metadata from the video.
    - url, the url to the video.
    - parentName, the name of the parent folder.
    - parentURL, the url of the parent folder.
    - title, the title of the video.
    - detailsTab, the details from the Oplysninger-tab.

    Args:
        driver, the selenium driver.
    Returns:
        dict: containing the scraped information about the video.
    """

    try:
        # Get the current url.
        url = driver.current_url

        # Parent Name.
        parentName = driver.find_element(
            by="xpath", value='//*[@id="parentName"]'
        ).get_property("innerHTML")

        # Click the details tab.
        elem = driver.find_element(by="xpath", value='//*[@id="detailsTabHeader"]')
        elem.click()
        time.sleep(1)

        # Extract the title
        title = driver.find_element(
            by="xpath", value='//*[@id="detailsTab"]/div[1]'
        ).text

        # And all of the details.
        detailsTab = driver.find_element(by="xpath", value='//*[@id="detailsTab"]').text

        # Get the href to the parent folder.
        parentURL = driver.find_element(
            by="xpath", value='//*[@id="parentContext"]'
        ).get_property("innerHTML")

        # Get the new window, get the url and close it again.
        elem = driver.find_element(by="xpath", value='//*[@id="parentClickTarget"]')
        elem.click()
        driver.switch_to.window(driver.window_handles[1])
        parentURL = driver.current_url
        driver.close()
        driver.switch_to.window(driver.window_handles[0])

        info = {
            "url": url,
            "parentName": parentName,
            "parentURL": parentURL,
            "title": title,
            "detailsTab": detailsTab,
        }

    except:
        driver.refresh()
        raise Exception("Error extracting info - trying again!")

    return info


def scrape_subtitles(driver: webdriver.Chrome, out_dir: str, title: str) -> None:
    """
    Scrape the subtitles from the page.

    Args:
        driver, the selenium driver.
        out_dir, the output directory.
        title, the title of the video.
    Returns:
        None
    """
    try:
        subtitles = driver.find_element(
            by="xpath", value='//*[@id="transcriptTabPane"]/div[3]/div[2]'
        ).get_attribute("innerHTML")
    except:
        # If the subtitles cannot be found, then we don't retry.
        subtitles = None

    if subtitles is not None:
        soup = BeautifulSoup(subtitles, features="lxml")
        subtitles = [
            (x.find_all("div", attrs={"class": "event-time"})[0].text, x.span.text)
            for x in soup.find_all("div", attrs={"class": "index-event-row"})
        ]

        subtitles = ["\n".join(x) for x in subtitles]
        subtitles = "\n\n".join(subtitles)
    else:
        subtitles = ""

    outpath = os.path.join(out_dir, f"{title}.txt")

    # Write the subtitles to a .txt file.
    with open(outpath, "w") as f:
        f.write(subtitles)

    return


def extract_video_duration(m3u8_path: str) -> float:
    """
    Extract the video duration from the m3u8 files.

    Args:
        m3u8_path, the path to the m3u8 file.
    Returns:
        duration, the duration of the video in seconds.
    """

    # Add the duration parts of the m3u8 file together.
    with open(m3u8_path) as f:
        m3u8 = f.read().splitlines()

    return sum(
        [
            float(x.split(":")[-1].replace(",", "").strip())
            for x in m3u8
            if x.startswith("#EXTINF")
        ]
    )


def save_info(info: dict, out_dir: str, title: str) -> None:
    """
    Save the info to a json file as out_dir/title.json.

    Args:
        info, dictionary containing the information to save.
    Outpath:
        outpath, the path to save the json file to.
    """

    outpath = os.path.join(out_dir, f"{title}.json")

    with open(outpath, "w", encoding="utf8") as f:
        json.dump(info, f, indent=4, ensure_ascii=False)

    return

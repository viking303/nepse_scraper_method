"""
NEPSE Floorsheet Historical Data Scraper
==========================================
Scrapes historical floorsheet data from merolagani.com
for Nepal Stock Exchange (NEPSE).

Usage:
    python3 scraper.py

Data is saved as YYYY_MM_DD_floorsheet.csv in NEPSE_data folder.
Script is resume-friendly - skips already downloaded dates.

Author: Your Name
GitHub: your-github-url
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from io import StringIO
import pandas as pd
import time
import datetime
import os
import re

# ── Config ────────────────────────────────────────────────────────────────────
DRIVE_FOLDER = "/home/ubuntu/nepse/NEPSE_data"  # change this to your path
START_DATE   = datetime.date(2014, 5, 5)         # change start date
END_DATE     = datetime.date.today() - datetime.timedelta(days=1)  # yesterday
PAGE_DELAY   = 1.0   # seconds between page clicks
DATE_DELAY   = 1.5   # seconds between dates
MAX_RETRIES  = 3     # retries per page
# ─────────────────────────────────────────────────────────────────────────────


def create_driver():
    """Create headless Chrome browser instance."""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-popup-blocking")
    options.add_experimental_option("prefs", {
        "profile.default_content_setting_values.notifications": 2
    })
    service = Service("/usr/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def dismiss_alert(driver):
    """Dismiss any browser alerts/popups."""
    try:
        driver.switch_to.alert.dismiss()
    except:
        pass


def get_records_info(driver):
    """Extract total pages and records from page text."""
    try:
        text = driver.find_element(
            By.XPATH,
            "//*[contains(text(), 'Total pages:')]"
        ).text
        pages   = re.search(r"Total pages:\s*(\d+)", text)
        records = re.search(r"of\s+([\d,]+)\s+records", text)
        total_pages   = int(pages.group(1)) if pages else 1
        total_records = int(records.group(1).replace(",", "")) if records else 0
        return total_pages, total_records
    except:
        return 1, 0


def already_downloaded(date_str):
    """Check if CSV for this date already exists."""
    filename = date_str.replace("-", "_") + "_floorsheet.csv"
    return os.path.exists(os.path.join(DRIVE_FOLDER, filename))


def search_date(driver, date_str):
    """
    Navigate to floorsheet page and search for specific date.
    
    Important: Page must be visited 3 times during warmup before
    date filter works correctly. First request always returns
    latest data regardless of date set.
    """
    driver.get("https://merolagani.com/Floorsheet.aspx")
    time.sleep(3)
    dismiss_alert(driver)

    # Convert YYYY-MM-DD to MM/DD/YYYY format required by site
    d = datetime.date.fromisoformat(date_str)
    formatted = d.strftime("%m/%d/%Y")

    # Find and fill date field
    date_field = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((
            By.NAME,
            "ctl00$ContentPlaceHolder1$txtFloorsheetDateFilter"
        ))
    )
    date_field.clear()
    date_field.send_keys(formatted)
    time.sleep(0.5)
    dismiss_alert(driver)

    # Click search button
    driver.find_element(
        By.ID,
        "ctl00_ContentPlaceHolder1_lbtnSearchFloorsheet"
    ).click()
    time.sleep(4)  # Wait for page to reload with filtered data
    dismiss_alert(driver)


def get_page_data(driver, date_str):
    """Extract table data from current page."""
    try:
        tables = pd.read_html(StringIO(driver.page_source))
        if tables:
            df = tables[0]
            df["Date"] = date_str
            return df
    except:
        pass
    return None


def go_to_page(driver, page_num):
    """Click on specific page number in pagination."""
    try:
        page_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((
                By.XPATH,
                f"//a[contains(@href,'javascript') and normalize-space()='{page_num}']"
            ))
        )
        page_link.click()
        time.sleep(PAGE_DELAY)
        dismiss_alert(driver)
        return True
    except Exception as e:
        print(f"    ⚠️ Page {page_num} error: {e}")
        return False


def scrape_date(driver, date_str):
    """
    Scrape all pages of floorsheet data for a specific date.
    Returns True if data found and saved, False if market closed.
    """
    try:
        # Search for date
        search_date(driver, date_str)

        # Check if market was open
        total_pages, total_records = get_records_info(driver)
        if total_records == 0:
            return False

        print(f"  📄 {total_pages} pages, ~{total_records:,} records")

        all_data = []

        # Get page 1 data
        df = get_page_data(driver, date_str)
        if df is not None:
            all_data.append(df)

        # Get remaining pages
        for page in range(2, total_pages + 1):
            if go_to_page(driver, page):
                df = get_page_data(driver, date_str)
                if df is not None:
                    all_data.append(df)
                    print(f"  ✅ Page {page:>4} / {total_pages}")
                else:
                    print(f"  🚩 Page {page} no data")
            else:
                print(f"  🚩 Page {page} failed")

        if not all_data:

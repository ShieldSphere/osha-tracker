"""
Automated OSHA CSV Download using Selenium

This script uses Selenium to automatically download the OSHA inspection
and violation CSV files from the DOL enforcement data website.

Requirements:
    pip install selenium webdriver-manager

Usage:
    python download_osha_csvs.py

The script will:
1. Open Chrome browser
2. Navigate to OSHA data catalog
3. Download inspection CSV
4. Download violation CSV
5. Move files to the data/ folder
"""
import os
import sys
import time
import shutil
import logging
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_dependencies():
    """Check if required packages are installed."""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        return True
    except ImportError:
        return False


def install_dependencies():
    """Install required packages."""
    import subprocess
    logger.info("Installing required packages...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "selenium", "webdriver-manager", "-q"])
    logger.info("Packages installed successfully")


def download_osha_csvs(download_dir: str = None, headless: bool = False) -> dict:
    """
    Download OSHA inspection and violation CSVs using Selenium.

    Args:
        download_dir: Directory to save downloaded files (default: data/)
        headless: Run browser in headless mode (no visible window)

    Returns:
        Dict with paths to downloaded files
    """
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager

    # Setup download directory
    if download_dir is None:
        download_dir = str(Path(__file__).parent / "data")

    Path(download_dir).mkdir(exist_ok=True)

    # Chrome options
    options = Options()
    if headless:
        options.add_argument("--headless=new")

    # Set download preferences
    prefs = {
        "download.default_directory": download_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
    }
    options.add_experimental_option("prefs", prefs)
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    results = {
        "inspection_csv": None,
        "violation_csv": None,
        "errors": []
    }

    driver = None
    try:
        logger.info("Starting Chrome browser...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.implicitly_wait(10)

        # Navigate to OSHA data catalog
        url = "https://enforcedata.dol.gov/views/data_catalogs.php"
        logger.info(f"Navigating to {url}")
        driver.get(url)
        time.sleep(3)

        # Click on OSHA in the left menu
        logger.info("Looking for OSHA menu item...")
        try:
            # Try different selectors for OSHA link
            osha_link = None
            selectors = [
                "//a[contains(text(), 'OSHA')]",
                "//td[contains(text(), 'OSHA')]",
                "//*[contains(@onclick, 'OSHA')]",
                "//a[@href='#osha']"
            ]
            for selector in selectors:
                try:
                    elements = driver.find_elements(By.XPATH, selector)
                    if elements:
                        osha_link = elements[0]
                        break
                except:
                    continue

            if osha_link:
                osha_link.click()
                time.sleep(2)
                logger.info("Clicked OSHA menu")
            else:
                logger.warning("Could not find OSHA menu link")
        except Exception as e:
            logger.warning(f"Error clicking OSHA menu: {e}")

        # Download Inspection CSV
        logger.info("Looking for Inspection download link...")
        try:
            # Find and click the inspection download
            inspection_links = driver.find_elements(
                By.XPATH,
                "//a[contains(@href, 'inspection') and contains(@href, 'csv')]"
            )
            if not inspection_links:
                # Try form submission approach
                inspection_links = driver.find_elements(
                    By.XPATH,
                    "//*[contains(text(), 'Inspection') and contains(text(), 'CSV')]"
                )
            if not inspection_links:
                # Look for any download link with inspection
                inspection_links = driver.find_elements(
                    By.XPATH,
                    "//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'inspection')]"
                )

            if inspection_links:
                logger.info(f"Found {len(inspection_links)} inspection link(s)")
                inspection_links[0].click()
                time.sleep(5)  # Wait for download to start
                logger.info("Clicked inspection download")
            else:
                # Try direct URL
                logger.info("Trying direct inspection download URL...")
                driver.get("https://enforcedata.dol.gov/views/data_summary.php?agency=osha&form=osha_inspection&type=csv")
                time.sleep(5)
        except Exception as e:
            logger.error(f"Error downloading inspection CSV: {e}")
            results["errors"].append(f"Inspection download error: {e}")

        # Wait for download to complete
        logger.info("Waiting for inspection download to complete...")
        wait_for_download(download_dir, "inspection", timeout=120)

        # Go back and download Violation CSV
        driver.get(url)
        time.sleep(3)

        # Click OSHA again
        try:
            osha_link = driver.find_element(By.XPATH, "//a[contains(text(), 'OSHA')]")
            osha_link.click()
            time.sleep(2)
        except:
            pass

        logger.info("Looking for Violation download link...")
        try:
            violation_links = driver.find_elements(
                By.XPATH,
                "//a[contains(@href, 'violation') and contains(@href, 'csv')]"
            )
            if not violation_links:
                violation_links = driver.find_elements(
                    By.XPATH,
                    "//a[contains(translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'violation')]"
                )

            if violation_links:
                logger.info(f"Found {len(violation_links)} violation link(s)")
                violation_links[0].click()
                time.sleep(5)
                logger.info("Clicked violation download")
            else:
                logger.info("Trying direct violation download URL...")
                driver.get("https://enforcedata.dol.gov/views/data_summary.php?agency=osha&form=osha_violation&type=csv")
                time.sleep(5)
        except Exception as e:
            logger.error(f"Error downloading violation CSV: {e}")
            results["errors"].append(f"Violation download error: {e}")

        # Wait for download to complete
        logger.info("Waiting for violation download to complete...")
        wait_for_download(download_dir, "violation", timeout=120)

        # Find downloaded files
        results["inspection_csv"] = find_downloaded_file(download_dir, "inspection")
        results["violation_csv"] = find_downloaded_file(download_dir, "violation")

        logger.info(f"Inspection CSV: {results['inspection_csv']}")
        logger.info(f"Violation CSV: {results['violation_csv']}")

    except Exception as e:
        logger.error(f"Selenium error: {e}")
        results["errors"].append(str(e))
    finally:
        if driver:
            driver.quit()
            logger.info("Browser closed")

    return results


def wait_for_download(download_dir: str, file_type: str, timeout: int = 120):
    """Wait for a download to complete."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        # Check for partial downloads
        partial_files = list(Path(download_dir).glob("*.crdownload")) + \
                       list(Path(download_dir).glob("*.tmp"))
        if not partial_files:
            # Check if file exists
            if find_downloaded_file(download_dir, file_type):
                return True
        time.sleep(2)
    return False


def find_downloaded_file(download_dir: str, file_type: str) -> str:
    """Find the most recently downloaded file matching the type."""
    patterns = [
        f"*{file_type}*.csv",
        f"*{file_type}*.zip",
        f"osha_{file_type}*.csv",
    ]

    latest_file = None
    latest_time = 0

    for pattern in patterns:
        for f in Path(download_dir).glob(pattern):
            if f.stat().st_mtime > latest_time:
                latest_time = f.stat().st_mtime
                latest_file = str(f)

    return latest_file


def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("OSHA CSV Automated Download")
    logger.info(f"Time: {datetime.now()}")
    logger.info("=" * 60)

    # Check and install dependencies
    if not check_dependencies():
        logger.info("Installing Selenium and WebDriver Manager...")
        install_dependencies()

    # Download CSVs
    results = download_osha_csvs(headless=False)  # Set to True for background operation

    if results["inspection_csv"] and results["violation_csv"]:
        logger.info("=" * 60)
        logger.info("Download complete!")
        logger.info(f"Inspection: {results['inspection_csv']}")
        logger.info(f"Violation: {results['violation_csv']}")
        logger.info("")
        logger.info("Now run: python daily_sync.py")
        logger.info("=" * 60)
        return 0
    else:
        logger.error("=" * 60)
        logger.error("Download failed or incomplete")
        if results["errors"]:
            for err in results["errors"]:
                logger.error(f"  - {err}")
        logger.error("")
        logger.error("Please download manually from:")
        logger.error("  https://enforcedata.dol.gov/views/data_catalogs.php")
        logger.error("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())

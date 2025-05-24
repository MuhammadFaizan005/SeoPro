import sys
import time
import os
import random
import json
import pytest
import logging
from datetime import datetime
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from HelperFunctions.CustomdriverSeleniumbase import CustomSeleniumBaseDriver

# Configure logging
logger = logging.getLogger(__name__)

def pytest_addoption(parser):
    """Register the command-line arguments."""
    parser.addoption(
        "--query",
        action="store",
        default='{"web_match":["trendyol"],"Follow_up_links":[],"headless":false,"uc":true,"eager":false}',
        help="Query configuration as JSON string"
    )
    parser.addoption(
        "--log-file",
        action="store",
        help="Path to the log file"
    )

def get_num_workers():
    """Get the number of workers from pytest-xdist."""
    try:
        import xdist
        worker_count = int(os.environ.get('PYTEST_XDIST_WORKER_COUNT', '1'))
        logger.info(f"Number of workers detected: {worker_count}")
        return worker_count
    except ImportError:
        logger.warning("xdist not found, running in single process mode")
        return 1

def pytest_generate_tests(metafunc):
    """Generate test cases based on the query parameter and number of threads."""
    if "query_config" in metafunc.fixturenames:
        # Parse the query configuration from command line
        query_json = metafunc.config.getoption("--query")
        try:
            query_config = json.loads(query_json)
            logger.info(f"Successfully parsed query configuration: {query_config}")
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing query JSON: {e}")
            return

        # Get the number of workers
        num_workers = get_num_workers()
        
        # Generate test cases based on web_match queries
        web_matches = query_config.get("web_match", [])
        if not web_matches:
            logger.warning("No web_match queries found in configuration")
            return

        # Create test cases for each web match query
        test_cases = []
        
        # If we have fewer web_matches than workers, we'll repeat them
        while len(test_cases) < num_workers:
            for web_match in web_matches:
                if len(test_cases) >= num_workers:
                    break
                test_case = {
                    "web_match": web_match,
                    "follow_up_links": query_config.get("Follow_up_links", []),
                    "headless": query_config.get("headless", False),
                    "uc": query_config.get("uc", True),
                    "eager": query_config.get("eager", False)
                }
                test_cases.append(test_case)

        logger.info(f"Generated {len(test_cases)} test cases")
        metafunc.parametrize("query_config", test_cases)

def scroll_to_element(driver, element):
    driver.execute_script("arguments[0].scrollIntoView({ behavior: 'smooth', block: 'center' });", element)

def test_google_search(query_config):
    """Run the test for each query configuration."""
    logger.info(f"\nStarting test with web_match: {query_config['web_match']}")
    logger.info(f"Follow-up links to process: {len(query_config['follow_up_links'])}")
    logger.info(f"Current views: {query_config.get('current_views', 0)}/{query_config.get('views', 50)}")
    
    # Initialize driver with configuration
    driver_instance = CustomSeleniumBaseDriver(
        uc=query_config["uc"],
        headless=query_config["headless"],
        eager_load=query_config["eager"]
    )
    driver = driver_instance.driver
    
    # Store visited pages
    visited_pages = []

    try:
        # First perform Google search
        driver.get("https://www.google.com/")
        logger.info("Navigated to Google")
        
        # Simulate human-like typing
        search_box = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.NAME, "q"))
        )
        search_box.click()
        time.sleep(1)
        search_box.clear()
        
        # Type the web match query
        for char in query_config["web_match"]:
            search_box.send_keys(char)
            time.sleep(random.uniform(0.1, 0.3))
        search_box.send_keys(Keys.RETURN)
        logger.info(f"Submitted search query: {query_config['web_match']}")
        
        # Wait for search results
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "search"))
        )
        
        try:
            # Wait for the search results to load
            time.sleep(2)
            logger.info("Looking for pagination table...")
            try:
                # Try the new pagination structure first
                pages_table = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "AaVjTc"))
                )
                logger.info("Found new pagination table structure")
            except:
                # Fallback to old structure
                logger.info("Trying old pagination structure...")
                pages_table = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "TeSSVd"))
                )
                logger.info("Found old pagination table structure")

            # Find all pagination elements
            pages = pages_table.find_elements(By.TAG_NAME, "td")
            logger.info(f"Found {len(pages)} pagination elements")
            
            len_results = None
            # Look for the "Next" button in the last cell
            for page in pages:
                try:
                    if page.get_attribute("aria-level"):
                        len_results = page.get_attribute("aria-level")
                        logger.info(f"Found pagination with {len_results} pages")
                        break
                except:
                    continue

            if not len_results:
                logger.info("No pagination found or no page count attribute present")
            

            def get_headings(driver):
                logger.info("Fetching search result headings...")
                # Find all search result elements
                headings = WebDriverWait(driver, 5).until(
                    EC.presence_of_all_elements_located((By.CLASS_NAME, "yuRUbf"))
                )
                logger.info(f"Found {len(headings)} search result headings")
                return headings
            
            logger.info(f"\nSearch results for query: {query_config['web_match']}")
            logger.info("-" * 50)
            
            def match_links(driver, result_headings, query_config):
                logger.info(f"Starting link matching process for {len(result_headings)} results")
                match_flag = False
                for idx, heading in enumerate(result_headings, 1):
                    try:
                        # Scroll to the element
                        logger.info(f"Processing result {idx}/{len(result_headings)}")
                        scroll_to_element(driver, heading)
                        
                        # Extract the link and heading text
                        href = heading.find_element(By.TAG_NAME, "a")
                        link = href.get_attribute("href")
                        heading_text = heading.find_element(By.TAG_NAME, "h3").text
                        
                        # Log the extracted data
                        logger.info(f"Title: {heading_text}")
                        logger.info(f"Link: {link}")
                        
                        if query_config['web_match'][1] in link:
                            logger.info(f"Found matching link: {link}")
                            logger.info(f"Match found at position {idx}")
                            logger.info("-" * 30)
                            match_flag = True
                            # Store the link for later use
                            return href, match_flag, link
                        logger.info("-" * 30)
                        
                        # Pause between iterations
                        time.sleep(1)
                    except Exception as e:
                        logger.error(f"Error processing result {idx}: {str(e)}")
                        continue
                
                if not match_flag:
                    logger.info("No matching link found on current page")
                return None, match_flag, None

            if len_results:
                logger.info(f"Starting pagination search through {len_results} pages")
                for page in range(int(len_results)):
                    logger.info(f"\nProcessing page {page + 1}/{len_results}")
                    headings_new = get_headings(driver)
                    match_element, flag, target_url = match_links(driver, headings_new, query_config)
                    if flag and match_element:
                        logger.info(f"Match found on page {page + 1}, preparing to click link...")
                        try:
                            # Scroll the element into view again
                            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", match_element)
                            time.sleep(1)  # Wait for scroll to complete
                            
                            # Try JavaScript click first
                            logger.info("Attempting JavaScript click...")
                            driver.execute_script("arguments[0].click();", match_element)
                            
                            # Wait for URL to change
                            logger.info("Waiting for URL to change...")
                            WebDriverWait(driver, 5).until(
                                lambda d: d.current_url != "https://www.google.com/search"
                            )
                            
                            current_url = driver.current_url
                            logger.info(f"Successfully navigated to: {current_url}")
                            
                            # Store the visited page
                            visited_pages.append({
                                'url': current_url,
                                'title': driver.title,
                                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            })
                            
                            time.sleep(2)  # Additional wait for page load
                            break
                        except Exception as e:
                            logger.error(f"Error clicking link: {str(e)}")
                            # Fallback to direct navigation
                            try:
                                logger.info("Attempting direct navigation...")
                                driver.get(target_url)
                                current_url = driver.current_url
                                logger.info(f"Directly navigated to: {current_url}")
                                
                                # Store the visited page
                                visited_pages.append({
                                    'url': current_url,
                                    'title': driver.title,
                                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                })
                                
                                time.sleep(2)
                                break
                            except Exception as e2:
                                logger.error(f"Error in direct navigation: {str(e2)}")
                    else:
                        logger.info(f"No match found on page {page + 1}")
                        if page < int(len_results) - 1:
                            logger.info("Moving to next page...")
                            try:
                                next_button = driver.find_element(By.ID, "pnnext")
                                next_button.click()
                                logger.info("Clicked next page button")
                                time.sleep(2)
                            except Exception as e:
                                logger.error(f"Error clicking next page button: {str(e)}")
                                break
            else:
                logger.info("No pagination found, searching only current page")
                headings_new = get_headings(driver)
                match_element, flag, target_url = match_links(driver, headings_new, query_config)
                if flag and match_element:
                    logger.info("Match found on current page, preparing to click link...")
                    try:
                        # Scroll the element into view again
                        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", match_element)
                        time.sleep(1)  # Wait for scroll to complete
                        
                        # Try JavaScript click first
                        logger.info("Attempting JavaScript click...")
                        driver.execute_script("arguments[0].click();", match_element)
                        
                        # Wait for URL to change
                        logger.info("Waiting for URL to change...")
                        WebDriverWait(driver, 5).until(
                            lambda d: d.current_url != "https://www.google.com/search"
                        )
                        
                        current_url = driver.current_url
                        logger.info(f"Successfully navigated to: {current_url}")
                        
                        # Store the visited page
                        visited_pages.append({
                            'url': current_url,
                            'title': driver.title,
                            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        
                        time.sleep(5)  # Additional wait for page load
                    except Exception as e:
                        logger.error(f"Error clicking link: {str(e)}")
                        # Fallback to direct navigation
                        try:
                            logger.info("Attempting direct navigation...")
                            driver.get(target_url)
                            current_url = driver.current_url
                            logger.info(f"Directly navigated to: {current_url}")
                            
                            # Store the visited page
                            visited_pages.append({
                                'url': current_url,
                                'title': driver.title,
                                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            })
                            
                            time.sleep(2)
                        except Exception as e2:
                            logger.error(f"Error in direct navigation: {str(e2)}")
                else:
                    logger.info("No match found on current page")

            # Process follow-up links
            if query_config["follow_up_links"]:
                logger.info("\nProcessing follow-up links...")
                for i, follow_up_link in enumerate(query_config["follow_up_links"], 1):
                    try:
                        logger.info(f"\n[{i}/{len(query_config['follow_up_links'])}] Visiting follow-up link: {follow_up_link}")
                        driver.get(follow_up_link)
                        
                        # Wait for page to load
                        WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.TAG_NAME, "body"))
                        )
                        
                        # Additional wait to ensure dynamic content loads
                        time.sleep(3)
                        
                        # Get page title
                        page_title = driver.title
                        logger.info(f"Page title: {page_title}")
                        
                        # Get current URL (in case of redirects)
                        current_url = driver.current_url
                        logger.info(f"Current URL: {current_url}")
                        
                        # Store the visited page
                        visited_pages.append({
                            'url': current_url,
                            'title': page_title,
                            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                        
                    except Exception as e:
                        logger.error(f"Error visiting follow-up link: {str(e)}")
                        continue
            else:
                logger.info("\nNo follow-up links to process")

            # Log all visited pages
            logger.info("\nVisited Pages Summary:")
            logger.info("-" * 50)
            for page in visited_pages:
                logger.info(f"Time: {page['timestamp']}")
                logger.info(f"Title: {page['title']}")
                logger.info(f"URL: {page['url']}")
                logger.info("-" * 30)
                    
        except Exception as e:
            logger.error(f"Error finding search results: {str(e)}")

    finally:
        logger.info(f"Closing driver for web_match: {query_config['web_match']}")
        driver.quit()

if __name__ == "__main__":
    # This allows running the file directly with pytest
    pytest.main(["-n", "2", __file__, "--query={\"web_match\":[\"trendyol\"],\"Follow_up_links\":[],\"headless\":false,\"uc\":true,\"eager\":false}", "-q"])
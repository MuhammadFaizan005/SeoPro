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
        
        # Simulate human-like typing with retry mechanism
        max_retries = 3
        for attempt in range(max_retries):
            try:
                search_box = WebDriverWait(driver, 10).until(
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
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                logger.warning(f"Attempt {attempt + 1} failed, retrying...")
                time.sleep(2)
        
        # Wait for search results with increased timeout
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "search"))
        )
        
        def get_search_results():
            """Get search results with retry mechanism."""
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # Wait for results to be present
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CLASS_NAME, "yuRUbf"))
                    )
                    
                    # Get all search results
                    results = driver.find_elements(By.CLASS_NAME, "yuRUbf")
                    if results:
                        return results
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    logger.warning(f"Attempt {attempt + 1} to get results failed, retrying...")
                    time.sleep(2)
            return []

        def process_search_result(result):
            """Process a single search result with retry mechanism."""
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # Scroll to the element
                    scroll_to_element(driver, result)
                    time.sleep(1)  # Wait for scroll to complete
                    
                    # Get link and heading with explicit wait
                    link_element = WebDriverWait(result, 5).until(
                        EC.presence_of_element_located((By.TAG_NAME, "a"))
                    )
                    heading_element = WebDriverWait(result, 5).until(
                        EC.presence_of_element_located((By.TAG_NAME, "h3"))
                    )
                    
                    link = link_element.get_attribute("href")
                    heading_text = heading_element.text
                    
                    return link, heading_text, link_element
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    logger.warning(f"Attempt {attempt + 1} to process result failed, retrying...")
                    time.sleep(2)
            return None, None, None

        def navigate_to_page(url, element=None):
            """Navigate to a page with retry mechanism."""
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    if element:
                        # Try JavaScript click first
                        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element)
                        time.sleep(1)
                        driver.execute_script("arguments[0].click();", element)
                    else:
                        driver.get(url)
                    
                    # Wait for URL to change
                    WebDriverWait(driver, 10).until(
                        lambda d: d.current_url != "https://www.google.com/search"
                    )
                    
                    # Wait for page load
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.TAG_NAME, "body"))
                    )
                    
                    return True
                except Exception as e:
                    if attempt == max_retries - 1:
                        return False
                    logger.warning(f"Attempt {attempt + 1} to navigate failed, retrying...")
                    time.sleep(2)
            return False

        # Process search results
        current_page = 1
        max_pages = 5  # Limit the number of pages to search
        found_match = False

        while current_page <= max_pages and not found_match:
            logger.info(f"\nProcessing page {current_page}")
            
            # Get search results
            results = get_search_results()
            if not results:
                logger.info("No results found on current page")
                break

            # Process each result
            for idx, result in enumerate(results, 1):
                try:
                    link, heading_text, link_element = process_search_result(result)
                    if not link:
                        continue

                    logger.info(f"Result {idx}: {heading_text}")
                    logger.info(f"Link: {link}")

                    # Check if the link matches our criteria
                    if any(match in link.lower() for match in [m.lower() for m in query_config['web_match']]):
                        logger.info(f"Found matching link: {link}")
                        found_match = True
                        
                        # Navigate to the page
                        if navigate_to_page(link, link_element):
                            visited_pages.append({
                                'url': driver.current_url,
                                'title': driver.title,
                                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            })
                            break
                except Exception as e:
                    logger.error(f"Error processing result {idx}: {str(e)}")
                    continue

            if found_match:
                break

            # Try to go to next page
            try:
                next_button = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.ID, "pnnext"))
                )
                next_button.click()
                current_page += 1
                time.sleep(2)
            except Exception as e:
                logger.info("No more pages available")
                break

        # Process follow-up links
        if query_config["follow_up_links"]:
            logger.info("\nProcessing follow-up links...")
            for i, follow_up_link in enumerate(query_config["follow_up_links"], 1):
                try:
                    logger.info(f"\n[{i}/{len(query_config['follow_up_links'])}] Visiting follow-up link: {follow_up_link}")
                    if navigate_to_page(follow_up_link):
                        visited_pages.append({
                            'url': driver.current_url,
                            'title': driver.title,
                            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        })
                except Exception as e:
                    logger.error(f"Error visiting follow-up link: {str(e)}")
                    continue

        # Log all visited pages
        logger.info("\nVisited Pages Summary:")
        logger.info("-" * 50)
        for page in visited_pages:
            logger.info(f"Time: {page['timestamp']}")
            logger.info(f"Title: {page['title']}")
            logger.info(f"URL: {page['url']}")
            logger.info("-" * 30)

    except Exception as e:
        logger.error(f"Test execution failed: {str(e)}")
        raise
    finally:
        logger.info(f"Closing driver for web_match: {query_config['web_match']}")
        driver.quit()

if __name__ == "__main__":
    # This allows running the file directly with pytest
    pytest.main(["-n", "2", __file__, "--query={\"web_match\":[\"trendyol\"],\"Follow_up_links\":[],\"headless\":false,\"uc\":true,\"eager\":false}", "-q"])
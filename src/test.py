import subprocess
import json
import logging
import os
from datetime import datetime

# Create logs directory if it doesn't exist
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Create data directory if it doesn't exist
data_dir = "data"
if not os.path.exists(data_dir):
    os.makedirs(data_dir)

# Generate log filename with timestamp
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = os.path.join(log_dir, f"test_run_{timestamp}.log")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()  # This will also show logs in console
    ]
)
logger = logging.getLogger(__name__)

# def load_views_data():
#     """Load views data from JSON file."""
#     views_file = os.path.join(data_dir, "views_data.json")
#     if os.path.exists(views_file):
#         try:
#             with open(views_file, 'r') as f:
#                 return json.load(f)
#         except json.JSONDecodeError:
#             logger.error("Error reading views data file, creating new one")
#     return {"current_views": 0, "target_views": 100}

def save_views_data(data):
    """Save views data to JSON file."""
    views_file = os.path.join(data_dir, "views_data.json")
    with open(views_file, 'w') as f:
        json.dump(data, f, indent=4)

def run_tests_in_parallel():
    # logger.info(f"Log file created at: {log_file}")
    
    # # Load current views data
    # views_data = load_views_data()
    # current_views = views_data["current_views"]
    # target_views = views_data["target_views"]
    
    # logger.info(f"Current views: {current_views}/{target_views}")
    
    # if current_views >= target_views:
    #     logger.info("Target views reached, no need to run more sessions")
    #     return
    
    # Base query and number of threads
    query = {
        "web_match": ["trendyol", "trendyol.com"],
        "Follow_up_links": [
            "https://www.trendyol.com/sr?q=sheovation&qt=sheovation&st=sheovation&os=1",
            "https://www.trendyol.com/sheovation/leke-karsiti-aydinlatici-gozenek-sikilastirici-c-vitamini-serum-arbutin-ha-tranexamic-acid-p-891727886?boutiqueId=61&merchantId=159188"
        ],
        "headless": False,
        "uc": True,
        "eager": False,
        "num_threads": 4,
        "views": 100,
    }
    
    # Get number of threads before converting to JSON
    num_threads = str(query["num_threads"])
    
    # Convert query dictionary to JSON string
    query_json = json.dumps(query)
    
    # Generate the pytest command with the arguments
    pytest_args = [
        "pytest",  # Run pytest as a subprocess
        "-n", num_threads,  # Number of parallel threads
        "src/main2.py",  # Test script file path
        f"--query={query_json}",  # Pass the query as JSON string
        "-v",  # Verbose mode to show more output
        "--log-cli-level=INFO",  # Enable logging at INFO level
        "--capture=no",  # Don't capture stdout/stderr
        f"--log-file={log_file}",  # Save pytest logs to the same file
    ]
    
    logger.info("Starting test execution with configuration:")
    logger.info(f"Number of threads: {num_threads}")
    logger.info(f"Query configuration: {query}")
    
    # Execute the pytest command
    try:
        chk_flag = False
        over_all_views = 0
        while chk_flag == False:
            subprocess.run(pytest_args, check=True)
            logger.info("Test execution completed successfully")
            # Parse the query_json string back to dictionary
            query_dict = json.loads(query_json)
            total_links = len(query_dict['Follow_up_links']) + 1
            performed_views = total_links * int(num_threads)
            over_all_views += performed_views
            logger.info(f"Current total views: {over_all_views}/{query_dict['views']}")
            if over_all_views >= query_dict['views']:
                chk_flag = True
                logger.info(f"Target views reached: {over_all_views}")
                break
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Test execution failed with error: {e}")
        raise

if __name__ == "__main__":
    run_tests_in_parallel()

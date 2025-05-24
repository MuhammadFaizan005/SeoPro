from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import subprocess
import json
import logging
import os
from datetime import datetime

# Create logs directory if it doesn't exist
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# Generate log filename with timestamp
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_file = os.path.join(log_dir, f"test_run_{timestamp}.log")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = FastAPI(title="SEO Test Runner API")

class FollowUpLinks(BaseModel):
    Follow_up_links: List[str]

@app.post("/run-test")
async def run_test(
    follow_up_links: FollowUpLinks,
    web_match: List[str] = Query(["trendyol", "trendyol.com"]),
    headless: bool = Query(False),
    uc: bool = Query(True),
    eager: bool = Query(False),
    Browser: int = Query(4, description="Number of browser instances to run in parallel"),
    views: int = Query(100)
):
    try:
        # Create query dictionary
        query = {
            "web_match": web_match,
            "Follow_up_links": follow_up_links.Follow_up_links,
            "headless": headless,
            "uc": uc,
            "eager": eager,
            "num_threads": Browser,  # Using Browser value for num_threads
            "views": views
        }
        
        # Get number of threads
        num_threads = str(Browser)
        
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
        logger.info(f"Number of browsers: {Browser}")
        logger.info(f"Query configuration: {query}")
        
        # Execute the pytest command
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
        
        return {
            "status": "success",
            "message": "Test execution completed",
            "total_views": over_all_views,
            "target_views": query["views"],
            "log_file": log_file
        }
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Test execution failed with error: {e}")
        raise HTTPException(status_code=500, detail=f"Test execution failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@app.get("/")
async def root():
    return {
        "message": "SEO Test Runner API",
        "endpoints": {
            "/run-test": "POST - Run SEO tests with configuration",
            "/": "GET - API information"
        }
    }

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True) 
from seleniumbase import Driver
from selenium.common.exceptions import WebDriverException
import os
import random
import ua_generator
import logging
import tempfile
import shutil
import sys

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_random_user_agent():
    user_agent_obj = ua_generator.generate(device='mobile')
    return user_agent_obj.text

class CustomSeleniumBaseDriver:
    def __init__(self, uc=True, headless=False, eager_load=True, window_width=None, window_height=None,):
        self.uc = uc
        self.headless = headless
        self.eager_load = eager_load
        self.window_width = window_width
        self.window_height = window_height
        self.user_agent = get_random_user_agent()
        self.driver = self._initialize_driver()

    def _initialize_driver(self):

        options = {
            "browser": "chrome",
            "uc": self.uc,  # Now set to False so it won't download undetected-chrome
            "page_load_strategy": "eager" if self.eager_load else "normal",
            "d_width": self.window_width,
            "d_height": self.window_height,
            "headless": self.headless,  # Use normal headless mode
            
        }
        # if self.user_agent:
        #     options["user_agent"] = self.user_agent
        # Common paths to check for the Chromium or Chrome binary
        common_paths = [
            "/usr/bin/chromedriver",  # Docker/Linux
            "/usr/local/bin/chromedriver",  # macOS/Linux
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",  # macOS
            "/opt/homebrew/bin/chromedriver",  # macOS (Apple Silicon)
            # Windows common paths:
            "C:\\Program Files\\chromedriver\\chromedriver.exe",
            "C:\\Program Files (x86)\\chromedriver\\chromedriver.exe",
            "C:\\chromedriver\\chromedriver.exe",
            "C:\\WebDriver\\bin\\chromedriver.exe",
            "C:\\Windows\\chromedriver.exe",
            "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
            "C:\\Windows\\System32\\chromedriver.exe"
        ]

        binary_location = None
        for path in common_paths:
            if os.path.exists(path):
                binary_location = path
                break

        if binary_location:
            options["binary_location"] = binary_location  # Add only if the file exists

        try:
            if binary_location:
                print("Initializing SeleniumBase driver with binary_location in {}".format(binary_location))
            else:
                print("Initializing SeleniumBase driver without specifying binary_location")

            return Driver(**options)
        except WebDriverException as e:
            print("Initialization failed:", e)

        raise WebDriverException("All attempts to initialize the SeleniumBase driver failed.")
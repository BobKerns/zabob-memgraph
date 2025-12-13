"""
Playwright configuration for UI testing.
"""

# Timeout settings
DEFAULT_TIMEOUT = 30000  # 30 seconds
NAVIGATION_TIMEOUT = 30000
EXPECT_TIMEOUT = 5000

# Browser settings
HEADLESS = True
SLOW_MO = 0  # Slow down operations by N milliseconds

# Screenshot and video settings
SCREENSHOT_ON_FAILURE = True
VIDEO_ON_FAILURE = False

# Base URL
BASE_URL = "http://localhost:8080"

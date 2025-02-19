import logging
import time
import functools
from config import LOGGING_CONFIG, RATE_LIMITS, INTERACTION_LIMITS
import os
from datetime import datetime, timedelta

def setup_logging():
    """Configure and setup logging"""
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)

    # Configure logging
    logging.basicConfig(
        filename=LOGGING_CONFIG['filename'],
        format=LOGGING_CONFIG['format'],
        level=LOGGING_CONFIG['level']
    )

    # Also log to console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(LOGGING_CONFIG['format']))
    logging.getLogger('').addHandler(console_handler)

    return logging.getLogger('InstagramBot')

def handle_rate_limit(func):
    """Decorator to handle rate limiting and retries"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        retries = 0
        while retries < RATE_LIMITS['max_retries']:
            try:
                result = func(*args, **kwargs)
                time.sleep(RATE_LIMITS['default_delay'])
                return result
            except Exception as e:
                if "rate limit" in str(e).lower():
                    retries += 1
                    if retries < RATE_LIMITS['max_retries']:
                        logging.warning(f"Rate limit hit, waiting {RATE_LIMITS['retry_delay']} seconds before retry {retries}/{RATE_LIMITS['max_retries']}")
                        time.sleep(RATE_LIMITS['retry_delay'])
                    else:
                        logging.error("Max retries reached for rate limit")
                        raise
                else:
                    raise
    return wrapper

class InteractionLimiter:
    def __init__(self):
        self.limits = {
            'likes': {'hourly': 0, 'daily': 0, 'last_reset': datetime.now()},
            'follows': {'hourly': 0, 'daily': 0, 'last_reset': datetime.now()}
        }
        self.logger = logging.getLogger('InstagramBot')

    def _should_reset_counters(self):
        """Check if counters should be reset based on time"""
        now = datetime.now()

        # Reset daily counters at midnight if enabled
        if INTERACTION_LIMITS['reset_at_midnight']:
            for action_type in self.limits:
                last_reset = self.limits[action_type]['last_reset']
                if now.date() > last_reset.date():
                    self.limits[action_type]['daily'] = 0
                    self.limits[action_type]['hourly'] = 0
                    self.limits[action_type]['last_reset'] = now
                    self.logger.info(f"Reset {action_type} counters at midnight")

        # Reset hourly counters
        for action_type in self.limits:
            last_reset = self.limits[action_type]['last_reset']
            if now - last_reset > timedelta(hours=1):
                self.limits[action_type]['hourly'] = 0
                self.limits[action_type]['last_reset'] = now
                self.logger.info(f"Reset hourly {action_type} counter")

    def can_perform_action(self, action_type):
        """Check if an action can be performed based on limits"""
        if not INTERACTION_LIMITS[action_type]['enabled']:
            return True

        self._should_reset_counters()

        hourly_limit = INTERACTION_LIMITS[action_type]['hourly_limit']
        daily_limit = INTERACTION_LIMITS[action_type]['daily_limit']

        if self.limits[action_type]['hourly'] >= hourly_limit:
            self.logger.warning(f"Hourly {action_type} limit reached ({hourly_limit})")
            return False

        if self.limits[action_type]['daily'] >= daily_limit:
            self.logger.warning(f"Daily {action_type} limit reached ({daily_limit})")
            return False

        return True

    def increment_action(self, action_type):
        """Increment the counter for a specific action"""
        self.limits[action_type]['hourly'] += 1
        self.limits[action_type]['daily'] += 1
        self.logger.info(f"Performed {action_type} action. "
                        f"Hourly: {self.limits[action_type]['hourly']}/{INTERACTION_LIMITS[action_type]['hourly_limit']}, "
                        f"Daily: {self.limits[action_type]['daily']}/{INTERACTION_LIMITS[action_type]['daily_limit']}")
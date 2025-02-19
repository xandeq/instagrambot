import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Instagram credentials
CREDENTIALS = {
    'username': os.getenv('INSTAGRAM_USERNAME'),
    'password': os.getenv('INSTAGRAM_PASSWORD')
}

# Optional settings
OPTIONAL_SETTINGS = {
    'proxy_url': os.getenv('PROXY_URL'),
    'verification_code': os.getenv('VERIFICATION_CODE')
}

# Logging configuration
LOGGING_CONFIG = {
    'filename': 'logs/instagram_bot.log',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'level': 'INFO'
}

# Rate limiting configuration
RATE_LIMITS = {
    'default_delay': 30,  # seconds
    'max_retries': 3,
    'retry_delay': 60,  # seconds
    'login_retry_delay': 300  # 5 minutes delay between login attempts
}

# Interaction limits configuration
INTERACTION_LIMITS = {
    'likes': {
        'hourly_limit': 20,    # Maximum likes per hour
        'daily_limit': 100,    # Maximum likes per day
        'enabled': True        # Enable/disable like limits
    },
    'follows': {
        'hourly_limit': 10,    # Maximum follows per hour
        'daily_limit': 50,     # Maximum follows per day
        'enabled': True        # Enable/disable follow limits
    },
    'reset_at_midnight': True  # Whether to reset counters at midnight
}

# Hashtag configuration
HASHTAG_CONFIG = {
    'hashtags': [
        'pousadadecharme',
        'pousada',
        'pousadas',
        'pousadastop',
        'pousadatop',
        'pousadasrural',
    ],
    'posts_per_hashtag': 5,    # Number of posts to like per hashtag
    'max_hashtags': 2,         # Maximum number of hashtags to process in one run
    'randomize': True          # Whether to randomize hashtag selection
}
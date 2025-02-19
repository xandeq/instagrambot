import random
from instagrapi import Client
from config import CREDENTIALS, HASHTAG_CONFIG, LOGGING_CONFIG, RATE_LIMITS, INTERACTION_LIMITS
import logging
import time
from utils import setup_logging, handle_rate_limit, InteractionLimiter
import os
import json

# Setup logging
logger = setup_logging()

class InstagramBot:
    def __init__(self):
        self.cl = Client()
        self.authenticated = False
        self.limiter = InteractionLimiter()

    def authenticate(self):
        """Authenticate with Instagram using credentials from config"""
        try:
            logger.info("Attempting to authenticate with Instagram")

            # Set up custom device
            self.cl.set_device({
                "app_version": "269.0.0.18.75",
                "android_version": 26,
                "android_release": "8.0.0",
                "dpi": "480dpi",
                "resolution": "1080x1920",
                "manufacturer": "OnePlus",
                "device": "GT-S7580",
                "model": "6T",
                "cpu": "qcom",
                "version_code": "301484483",
            })

            # Set proxy if available
            if os.getenv('PROXY_URL'):
                logger.info("Using proxy for authentication")
                self.cl.set_proxy(os.getenv('PROXY_URL'))

            verification_code = os.getenv('VERIFICATION_CODE')
            if verification_code:
                logger.info("Verification code found, will use it if challenge required")

            # Attempt login with additional settings
            try:
                login_response = self.cl.login(
                    CREDENTIALS['username'],
                    CREDENTIALS['password'],
                    relogin=True,
                    verification_code=verification_code
                )

                if login_response:
                    self.authenticated = True
                    logger.info("Successfully authenticated with Instagram")
                    return True
                else:
                    logger.error("Login failed - no response received")
                    return False

            except Exception as login_error:
                error_message = str(login_error).lower()
                if "challenge_required" in error_message:
                    if not verification_code:
                        logger.error("Instagram requires verification code. Please set VERIFICATION_CODE environment variable")
                        return False
                    logger.error("Challenge required but verification code was invalid")
                    return False
                raise  # Re-raise other login errors

        except Exception as e:
            error_message = str(e).lower()
            if "bad_password" in error_message:
                logger.error("Incorrect password provided")
            elif "invalid_user" in error_message:
                logger.error("Username not found")
            elif "ip" in error_message and "blacklist" in error_message:
                logger.error("IP address is blacklisted. Consider using a proxy or waiting before retrying")
            else:
                logger.error(f"Authentication failed: {str(e)}")
            return False

    @handle_rate_limit
    def get_profile_info(self, username):
        """Retrieve profile information for a given username"""
        try:
            # Use private API endpoint directly instead of public API
            user_id = self.cl.user_id_from_username(username)
            user_info = self.cl.user_info(user_id)

            if user_info:
                logger.info(f"Successfully retrieved profile info for {username}")
                return user_info
            else:
                logger.warning(f"No profile information found for {username}")
                return None

        except json.JSONDecodeError as je:
            logger.debug(f"JSON parsing error while fetching profile info (non-critical): {str(je)}")
            return None
        except Exception as e:
            logger.error(f"Failed to get profile info for {username}: {str(e)}")
            return None

    @handle_rate_limit
    def like_hashtag_posts(self, hashtag, count=10):
        """Like recent posts from a specific hashtag and save unique URLs to a text file"""
        if not self.limiter.can_perform_action('likes'):
            logger.warning("Like limit reached, skipping like_hashtag_posts")
            return False

        try:
            medias = self.cl.hashtag_medias_recent(hashtag, amount=count)

            if not medias:
                logger.warning(f"No posts found for hashtag #{hashtag}")
                return False

            # Ler URLs já curtidas para evitar duplicação
            if os.path.exists("liked_posts.txt"):
                with open("liked_posts.txt", "r", encoding="utf-8") as file:
                    liked_urls = set(file.read().splitlines())
            else:
                liked_urls = set()

            liked_count = 0
            for post in medias:
                if not self.limiter.can_perform_action('likes'):
                    logger.warning("Like limit reached during execution")
                    break

                try:
                    if self.cl.media_like(post.id):
                        self.limiter.increment_action('likes')
                        liked_count += 1

                        media_info = self.cl.media_info(post.id)
                        post_url = f"https://www.instagram.com/p/{media_info.code}/"

                        # Evita salvar URLs duplicadas
                        if post_url not in liked_urls:
                            with open("liked_posts.txt", "a", encoding="utf-8") as file:
                                file.write(post_url + "\n")
                            liked_urls.add(post_url)

                        logger.info(f"✔️ Liked: {post_url}")
                        print(f"✔️ Liked: {post_url}")

                        time.sleep(30)  # Delay de 30 segundos entre curtidas

                except Exception as e:
                    if "already liked" in str(e).lower():
                        logger.info(f"Post {post.id} was already liked")
                    else:
                        logger.error(f"Failed to like post {post.id}: {str(e)}")

            logger.info(f"Successfully liked {liked_count} posts from #{hashtag}")
            return liked_count > 0

        except json.JSONDecodeError as je:
            logger.debug(f"JSON parsing error while liking hashtag posts (non-critical): {str(je)}")
            return False
        except Exception as e:
            logger.error(f"Failed to like posts from #{hashtag}: {str(e)}")
            return False

    def like_multiple_hashtags(self):
        """Like posts from multiple randomly selected hashtags"""
        available_hashtags = HASHTAG_CONFIG['hashtags']
        
        if HASHTAG_CONFIG['randomize']:
            random.shuffle(available_hashtags)  # Embaralha antes de escolher

        selected_hashtags = available_hashtags[:HASHTAG_CONFIG['max_hashtags']]
        logger.info(f"Selected hashtags for this run: {selected_hashtags}")

        total_likes = 0
        for hashtag in selected_hashtags:
            if not self.limiter.can_perform_action('likes'):
                logger.warning("Overall like limit reached, stopping hashtag processing")
                break

            if self.like_hashtag_posts(hashtag, HASHTAG_CONFIG['posts_per_hashtag']):
                total_likes += 1
                time.sleep(RATE_LIMITS['default_delay'])

        return total_likes

    @handle_rate_limit
    def follow_user(self, username):
        """Follow a specific user"""
        if not self.limiter.can_perform_action('follows'):
            logger.warning("Follow limit reached, skipping follow_user")
            return False

        try:
            user_id = self.cl.user_id_from_username(username)
            if self.cl.user_follow(user_id):
                self.limiter.increment_action('follows')
                logger.info(f"Successfully followed user {username}")
                return True
            return False
        except json.JSONDecodeError as je:
            logger.debug(f"JSON parsing error while following user (non-critical): {str(je)}")
            return False
        except Exception as e:
            logger.error(f"Failed to follow user {username}: {str(e)}")
            return False

    def close(self):
        """Properly close the Instagram client"""
        try:
            self.cl.logout()
            logger.info("Successfully logged out")
        except Exception as e:
            logger.error(f"Error during logout: {str(e)}")

def main():
    bot = InstagramBot()

    # Authenticate
    if not bot.authenticate():
        logger.error("Failed to authenticate. Exiting...")
        return

    try:
        while True:
            # Get profile information (opcional)
            profile_info = bot.get_profile_info(CREDENTIALS['username'])
            if profile_info:
                logger.info(f"Profile followers: {profile_info.follower_count}")

            # Like posts by hashtag
            bot.like_multiple_hashtags()
            bot.like_hashtag_posts("espiritosanto", count=15)

            # Espera 5 minutos antes de curtir mais posts (ajuste conforme necessário)
            logger.info("Waiting 5 minutes before liking more posts...")
            time.sleep(300)  # 300 segundos = 5 minutos

    except KeyboardInterrupt:
        logger.info("Bot stopped manually.")
    except Exception as e:
        logger.error(f"An error occurred during execution: {str(e)}")
    finally:
        bot.close()

if __name__ == "__main__":
    main()
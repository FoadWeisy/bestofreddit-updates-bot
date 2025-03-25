import os
import logging
import praw
import tweepy
import time
import json
from dotenv import load_dotenv
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console handler first
        logging.FileHandler('bot.log')
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# File to store posted thread IDs
POSTED_THREADS_FILE = 'posted_threads.json'

def load_posted_threads():
    """Load the list of previously posted thread IDs."""
    try:
        if os.path.exists(POSTED_THREADS_FILE):
            with open(POSTED_THREADS_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading posted threads: {str(e)}")
    return []

def save_posted_thread(thread_id):
    """Save a posted thread ID to the file."""
    try:
        posted_threads = load_posted_threads()
        posted_threads.append(thread_id)
        with open(POSTED_THREADS_FILE, 'w') as f:
            json.dump(posted_threads, f)
    except Exception as e:
        logger.error(f"Error saving posted thread: {str(e)}")

def get_thread_summary(post):
    """Get a summary of the thread content."""
    try:
        # Get the first comment that's not from the OP
        for comment in post.comments:
            if not comment.stickied and not comment.is_submitter:
                # Get first 100 characters of the comment
                summary = comment.body[:100]
                if len(comment.body) > 100:
                    summary += "..."
                return summary
    except Exception as e:
        logger.error(f"Error getting thread summary: {str(e)}")
    return None

print("Starting bot with following configuration:")
print(f"TWITTER_API_KEY exists: {bool(os.getenv('TWITTER_API_KEY'))}")
print(f"TWITTER_API_SECRET exists: {bool(os.getenv('TWITTER_API_SECRET'))}")
print(f"TWITTER_ACCESS_TOKEN exists: {bool(os.getenv('TWITTER_ACCESS_TOKEN'))}")
print(f"TWITTER_ACCESS_TOKEN_SECRET exists: {bool(os.getenv('TWITTER_ACCESS_TOKEN_SECRET'))}")
print(f"REDDIT_CLIENT_ID exists: {bool(os.getenv('REDDIT_CLIENT_ID'))}")
print(f"REDDIT_CLIENT_SECRET exists: {bool(os.getenv('REDDIT_CLIENT_SECRET'))}")

# Reddit API setup
reddit = praw.Reddit(
    client_id=os.getenv('REDDIT_CLIENT_ID'),
    client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
    user_agent=os.getenv('REDDIT_USER_AGENT')
)

# Twitter API v2 setup with Free tier
client = tweepy.Client(
    bearer_token=None,  # Not needed for OAuth 1.0a
    consumer_key=os.getenv('TWITTER_API_KEY'),
    consumer_secret=os.getenv('TWITTER_API_SECRET'),
    access_token=os.getenv('TWITTER_ACCESS_TOKEN'),
    access_token_secret=os.getenv('TWITTER_ACCESS_TOKEN_SECRET'),
    wait_on_rate_limit=True
)

def truncate_text(text, max_length=275):  # 280 - 5 for safety
    """Truncate text to fit Twitter's character limit."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."

def post_reddit_update():
    """Fetch top post from r/BestofRedditorUpdates and post to Twitter."""
    try:
        print("\nFetching posts from Reddit...")
        # Fetch top post from the subreddit
        subreddit = reddit.subreddit('BestofRedditorUpdates')
        
        # Load previously posted threads
        posted_threads = load_posted_threads()
        print(f"\nPreviously posted {len(posted_threads)} threads")
        
        # Get the top 5 posts to see what's available
        print("\nTop 5 posts from r/BestofRedditorUpdates:")
        for post in subreddit.hot(limit=5):
            print(f"- {post.title}")
            print(f"  Score: {post.score}, URL: https://reddit.com{post.permalink}")
            print(f"  Sticky: {post.stickied}")
            print(f"  Previously posted: {post.id in posted_threads}")
        
        # Get the first non-stickied, non-posted post
        top_post = None
        for post in subreddit.hot(limit=20):  # Check more posts to find a suitable one
            if not post.stickied and post.id not in posted_threads:
                top_post = post
                break
        
        if not top_post:
            print("No suitable new posts found!")
            logger.warning("No suitable new posts found!")
            return
            
        print(f"\nSelected post to tweet: {top_post.title}")
        
        # Get thread summary
        summary = get_thread_summary(top_post)
        if summary:
            print(f"Thread summary: {summary}")
        
        # Create tweet content with truncation
        title = truncate_text(top_post.title)
        url = f"https://reddit.com{top_post.permalink}"
        
        # Create tweet text with summary if available
        if summary:
            tweet_text = f"{title}\n\n{summary}\n\n{url}"
        else:
            tweet_text = f"{title}\n\n{url}"
            
        print(f"Preparing to tweet: {tweet_text}")
        
        # Add a small delay to ensure we can see the output
        print("\nWaiting 2 seconds before posting to Twitter...")
        time.sleep(2)
        
        # Post to Twitter using v2 API
        try:
            print("\nAttempting to post to Twitter...")
            print("Using Twitter credentials:")
            print(f"API Key: {os.getenv('TWITTER_API_KEY')[:5]}...")
            print(f"Access Token: {os.getenv('TWITTER_ACCESS_TOKEN')[:5]}...")
            
            response = client.create_tweet(
                text=tweet_text,
                user_auth=True
            )
            
            print("Twitter API Response:", response)
            tweet_id = response.data['id']
            print(f"Successfully posted! Tweet ID: {tweet_id}")
            
            # Save the posted thread ID
            save_posted_thread(top_post.id)
            
            logger.info(f"Successfully posted tweet ID: {tweet_id}")
            logger.info(f"Tweet content: {tweet_text}")
            
        except tweepy.errors.Forbidden as e:
            print(f"\nTwitter API Forbidden error: {str(e)}")
            print("This usually means the app doesn't have the correct permissions.")
            logger.error(f"Twitter API Forbidden error: {str(e)}")
            logger.error("Please check your API access level and permissions")
        except tweepy.errors.Unauthorized as e:
            print(f"\nTwitter API Unauthorized error: {str(e)}")
            print("This usually means the credentials are incorrect.")
            logger.error(f"Twitter API Unauthorized error: {str(e)}")
        except tweepy.errors.TweepyException as e:
            print(f"\nTwitter API error: {str(e)}")
            logger.error(f"Twitter API error: {str(e)}")
            
    except Exception as e:
        print(f"\nGeneral error: {str(e)}")
        logger.error(f"General error: {str(e)}")

def main():
    """Main function to run the posting function once."""
    try:
        print("\nRunning Reddit to Twitter bot (single run)...")
        post_reddit_update()
        print("\nBot execution completed.")
        
    except Exception as e:
        print(f"Error during execution: {str(e)}")
        logger.error(f"Error during execution: {str(e)}")

if __name__ == "__main__":
    main() 
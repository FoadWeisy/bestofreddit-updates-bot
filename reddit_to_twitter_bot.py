import os
import logging
import praw
import tweepy
import time
import json
from dotenv import load_dotenv
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
import random

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

def clean_markdown(text):
    """Remove markdown formatting and metadata from text."""
    # Remove markdown formatting
    text = text.replace('**', '')
    text = text.replace('*', '')
    text = text.replace('[', '').replace(']', '')
    text = text.replace('u/', '@')
    text = text.replace('r/', '')
    
    # Split into lines and process
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        # Skip empty lines
        if not line:
            continue
        # Skip common metadata lines
        if any(skip in line.lower() for skip in [
            'i am not oop',
            'originally posted',
            'mood spoiler',
            'trigger warning',
            'content warning',
            'update:',
            'edit:',
            'tl;dr',
            'tldr',
            'editor\'s note',
            'note:',
            'thanks to',
            'credit to',
            'posted by',
            'submitted by',
            'reposted from',
            'crossposted from',
            'source:',
            'background:',
            'context:'
        ]):
            continue
        cleaned_lines.append(line)
    
    # Join lines with proper spacing
    text = ' '.join(cleaned_lines)
    
    # Remove multiple spaces
    text = ' '.join(text.split())
    
    return text

def get_thread_summary(post):
    """Get a summary of the thread content."""
    try:
        # First try to get the post body for context
        if hasattr(post, 'selftext') and post.selftext:
            # Clean up markdown and use improved truncation
            cleaned_text = clean_markdown(post.selftext)
            # Skip if it's too short after cleaning
            if len(cleaned_text) < 20:
                return None
            # If the cleaned text starts with the title, remove it to avoid repetition
            if cleaned_text.lower().startswith(post.title.lower()):
                cleaned_text = cleaned_text[len(post.title):].strip()
            summary = truncate_text(cleaned_text, max_length=100)
            if summary:
                return f"From post: {summary}"
            
        # If no post body, get the first meaningful comment
        for comment in post.comments:
            if not comment.stickied and not comment.is_submitter:
                # Skip very short or meme-like comments
                if len(comment.body) < 20 or "XD" in comment.body or "lol" in comment.body.lower():
                    continue
                # Clean up markdown and use improved truncation
                cleaned_text = clean_markdown(comment.body)
                if len(cleaned_text) < 20:
                    continue
                # If the comment starts with the title, remove it to avoid repetition
                if cleaned_text.lower().startswith(post.title.lower()):
                    cleaned_text = cleaned_text[len(post.title):].strip()
                summary = truncate_text(cleaned_text, max_length=100)
                if summary:
                    return f"Top comment: {summary}"
                
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
    """Truncate text to fit Twitter's character limit while preserving sentence boundaries."""
    if len(text) <= max_length:
        return text
        
    # Find the last complete sentence within the max length
    truncated = text[:max_length - 3]
    
    # Find the last sentence boundary (., !, or ?)
    last_period = truncated.rfind('.')
    last_exclamation = truncated.rfind('!')
    last_question = truncated.rfind('?')
    
    # Get the last sentence boundary
    last_boundary = max(last_period, last_exclamation, last_question)
    
    if last_boundary > 0:
        # Cut at the last sentence boundary and add ellipsis
        return truncated[:last_boundary + 1] + "..."
    else:
        # If no sentence boundary found, cut at the last space
        last_space = truncated.rfind(' ')
        if last_space > 0:
            return truncated[:last_space] + "..."
        else:
            # If no space found, just cut at max length
            return truncated + "..."

def get_engagement_question(title):
    """Generate a contextual engagement question based on the post title."""
    # Keywords to identify the type of post
    keywords = {
        'AITA': ['What do you think? Is this person the AH? 🤔', 'Who\'s in the wrong here? 🤔'],
        'Help': ['What advice would you give? 🤔', 'How would you handle this? 🤔'],
        'Update': ['What do you think about this update? 🤔', 'How would you react to this? 🤔'],
        'Found': ['What would you do if you found this? 🤔', 'How would you handle this discovery? 🤔'],
        'Told': ['What would you say in this situation? 🤔', 'How would you respond? 🤔'],
        'Sister': ['Family drama! What would you do? 🤔', 'How would you handle family conflict? 🤔'],
        'Brother': ['Family drama! What would you do? 🤔', 'How would you handle family conflict? 🤔'],
        'Mother': ['Family drama! What would you do? 🤔', 'How would you handle family conflict? 🤔'],
        'Father': ['Family drama! What would you do? 🤔', 'How would you handle family conflict? 🤔'],
        'Wife': ['Marriage drama! What would you do? 🤔', 'How would you handle this relationship issue? 🤔'],
        'Husband': ['Marriage drama! What would you do? 🤔', 'How would you handle this relationship issue? 🤔'],
        'Partner': ['Relationship drama! What would you do? 🤔', 'How would you handle this relationship issue? 🤔'],
        'Friend': ['Friendship drama! What would you do? 🤔', 'How would you handle this friendship issue? 🤔'],
        'Work': ['Workplace drama! What would you do? 🤔', 'How would you handle this work situation? 🤔'],
        'School': ['School drama! What would you do? 🤔', 'How would you handle this school situation? 🤔'],
        'Money': ['Money drama! What would you do? 🤔', 'How would you handle this financial situation? 🤔'],
        'House': ['Housing drama! What would you do? 🤔', 'How would you handle this housing situation? 🤔'],
        'Car': ['Car drama! What would you do? 🤔', 'How would you handle this car situation? 🤔'],
        'Pet': ['Pet drama! What would you do? 🤔', 'How would you handle this pet situation? 🤔'],
        'Food': ['Food drama! What would you do? 🤔', 'How would you handle this food situation? 🤔'],
        'Party': ['Party drama! What would you do? 🤔', 'How would you handle this party situation? 🤔'],
        'Wedding': ['Wedding drama! What would you do? 🤔', 'How would you handle this wedding situation? 🤔'],
        'Baby': ['Baby drama! What would you do? 🤔', 'How would you handle this parenting situation? 🤔'],
        'Child': ['Parenting drama! What would you do? 🤔', 'How would you handle this parenting situation? 🤔'],
        'Kid': ['Parenting drama! What would you do? 🤔', 'How would you handle this parenting situation? 🤔'],
        'DNA': ['This is wild! What would you do? 🤔', 'This is crazy! How would you handle this? 🤔'],
        'Test': ['This is wild! What would you do? 🤔', 'This is crazy! How would you handle this? 🤔'],
        'Results': ['This is wild! What would you do? 🤔', 'This is crazy! How would you handle this? 🤔'],
        'Found out': ['This is wild! What would you do? 🤔', 'This is crazy! How would you handle this? 🤔'],
        'Discovered': ['This is wild! What would you do? 🤔', 'This is crazy! How would you handle this? 🤔'],
        'Shocked': ['This is wild! What would you do? 🤔', 'This is crazy! How would you handle this? 🤔'],
        'Surprised': ['This is wild! What would you do? 🤔', 'This is crazy! How would you handle this? 🤔'],
        'Angry': ['This is wild! What would you do? 🤔', 'This is crazy! How would you handle this? 🤔'],
        'Mad': ['This is wild! What would you do? 🤔', 'This is crazy! How would you handle this? 🤔'],
        'Upset': ['This is wild! What would you do? 🤔', 'This is crazy! How would you handle this? 🤔'],
        'Happy': ['This is wild! What would you do? 🤔', 'This is crazy! How would you handle this? 🤔'],
        'Excited': ['This is wild! What would you do? 🤔', 'This is crazy! How would you handle this? 🤔'],
        'Sad': ['This is wild! What would you do? 🤔', 'This is crazy! How would you handle this? 🤔'],
        'Depressed': ['This is wild! What would you do? 🤔', 'This is crazy! How would you handle this? 🤔'],
        'Anxious': ['This is wild! What would you do? 🤔', 'This is crazy! How would you handle this? 🤔'],
        'Worried': ['This is wild! What would you do? 🤔', 'This is crazy! How would you handle this? 🤔'],
        'Scared': ['This is wild! What would you do? 🤔', 'This is crazy! How would you handle this? 🤔'],
        'Afraid': ['This is wild! What would you do? 🤔', 'This is crazy! How would you handle this? 🤔'],
        'Terrified': ['This is wild! What would you do? 🤔', 'This is crazy! How would you handle this? 🤔'],
        'Confused': ['This is wild! What would you do? 🤔', 'This is crazy! How would you handle this? 🤔'],
        'Lost': ['This is wild! What would you do? 🤔', 'This is crazy! How would you handle this? 🤔'],
        'Stuck': ['This is wild! What would you do? 🤔', 'This is crazy! How would you handle this? 🤔'],
        'Trapped': ['This is wild! What would you do? 🤔', 'This is crazy! How would you handle this? 🤔']
    }
    
    # Check for keywords in the title
    title_lower = title.lower()
    for keyword, questions in keywords.items():
        if keyword.lower() in title_lower:
            # Return a random question from the list
            return random.choice(questions)
    
    # Default question if no keywords match
    return "What would you do in this situation? 🤔"

def post_reddit_update():
    """Fetch top post from r/BestofRedditorUpdates and post to Twitter."""
    try:
        logger.info("\n=== Starting new post update ===")
        print("\nFetching posts from Reddit...")
        # Fetch top post from the subreddit
        subreddit = reddit.subreddit('BestofRedditorUpdates')
        
        # Load previously posted threads
        posted_threads = load_posted_threads()
        logger.info(f"\nPreviously posted {len(posted_threads)} threads")
        
        # Get the top 5 posts to see what's available
        logger.info("\nTop 5 posts from r/BestofRedditorUpdates:")
        for post in subreddit.hot(limit=5):
            logger.info(f"- {post.title}")
            logger.info(f"  Score: {post.score}, URL: https://reddit.com{post.permalink}")
            logger.info(f"  Sticky: {post.stickied}")
            logger.info(f"  Previously posted: {post.id in posted_threads}")
        
        # Get the first non-stickied, non-posted post
        top_post = None
        for post in subreddit.hot(limit=20):  # Check more posts to find a suitable one
            if not post.stickied and post.id not in posted_threads:
                top_post = post
                break
        
        if not top_post:
            logger.warning("No suitable new posts found!")
            return
            
        logger.info(f"\nSelected post to tweet: {top_post.title}")
        
        # Get thread summary
        summary = get_thread_summary(top_post)
        if summary:
            logger.info(f"Thread summary: {summary}")
        
        # Create tweet content with truncation
        title = truncate_text(top_post.title)
        url = f"https://reddit.com{top_post.permalink}"
        
        # Get contextual engagement question
        question = get_engagement_question(top_post.title)
        logger.info(f"Selected engagement question: {question}")
        
        # Create tweet text with summary and question
        if summary:
            tweet_text = f"{title}\n\n{summary}\n\n{question}\n\n{url}"
        else:
            tweet_text = f"{title}\n\n{question}\n\n{url}"
            
        logger.info(f"Preparing to tweet:\n{tweet_text}")
        
        # Add a small delay to ensure we can see the output
        logger.info("\nWaiting 2 seconds before posting to Twitter...")
        time.sleep(2)
        
        # Post to Twitter using v2 API
        try:
            logger.info("\nAttempting to post to Twitter...")
            logger.info("Using Twitter credentials:")
            logger.info(f"API Key: {os.getenv('TWITTER_API_KEY')[:5]}...")
            logger.info(f"Access Token: {os.getenv('TWITTER_ACCESS_TOKEN')[:5]}...")
            
            response = client.create_tweet(
                text=tweet_text,
                user_auth=True
            )
            
            logger.info("Twitter API Response:", response)
            tweet_id = response.data['id']
            logger.info(f"Successfully posted! Tweet ID: {tweet_id}")
            
            # Save the posted thread ID
            save_posted_thread(top_post.id)
            
            logger.info(f"Successfully posted tweet ID: {tweet_id}")
            logger.info(f"Tweet content:\n{tweet_text}")
            
        except tweepy.errors.Forbidden as e:
            logger.error(f"\nTwitter API Forbidden error: {str(e)}")
            logger.error("This usually means the app doesn't have the correct permissions.")
        except tweepy.errors.Unauthorized as e:
            logger.error(f"\nTwitter API Unauthorized error: {str(e)}")
            logger.error("This usually means the credentials are incorrect.")
        except tweepy.errors.TweepyException as e:
            logger.error(f"\nTwitter API error: {str(e)}")
            
    except Exception as e:
        logger.error(f"\nGeneral error: {str(e)}")

# Add a main function to run the bot
def main():
    """Main function to run the bot."""
    try:
        post_reddit_update()
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")

if __name__ == "__main__":
    main()
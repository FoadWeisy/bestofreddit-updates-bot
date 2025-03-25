from flask import Flask, jsonify
import os
from dotenv import load_dotenv
import praw
import tweepy
import logging
from datetime import datetime
import json
import time
import schedule

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Initialize Reddit client
reddit = praw.Reddit(
    client_id=os.getenv('REDDIT_CLIENT_ID'),
    client_secret=os.getenv('REDDIT_CLIENT_SECRET'),
    user_agent=os.getenv('REDDIT_USER_AGENT', 'RedditToTwitterBot/1.0')
)

# Initialize Twitter client
twitter_client = tweepy.Client(
    consumer_key=os.getenv('TWITTER_API_KEY'),
    consumer_secret=os.getenv('TWITTER_API_SECRET_KEY'),
    access_token=os.getenv('TWITTER_ACCESS_TOKEN'),
    access_token_secret=os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
)

def load_posted_threads():
    """Load the list of previously posted thread IDs from a JSON file."""
    try:
        with open('posted_threads.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_posted_threads(thread_ids):
    """Save the list of posted thread IDs to a JSON file."""
    with open('posted_threads.json', 'w') as f:
        json.dump(thread_ids, f)

def clean_markdown(text):
    """Clean markdown formatting and metadata from text."""
    # Remove markdown formatting
    text = text.replace('**', '').replace('*', '').replace('>', '')
    
    # Split into lines and filter out metadata
    lines = text.split('\n')
    cleaned_lines = []
    skip_next = False
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Skip metadata lines
        if any(phrase in line.lower() for phrase in [
            'i am not oop', 'originally posted', 'mood spoiler',
            'trigger warning', 'content warning', 'update:', 'edit:',
            'tl;dr', 'tldr', 'editor\'s note', 'note:', 'thanks to',
            'credit to', 'posted by', 'submitted by', 'reposted from',
            'crossposted from', 'source:', 'background:', 'context:'
        ]):
            continue
            
        cleaned_lines.append(line)
    
    return ' '.join(cleaned_lines)

def get_thread_summary(post):
    """Get a summary of the thread, preferring top comment if available."""
    try:
        # Try to get top comment first
        post.comments.replace_more(limit=0)
        if post.comments:
            top_comment = post.comments[0]
            if top_comment and top_comment.body:
                cleaned_comment = clean_markdown(top_comment.body)
                if cleaned_comment:
                    return f"Top comment: {cleaned_comment}"
        
        # Fall back to post content
        if post.selftext:
            cleaned_text = clean_markdown(post.selftext)
            if cleaned_text:
                # Remove title if it appears at the start
                if cleaned_text.lower().startswith(post.title.lower()):
                    cleaned_text = cleaned_text[len(post.title):].strip()
                return f"From post: {cleaned_text}"
        
        return None
    except Exception as e:
        logger.error(f"Error getting thread summary: {str(e)}")
        return None

def get_engagement_question(title):
    """Generate a contextual engagement question based on the post title."""
    # Extract key topics from title
    topics = title.lower().split()
    
    # Define topic-specific questions
    if any(word in topics for word in ['aita', 'amita', 'wibta']):
        return "What's your verdict? 🤔"
    elif any(word in topics for word in ['relationship', 'partner', 'boyfriend', 'girlfriend', 'husband', 'wife']):
        return "Relationship advice needed! What would you do? 💭"
    elif any(word in topics for word in ['family', 'parent', 'child', 'sibling']):
        return "Family drama! What would you do? 🤔"
    elif any(word in topics for word in ['work', 'job', 'boss', 'employee']):
        return "Workplace situation! How would you handle it? 💼"
    elif any(word in topics for word in ['friend', 'friendship']):
        return "Friendship advice needed! What's your take? 🤝"
    else:
        return "What's your opinion on this? 🤔"

def truncate_text(text, max_length=280):
    """Truncate text to fit Twitter's character limit while preserving words."""
    if len(text) <= max_length:
        return text
    
    # Remove URLs and replace with placeholder
    import re
    urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text)
    for url in urls:
        text = text.replace(url, 'URL')
    
    # If still too long, truncate
    if len(text) > max_length:
        text = text[:max_length-3] + "..."
    
    # Restore URLs
    for url in urls:
        text = text.replace('URL', url)
    
    return text

def post_reddit_update():
    """Fetch and post a new Reddit update to Twitter."""
    try:
        logger.info("\n=== Starting new post update ===\n")
        
        # Load previously posted threads
        posted_threads = load_posted_threads()
        logger.info(f"\nPreviously posted {len(posted_threads)} threads")
        
        # Fetch posts from Reddit
        subreddit = reddit.subreddit('BestofRedditorUpdates')
        posts = list(subreddit.hot(limit=5))
        
        logger.info("\nTop 5 posts from r/BestofRedditorUpdates:")
        for post in posts:
            logger.info(f"- {post.title}")
            logger.info(f"  Score: {post.score}, URL: {post.url}")
            logger.info(f"  Sticky: {post.stickied}")
            logger.info(f"  Previously posted: {post.id in posted_threads}")
        
        # Find first unposted thread
        selected_post = None
        for post in posts:
            if post.id not in posted_threads and not post.stickied:
                selected_post = post
                break
        
        if not selected_post:
            logger.info("No new posts to tweet")
            return
        
        logger.info(f"\nSelected post to tweet: {selected_post.title}")
        
        # Get thread summary
        summary = get_thread_summary(selected_post)
        if summary:
            logger.info(f"Thread summary: {summary}")
        
        # Generate engagement question
        question = get_engagement_question(selected_post.title)
        logger.info(f"Selected engagement question: {question}")
        
        # Prepare tweet text
        tweet_text = f"{selected_post.title}\n\n{summary}\n\n{question}\n\n{selected_post.url}"
        tweet_text = truncate_text(tweet_text)
        
        logger.info(f"Preparing to tweet:\n{tweet_text}")
        
        # Wait before posting
        logger.info("\nWaiting 2 seconds before posting to Twitter...")
        time.sleep(2)
        
        # Post to Twitter
        logger.info("\nAttempting to post to Twitter...")
        logger.info("Using Twitter credentials:")
        logger.info(f"API Key: {os.getenv('TWITTER_API_KEY')[:6]}...")
        logger.info(f"Access Token: {os.getenv('TWITTER_ACCESS_TOKEN')[:6]}...")
        
        try:
            response = twitter_client.create_tweet(text=tweet_text)
            logger.info("\nTwitter API Response:", response)
            logger.info(f"Successfully posted! Tweet ID: {response.data['id']}")
            
            # Save posted thread ID
            posted_threads.append(selected_post.id)
            save_posted_threads(posted_threads)
            logger.info(f"Successfully posted tweet ID: {response.data['id']}")
            logger.info(f"Tweet content:\n{tweet_text}")
            
        except Exception as e:
            logger.error(f"Error posting to Twitter: {str(e)}")
            raise
        
    except Exception as e:
        logger.error(f"Error in post_reddit_update: {str(e)}")
        raise

@app.route('/')
def home():
    """Home route that shows the app is running."""
    return jsonify({
        "status": "running",
        "last_update": datetime.now().isoformat()
    })

@app.route('/trigger-update')
def trigger_update():
    """Endpoint to manually trigger a Reddit update."""
    try:
        post_reddit_update()
        return jsonify({
            "status": "success",
            "message": "Update completed successfully"
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

def run_scheduler():
    """Run the scheduler to post updates periodically."""
    schedule.every(15).minutes.do(post_reddit_update)
    
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == '__main__':
    # Start the scheduler in a separate thread
    import threading
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    # Get port from environment variable or use default
    port = int(os.getenv('PORT', 5000))
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=port) 
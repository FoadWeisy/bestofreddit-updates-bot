import os
from dotenv import load_dotenv
import tweepy

# Load environment variables
load_dotenv()

# Print configuration
print("Checking Twitter API credentials:")
print(f"API Key: {os.getenv('TWITTER_API_KEY')[:5]}...")
print(f"API Secret: {os.getenv('TWITTER_API_SECRET')[:5]}...")
print(f"Access Token: {os.getenv('TWITTER_ACCESS_TOKEN')[:5]}...")
print(f"Access Token Secret: {os.getenv('TWITTER_ACCESS_TOKEN_SECRET')[:5]}...")

try:
    # Twitter API v2 setup
    client = tweepy.Client(
        bearer_token=None,
        consumer_key=os.getenv('TWITTER_API_KEY'),
        consumer_secret=os.getenv('TWITTER_API_SECRET'),
        access_token=os.getenv('TWITTER_ACCESS_TOKEN'),
        access_token_secret=os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
    )
    
    print("\nTrying to post a test tweet...")
    response = client.create_tweet(
        text="Test tweet from Reddit Bot",
        user_auth=True
    )
    print(f"Success! Tweet ID: {response.data['id']}")
    
except Exception as e:
    print(f"Error: {str(e)}") 
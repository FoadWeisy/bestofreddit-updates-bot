import os
from dotenv import load_dotenv
import tweepy

def main():
    print("Starting Twitter API test...")
    
    # Load environment variables
    load_dotenv()
    
    # Get credentials
    api_key = os.getenv('TWITTER_API_KEY')
    api_secret = os.getenv('TWITTER_API_SECRET')
    access_token = os.getenv('TWITTER_ACCESS_TOKEN')
    access_token_secret = os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
    
    print("\nChecking credentials:")
    print(f"API Key: {api_key[:5]}...")
    print(f"API Secret: {api_secret[:5]}...")
    print(f"Access Token: {access_token[:5]}...")
    print(f"Access Token Secret: {access_token_secret[:5]}...")
    
    try:
        print("\nCreating Twitter client...")
        client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        
        print("Attempting to post test tweet...")
        response = client.create_tweet(text="Test tweet from Reddit Bot")
        print(f"Success! Tweet ID: {response.data['id']}")
        
    except tweepy.errors.Forbidden as e:
        print(f"\nForbidden Error: {str(e)}")
        print("This usually means the app doesn't have the correct permissions.")
    except tweepy.errors.Unauthorized as e:
        print(f"\nUnauthorized Error: {str(e)}")
        print("This usually means the credentials are incorrect.")
    except tweepy.errors.TweepyException as e:
        print(f"\nTweepy Error: {str(e)}")
    except Exception as e:
        print(f"\nUnexpected Error: {str(e)}")

if __name__ == "__main__":
    main() 
# Best of Reddit Updates Bot

A Twitter bot that automatically posts top stories from r/BestofRedditorUpdates to Twitter.

## Features

- Fetches top posts from r/BestofRedditorUpdates
- Skips pinned/stickied posts
- Includes a brief summary from the thread comments
- Never posts the same thread twice
- Detailed logging of all operations

## Setup

1. Clone this repository
2. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file with your API credentials:
   ```
   # Twitter API Credentials
   TWITTER_API_KEY=your_api_key
   TWITTER_API_SECRET=your_api_secret
   TWITTER_ACCESS_TOKEN=your_access_token
   TWITTER_ACCESS_TOKEN_SECRET=your_access_token_secret

   # Reddit API Credentials
   REDDIT_CLIENT_ID=your_client_id
   REDDIT_CLIENT_SECRET=your_client_secret
   REDDIT_USER_AGENT=python:bestofreddit-updates-bot:v1.0
   ```

## Usage

Run the bot once:
```bash
python reddit_to_twitter_bot.py
```

## Requirements

See `requirements.txt` for a list of required packages. 
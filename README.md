# Reddit to Twitter Bot

A Python bot that automatically posts top posts from r/BestofRedditorUpdates to Twitter/X.

## Features

- Fetches top posts from r/BestofRedditorUpdates
- Generates contextual engagement questions
- Includes post summaries and top comments
- Runs on a schedule (every 15 minutes)
- Web interface for manual triggering
- Secure API key management

## Local Development

1. Clone the repository:
```bash
git clone https://github.com/yourusername/reddit-to-twitter-bot.git
cd reddit-to-twitter-bot
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file with your API keys:
```
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_client_secret
REDDIT_USER_AGENT=your_user_agent
TWITTER_API_KEY=your_twitter_api_key
TWITTER_API_SECRET_KEY=your_twitter_api_secret
TWITTER_ACCESS_TOKEN=your_twitter_access_token
TWITTER_ACCESS_TOKEN_SECRET=your_twitter_access_token_secret
```

5. Run the application:
```bash
python app.py
```

## Heroku Deployment

1. Install the Heroku CLI and login:
```bash
heroku login
```

2. Create a new Heroku app:
```bash
heroku create your-app-name
```

3. Set up environment variables in Heroku:
```bash
heroku config:set REDDIT_CLIENT_ID=your_reddit_client_id
heroku config:set REDDIT_CLIENT_SECRET=your_reddit_client_secret
heroku config:set REDDIT_USER_AGENT=your_user_agent
heroku config:set TWITTER_API_KEY=your_twitter_api_key
heroku config:set TWITTER_API_SECRET_KEY=your_twitter_api_secret
heroku config:set TWITTER_ACCESS_TOKEN=your_twitter_access_token
heroku config:set TWITTER_ACCESS_TOKEN_SECRET=your_twitter_access_token_secret
```

4. Deploy to Heroku:
```bash
git push heroku master
```

5. Add Heroku Scheduler add-on:
```bash
heroku addons:create scheduler:standard
```

6. Configure the scheduler:
- Go to https://dashboard.heroku.com/apps/your-app-name/scheduler
- Add a new job: `curl https://your-app-name.herokuapp.com/trigger-update`
- Set the frequency to "Every 15 minutes"

## Monitoring

- View logs: `heroku logs --tail`
- Check app status: `heroku ps`
- Monitor dyno usage: `heroku metrics:web`

## API Endpoints

- `GET /`: Health check endpoint
- `GET /trigger-update`: Manually trigger a Reddit update

## Error Handling

The application includes comprehensive error handling and logging:
- All API calls are wrapped in try-catch blocks
- Errors are logged with detailed information
- Failed operations are reported via the API endpoints
- Heroku logs capture all application output

## Security

- API keys are stored securely in Heroku Config Vars
- No sensitive information is committed to the repository
- Environment variables are loaded securely using python-dotenv
- HTTPS is enforced on all endpoints

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 
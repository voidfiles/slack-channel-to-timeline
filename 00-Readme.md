# Extract Slack Conversations

This is a tool meant for incident analysis.


## Start by visiting your slack community in a browser

https://[my-slack-community].slack.com

Once you are logged in, you are going to get a cookie. It's secure so, you can't access it from javascript console.

1. In chrome, open developer tools 
2. Navigate to the Application tab 
3. Look for cookies in the left rail
4. open app.slack.com
5. In filter type xoxd
6. You should see a cookie called d, the value of that cookie is what you want.

Grab the cookie value, now we are going to get a token.

visit https://[my-slack-community].slack.com/customize/emoji

in the console, put `boot_data.api_token` grab the output there.


## Setup

`make setup`

```
brew install python3
python3 -m ensurepip --upgrade
pip install virtualenv
virtualenv SlackExtract
source SlackExtract/bin/activate
pip install -r requirements.txt
```

Check if it worked `python3 slack.py --help`

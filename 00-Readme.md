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

1. visit https://[my-slack-community].slack.com/customize/emoji
2. Open developer tools 
3. In the console put `boot_data.api_token`
4. Grab that token

Now, clone this gist locally, and run setup.

## Setup

This was built for macs, with [homebrew](https://brew.sh/) already installed.

`make setup`

Now, create a file called .env and add the data you collected.

```
SLACK_COOKIE={Add the cookie value here (w/o {}, or quotes)}
SLACK_TOKEN={Add the token value here (w/o {}, or quotes)}
```

## Test your setup

Run `make test`, it will let you know if you have everything setup correctly.

## Extracting a Channel

Find the channel you'd like to extract and run this command.

`CHANNEL_ID=CFQLH5U2C make channel`

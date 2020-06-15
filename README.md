# Globus Newsie slack app


You need sam and awscli installed (just run `pip install -r requirements.txt`).

Then you can run `sam build; sam deploy --guided` and just follow the prompts.

## GitHub

The **App ID** is 67866.
Go here and install [globus-newsie](https://github.com/apps/globus-newsie). 
Then note the **Install ID** which is at the end of the url of the configure page: https://github.com/settings/installations/**9548427**.

You'll need to set as an env variable

```
GH_APP_ID = 67866
GH_APP_INSTALL_ID = .....
```

Get the .pem from Max and put it at 

`src/globus-newsie.2020-06-06.private-key.pem`

## Slack

Go here to install the app

https://slack.com/oauth/v2/authorize?client_id=1162218566662.1167573384725&scope=chat:write,app_mentions:read,channels:history,commands&user_scope=

Get the `SLACK_SIGNING_SECRET` from Max and set it as an env variable as well.
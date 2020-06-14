import base64
import datetime
import hashlib
import hmac
import os
import re
from urllib import parse

import github3
import requests

GH_APP_PEM_FP = os.environ["GH_APP_PEM_FP"]
GH_APP_ID = int(os.environ["GH_APP_ID"])
GH_APP_INSTALL_ID = int(os.environ["GH_APP_INSTALL_ID"])

with open(GH_APP_PEM_FP, "rb") as pem_file:
    KEY_FILE_PEM = pem_file.read()

GH_CLIENT = github3.GitHub()

SLACK_SIGNING_SECRET = bytes(os.environ["SLACK_SIGNING_SECRET"], "utf-8")


def verify_slack_signature(slack_post_request):
    slack_signature = slack_post_request["headers"]["X-Slack-Signature"]
    slack_request_timestamp = slack_post_request["headers"]["X-Slack-Request-Timestamp"]
    request_body = slack_post_request["body"]

    basestring = f"v0:{slack_request_timestamp}:{request_body}".encode("utf-8")
    my_signature = (
        "v0=" + hmac.new(SLACK_SIGNING_SECRET, basestring, hashlib.sha256).hexdigest()
    )

    return hmac.compare_digest(my_signature, slack_signature)


def lambda_handler(event, context):
    if not verify_slack_signature(event):
        return {"statusCode": 400, "body": ""}

    slack_message = parse.parse_qs(event["body"])
    res = post_news(slack_message["text"][0], slack_message["user_name"][0])
    return {"statusCode": 200, "body": res}


with open("post_template.md") as f:
    POST_TEMPLATE_STR = f.read()

POSSIBLE_TYPES = {"paper", "award", "presentation", "join"}


def post_news(slack_text, slack_user):
    try:
        match = re.search(
            r"\s*title:\s*(?P<title>.*)type:\s*(?P<type>.*)text:\s*(?P<text>.*)",
            slack_text,
        )
        if not match.groups():
            return f"sorry you're missing something; i didn't get anything from you"
        title, text, type = (
            match.group("title").strip(),
            match.group("text").strip(),
            match.group("type").strip(),
        )
        if not title or not text or not type or not type in POSSIBLE_TYPES:
            return f"sorry you're missing something; here's what i got from you: title:{title} text:{text} type:{type}"

        GH_CLIENT.login_as_app_installation(
            private_key_pem=KEY_FILE_PEM,
            app_id=GH_APP_ID,
            installation_id=GH_APP_INSTALL_ID,
        )
        access_token = GH_CLIENT.session.auth.token

        today = datetime.datetime.today()
        post = POST_TEMPLATE_STR.format(
            title=title, date=str(today), type=type, text=text
        )
        post = base64.b64encode(bytes(post, "utf-8")).decode("utf-8")
        path = f"https://api.github.com/repos/makslevental/aliza_bot/contents/{today.date()}-{'-'.join(title.split())}.markdown"
        response = requests.put(
            path,
            headers={
                "Authorization": "token " + access_token,
                "Accept": "application/vnd.github.machine-man-preview+json",
            },
            json={
                "message": f"news posted",
                "committer": {"name": slack_user, "email": f"{slack_user}@globus.org"},
                "content": post,
            },
        )
        if response.status_code != 201:
            return f"something went wrong: {response.json()['message']}"
        else:
            return f"news posted @ {path.replace('api.', '').replace('repos/', '').replace('contents', 'blob/master')}"
    except Exception as e:
        return f"exception: {e}"


if __name__ == "__main__":
    print(post_news("title: asd fsdf a df a d f type: paper text: 343gdghdfkjgh", "ax"))

import base64
import datetime
import hashlib
import hmac
import os
import re
from urllib import parse

import github3
import requests

GH_APP_PEM_FP = "./globus-newsie.2020-06-06.private-key.pem"
GH_REPO = os.environ["GH_REPO"]
GH_POST_PATH = "_posts"
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

GH_CLIENT.login_as_app_installation(
    private_key_pem=KEY_FILE_PEM, app_id=GH_APP_ID, installation_id=GH_APP_INSTALL_ID
)
ACCESS_TOKEN = GH_CLIENT.session.auth.token


def get_posts():
    path = f"https://api.github.com/repos/{GH_REPO}/contents/{GH_POST_PATH}/"
    response = requests.get(
        path,
        headers={
            "Authorization": "token " + ACCESS_TOKEN,
            "Accept": "application/vnd.github.machine-man-preview+json",
        },
    )
    if response.status_code != 200:
        return []
    return [f for f in response.json() if "markdown" in f["name"]]


def find_post(title):
    posts = get_posts()
    return [p for p in posts if "-".join(title.split()) in p["name"]]


def post_news(slack_text, slack_user):
    try:
        if "warmup" in slack_text:
            return "warmed up"

        match = re.search(
            r"(?:delete)?"
            r"(?:warmup)?"
            r"(?:title:(?P<title>.*?))"
            r"((?:type:(?P<type>.*?))?(?:text:(?P<text>.*?))?$|$)",
            slack_text,
        )
        if not match.groups():
            return f"sorry you're missing something; i didn't get anything from you"

        title, text, type = (
            match.group("title"),
            match.group("text"),
            match.group("type"),
        )
        delete = "delete" in slack_text

        if delete and not title:
            return "you need `title` if you want to delete"
        elif (
            not delete and not (title and text and type) and type not in POSSIBLE_TYPES
        ):
            return f"sorry you're missing something; here's what i got from you: title:{title} text:{text} type:{type}"

        today = datetime.datetime.today()
        found_post = find_post(title)
        if found_post:
            path = found_post[0]["url"]
            sha = found_post[0]["sha"]
        else:
            path = f"https://api.github.com/repos/{GH_REPO}/contents/{GH_POST_PATH}/{today.date()}-{'-'.join(title.split())}.markdown"
            sha = ""
        post = POST_TEMPLATE_STR.format(
            title=title, date=str(today), type=type, text=text
        )
        post_encoded = base64.b64encode(bytes(post, "utf-8")).decode("utf-8")
        post_json = {
            "message": f"news updated",
            "committer": {"name": slack_user, "email": f"{slack_user}@globus.org"},
            "content": post_encoded,
            "sha": sha,
        }
        headers = {
            "Authorization": "token " + ACCESS_TOKEN,
            "Accept": "application/vnd.github.machine-man-preview+json",
        }

        if delete:
            response = requests.delete(path, headers=headers, json=post_json)
        else:
            response = requests.put(path, headers=headers, json=post_json)

        if response.status_code not in {200, 201}:
            return f"something went wrong: {response.json()['message']}"
        else:
            if delete:
                return "post deleted"
            else:
                return f"news posted @ {response.json()['content']['html_url']}. if you want to update then use the same title"
    except Exception as e:
        return f"exception: {e}"


if __name__ == "__main__":
    # print(
    #     post_news(
    #         "title: asd   fsd  sasdasd  sadfsd fsd f a df a d f type: paper text: upd ated2 sha: 62e7a8252c687e1c1d953e8773b4a3f361dd7ae1",
    #         "ax",
    #     )
    # )
    print(post_news("delete title: will it work", "ax"))
    # print(
    #     post_news("title: will it work type: paper text: gsjksf  update hgkjfdhg", "ax")
    # )

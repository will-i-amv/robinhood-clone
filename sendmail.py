# Imports
import os
import requests


def send_mail(email: str, subject: str, body: str) -> None:
    """Sends mail for resetting password to the user

    Args:
        path: Database path
        email: User email id

    Returns:
        None
    """
    MAILGUN_EMAIL = os.getenv("MAILGUN_EMAIL")
    MAILGUN_PASSWD = os.getenv("MAILGUN_PASSWD")

    try:
        requests.post(
            f"https://api.mailgun.net/v3/{MAILGUN_EMAIL}.mailgun.org/messages",
            data={
                "from": f"Mailgun Sandbox <postmaster@{MAILGUN_EMAIL}.mailgun.org>",
                "to": email,
                "subject": subject,
                "text": body,
            },
            auth=("api", MAILGUN_PASSWD),
        )
    except:
        print("Error Sending Mail")

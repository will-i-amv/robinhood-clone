import os

import pynance as pn
import requests
import yfinance as yf


class Currency_Conversion:
    """
    API Class for currency conversion
    """

    rates = {}

    def __init__(self, url):
        data = requests.get(url).json()
        self.rates = data["rates"]

    def convert(self, from_currency, to_currency, amount) -> float:
        """Converts one currency to another

        Args:
            from_currency: Currency to be converted from
            to_cuurency: Currency to be converted to
            amount: amount to be converted

        Returns:
            float: Converted amount
        """
        initial_amount = amount
        if from_currency != "EUR":
            amount = amount / self.rates[from_currency]

        amount = round(amount * self.rates[to_currency], 2)
        return amount


def get_current_price(symbol: str) -> float:
    """Gets current closing price of stock using Ticker method

    Args:
        symbol: Stock Symbol

    Returns:
        float: Closing Stock price
    """
    ticker = yf.Ticker(symbol)
    todays_data = ticker.history(period="1d")
    return float(todays_data["Close"][0])


def get_current_stock_price(symbol: str) -> float:
    """Gets current closing price of stock
    (Substitute for init function error)

    Args:
        symbol: Stock Symbol

    Returns:
        float: Closing Stock price
    """
    data = pn.data.get(symbol, start=None, end=None)
    return float(data["Close"][0])


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

# Imports
import datetime as dt
import glob
import json
import os
import random
from pathlib import Path

import pandas as pd
import requests
import yfinance as yf
from dotenv import load_dotenv
from flask import Flask, g, redirect, render_template, request, session, url_for

from models import contactus, stock, users
from utils import Currency_Conversion, get_current_stock_price, send_mail


# Import environment variables
load_dotenv()
RAZORPAY_ID = os.getenv("RAZORPAY_ID")
RAZORPAY_PASSWD = os.getenv("RAZORPAY_PASSWD")

# Initialize Payment Session
request_payment = requests.Session()
request_payment.auth = (RAZORPAY_ID, RAZORPAY_PASSWD)
payment_data = json.load(open("payment_data.json"))

# App configuration
app = Flask(__name__, template_folder=os.path.abspath("./templates"))
app.secret_key = "somekey"
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

# Create tables
DB_PATH = "app.db"
users.create_table(DB_PATH)
contactus.create_table(DB_PATH)
stock.create_table(DB_PATH)

# List of stock symbols from URL containing NASDAQ listings
url = (
    "https://pkgstore.datahub.io/core/nasdaq-listings/nasdaq-listed_csv/" + 
    "data/7665719fb51081ba0bd834fde71ce822/nasdaq-listed_csv.csv"
)
STOCK_SYMBOLS = (
    pd
    .read_csv(url)
    .loc[:, "Symbol"]
    .to_list()
)


@app.before_request
def security():
    """
    Sets current user (g.user) to none and checks if the user is in session
    If in session then email is fetched and g.user is updated to that email
    """
    g.user = None
    if "user_email" in session:
        emails = users.getemail(DB_PATH)
        try:
            useremail = [
                email for email in emails if email[0] == session["user_email"]
            ][0]
            g.user = useremail
        except Exception as e:
            print("Failed")


@app.route("/", methods=["GET", "POST"])
def home():
    return redirect("/login")


@app.route("/login", methods=["GET", "POST"])
def login():
    session.clear()
    if not request.method == "POST":
        return render_template("login.html")
    else:
        email = request.form.get('email', '')
        password = request.form.get('password', '')
        if not email:
            return render_template(
                    "login.html", 
                    error="You must provide email"
                )
        elif not password:
            return render_template(
                    "login.html", 
                    error="You must provide password"
                )
        elif not users.check_user_exist(DB_PATH, email):
            return render_template(
                "login.html", 
                error="User does not exist"
            )
        elif not users.check_hash(DB_PATH, password, email):
            return render_template(
                "login.html", 
                error="Password incorrect"
            )
        else:
            session["user_email"] = email
            return redirect("/index")


@app.route("/register", methods=["GET", "POST"])
def register():
    if not request.method == "POST":
        return render_template("register.html")
    else:
        name = request.form.get('name', '')
        email = request.form.get('email', '')
        password = request.form.get('password', '')
        repeat_password = request.form.get('rpassword', '')
        if not name:
            return render_template(
                    "register.html", 
                    error="You must provide name"
                )
        if not email:
            return render_template(
                    "register.html", 
                    error="You must provide email"
                )
        elif not password:
            return render_template(
                    "register.html", 
                    error="You must provide password"
                )
        elif password != repeat_password:
            return render_template(
                "register.html", 
                error="The passwords do not match"
            )
        elif users.check_user_exist(DB_PATH, email):
            return render_template(
                "register.html", 
                error="The user already exists"
            )
        else:
            password = users.hash_pwd(password)
            users.insert(DB_PATH, "user", (email, name, password, 0))
            session["user_email"] = email
            return redirect("/index")


@app.route("/recovery", methods=["GET", "POST"])
def recovery():
    if not request.method == "POST":
        return render_template("recovery.html")
    else:
        email = request.form.get('email', '')
        if not users.check_user_exist(DB_PATH, email):
            return render_template(
                "recovery.html", 
                error="The email does not exist."
            )
        else:
            code = str(random.randint(1000, 9999))
            subject = "RESET YOUR PASSWORD"
            body = (
                f"""
                Dear User,

                Please Click on the Link Below to reset your password for your {email} account.

                This is your 4 Digit Verification Code: {code}

                Link: http://localhost:8000/reset

                If you didn't ask to reset your password please ignore this email.

                Thank you.

                Best Regards.
                """
                .replace('  ', '')
            )
            users.add_code(DB_PATH, code, email)
            send_mail(email, subject, body)
            
            return render_template(
                "recovery.html",
                error="We have sent you a link to reset your password. Check your mailbox",
            )


@app.route("/reset", methods=["GET", "POST"])
def reset():
    """
    Reset Password Page
    """
    if not request.method == "POST":
        return render_template("reset.html")
    else:
        passwd = request.form["npassword"]
        repeat_passwd = request.form["rnpassword"]
        ver_code = str(request.form["vcode"])

        if passwd != repeat_passwd:
            return render_template(
                "reset.html", 
                error="The passwords do not match"
            )
        elif not users.check_code(DB_PATH, ver_code):
            return render_template(
                "reset.html", 
                error="Incorrect verification code"
            )
        else:
            passwd = users.hash_pwd(passwd)
            users.reset_pwd(DB_PATH, passwd, ver_code)
            users.reset_code(DB_PATH, ver_code)
            return redirect("/")


@app.route("/index", methods=["GET", "POST"])
def index():
    """
    Home Page
    """
    if g.user:
        return render_template("index.html")
    return redirect("/")


@app.route("/inv", methods=["GET", "POST"])
def inv():
    """
    Analysis Page - displays historical stock data
    """
    if g.user:
        if request.method == "POST":
            stock_id = request.form["stocksym"]
            stock_id = stock_id.upper()

            if stock_id in STOCK_SYMBOLS:
                df_stock = yf.download(stock_id, start="1950-01-01", period="1d")

            else:
                return render_template(
                    "inv.html",
                    error="Incorrect Stock Symbol. Please Enter Valid Symbol",
                )

            df_stock.drop("Adj Close", axis="columns", inplace=True)
            df_stock.reset_index(inplace=True)
            df_stock["Date"] = pd.to_datetime(df_stock["Date"])
            df_stock["Date"] = (
                df_stock["Date"] - dt.datetime(1970, 1, 1)
            ).dt.total_seconds()
            df_stock["Date"] = df_stock["Date"] * 1000

            files = glob.glob(
                "/home/nvombat/Desktop/Investment-WebApp/analysis/data/*_mod.json"
            )

            if len(files) != 0:
                file_rem = Path(files[0]).name
                location = "/home/nvombat/Desktop/Investment-WebApp/analysis/data/"
                os.remove(os.path.join(location, file_rem))

            df_stock.to_json(
                "/home/nvombat/Desktop/Investment-WebApp/analysis/data/"
                + stock_id
                + "_mod.json",
                orient="values",
            )
            return render_template("inv.html", name=stock_id)

        return render_template("inv.html")
    return redirect("/")


@app.route("/trade", methods=["GET", "POST"])
def trade():
    """
    Trade Page - Buy, Sell & View the price of stocks
    """
    if g.user:
        user_email = g.user
        transactions = stock.query(user_email[0], DB_PATH)

        if request.method == "POST":
            url = str.__add__(
                "http://data.fixer.io/api/latest?access_key=",
                os.getenv("FIXER_API_KEY"),
            )
            c = Currency_Conversion(url)
            from_country = "USD"
            to_country = "INR"

            # BUYING
            if request.form.get("b1"):
                symb = request.form["stockid"]
                quant = request.form["amount"]

                symb = symb.upper()
                if symb in STOCK_SYMBOLS:
                    date = dt.datetime.now()
                    date = date.strftime("%m/%d/%Y, %H:%M:%S")

                    quant = int(quant)
                    stock_price = get_current_stock_price(symb)
                    total = quant * stock_price

                    stock_price = "{:.2f}".format(stock_price)
                    total = "{:.2f}".format(total)

                    stock_price_rupees = c.convert(
                        from_country, to_country, stock_price
                    )
                    stock_price_int = int(stock_price_rupees)
                    stock_price_int *= 100

                    # ref_id = binascii.b2a_hex(os.urandom(20))
                    # payment_data["amount"] = stock_price_int
                    # payment_data["reference_id"] = ref_id.decode()
                    # payment_data["customer"]["name"] = users.getname(DB_PATH, g.user)
                    # payment_data["customer"]["email"] = user_email[0]

                    # payment_link_init = request_payment.post(
                    #     "https://api.razorpay.com/v1/payment_links/",
                    #     headers={"Content-Type": "application/json"},
                    #     data=json.dumps(payment_data),
                    # ).json()
                    # payment_link = payment_link_init["short_url"]

                    # return redirect(payment_link, code=303)

                    stock.buy(
                        "stock", (date, symb, stock_price, quant, user_email[0]), DB_PATH
                    )

                    subject = "Stock Transaction Receipt: BUY"
                    body = (
                        f"""
                        Dear User,
                        
                        Here is your transaction receipt for your {user_email[0]} account.
                        
                        You bought {quant} units of the {symb} stock on {date} 
                        at a rate of $ {price} per stock unit. Your total expenditure was $ {total}. 
                            
                        Thank you.
                        
                        Best Regards.
                        """
                        .replace('  ', '')

                    )
                    send_mail(user_email[0], subject, body)

                    return redirect(url_for("trade"))

                else:
                    return render_template(
                        "trade.html",
                        error="Incorrect Stock Symbol. Please Enter Valid Symbol",
                        transactions=transactions,
                    )

            # SELLING
            elif request.form.get("s1"):
                symb = request.form["stockid"]
                quant = request.form["amount"]
                symb = symb.upper()

                if symb in STOCK_SYMBOLS:
                    quant = int(quant)
                    stock_price = get_current_stock_price(symb)
                    total = quant * stock_price
                    stock_price = "{:.2f}".format(stock_price)
                    total = "{:.2f}".format(total)

                    date = dt.datetime.now()
                    date = date.strftime("%m/%d/%Y, %H:%M:%S")
                    data = (symb, quant, user_email[0], stock_price)

                    if stock.sell("stock", data, DB_PATH):
                        subject = "Stock Transaction Receipt: SELL"
                        body = (
                            f"""
                            Dear User,
                            
                            Here is your transaction receipt for your {user_email[0]} account.
                            
                            You sold {quant} units of the {symb} stock on {date} 
                            at a rate of $ {price} per stock unit. Your total earning was $ {total}. 
                                
                            Thank you.
                            
                            Best Regards.
                            """
                            .replace('  ', '')
                        )
                        send_mail(user_email[0], subject, body)

                    else:
                        return render_template(
                            "trade.html",
                            error="You either DO NOT own this stock or are trying to sell more than you own! Please check again!",
                            transactions=transactions,
                        )

                else:
                    return render_template(
                        "trade.html",
                        error="Incorrect Stock Symbol. Please Enter Valid Symbol",
                        transactions=transactions,
                    )

            # FIND PRICE
            elif request.form.get("p1"):
                sym = request.form["stockid"]
                quant = request.form["amount"]
                sym = sym.upper()

                if sym in STOCK_SYMBOLS:
                    quant = int(quant)
                    price = get_current_stock_price(sym)
                    price = float(price)

                    total = quant * price
                    price = "{:.2f}".format(price)
                    total = "{:.2f}".format(total)

                    quant = str(quant)
                    price = str(price)
                    total = str(total)

                    err_str = (
                        "The price for "
                        + quant
                        + " unit(s) of "
                        + sym
                        + " Stock is $ "
                        + total
                        + " at $ "
                        + price
                        + " per unit"
                    )

                    return render_template(
                        "trade.html", transactions=transactions, error=err_str
                    )

                else:
                    return render_template(
                        "trade.html",
                        error="Incorrect Stock Symbol. Please Enter Valid Symbol",
                        transactions=transactions,
                    )

        return render_template("trade.html", transactions=transactions)
    return redirect("/")


@app.route("/about")
def about():
    """
    About Us Page
    """
    if g.user:
        return render_template("about.html")
    return redirect("/")


@app.route("/doc")
def doc():
    """
    Trading Guide Page
    """
    if g.user:
        return render_template("doc.html")
    return redirect("/")


@app.route("/contact", methods=["GET", "POST"])
def contact():
    """
    Contact Us Page
    """
    if g.user:
        if request.method == "POST":
            email = request.form["email"]
            msg = request.form["message"]

            user_email = g.user
            curr_user = user_email[0]

            if users.check_contact_us(DB_PATH, email, curr_user):
                contactus.insert(email, msg, DB_PATH)
                return render_template(
                    "contact.html", error="Thank you, We will get back to you shortly"
                )

            else:
                return render_template("contact.html", error="Incorrect Email!")

        return render_template("contact.html")
    return redirect("/")


@app.route("/pipe", methods=["GET", "POST"])
def pipe():
    """
    Analysis Substitute Page
    """
    files = glob.glob(
        "/home/nvombat/Desktop/Investment-WebApp/analysis/data/*_mod.json"
    )
    if len(files) == 0:
        with open(
            "/home/nvombat/Desktop/Investment-WebApp/analysis/data/AAPL.json"
        ) as f:
            r = json.load(f)
            return {"res": r}
    else:
        with open(files[0]) as f:
            r = json.load(f)
            return {"res": r}


if __name__ == "__main__":
    app.run(debug=True, port=8000)

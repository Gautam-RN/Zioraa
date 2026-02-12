from django.shortcuts import render
from flask import Blueprint, request, render_template, redirect, session
from cashfree_pg.api_client import Cashfree
from dotenv import load_dotenv
import os
import time
import mysql.connector as sql

#load_dotenv()



Cashfree.XClientId = "CF10767318D5TGUSB28GPS73D9KPK0"
Cashfree.XClientSecret = "cfsk_ma_test_fd767d6f2eb6b761473ed5a165258a05_915bd019"
Cashfree.XEnvironment = Cashfree.SANDBOX

# 🔥 FORCE STRING
Cashfree.XApiVersion = "2023-08-01"

# Initialize Cashfree
""" Cashfree.XClientId = os.getenv("CASHFREE_APP_ID")
Cashfree.XClientSecret = os.getenv("CASHFREE_SECRET_KEY")
Cashfree.XEnvironment = Cashfree.SANDBOX
Cashfree.XApiVersion = os.getenv("CASHFREE_API_VERSION", "2023-08-01") """

payment = Blueprint("payment", __name__)

# ---------- HELPERS ----------
def login_required():
    return 'uid' in session

from db import get_db
db,cur=get_db()

# ---------- Checkout -------------
@payment.route("/checkout/")
def checkout():
    # Always get pid as list
    pids = request.args.getlist("pid")

    # Fallback if someone sent ?pid=5
    if not pids:
        pid = request.args.get("pid")
        if pid:
            pids = [pid]
    product=[]
    try:
        print(pids)
        for i in pids:
            cur.execute("Select prodname,price,offer from products where pid=%s",(i,))
            data=cur.fetchone()
            pri=float(data[1])-(float(data[2])*float(data[1]))
            product.append((data[0],pri))
        cur.execute("Select username,phone,address from users where uid=%s",(session['uid'],))
        data=cur.fetchone()
        co={"user":data,"product":product}
        total = sum(p[1] for p in co["product"])
    except Exception as e:
        return render_template("404.html",code=404,title="Page Not Founf",message=getattr(e, "description", "Something went wrong.."),e=e)
    finally:
        return render_template("checkout.html", data=co,total=total)

# ---------- ONLINE PAYMENT ----------
@payment.route("/payment/create", methods=["POST"])
def create_payment():
    """
    Creates an order in Cashfree and redirects to payment link
    """
    try:
        order_id = "ZI" + str(int(time.time()))
        amount = request.form.get("amount")
        phone = request.form.get("phone")

        if not amount or not phone:
            return render_template("404.html"), 400

        data = {
            "order_id": order_id,
            "order_amount": float(amount),
            "order_currency": "INR",
            "customer_details": {
                "customer_id": "cust001",
                "customer_phone": phone
            },
            "order_meta": {
                "return_url": f"http://localhost:5000/payment/status/{order_id}"
            }
        }

        response = Cashfree().PGCreateOrder(x_api_version="2023-08-01",create_order_request=data)
        return redirect(response.data["payment_link"])

    except Exception as e:
        print("Payment Error:", e)
        return render_template("404.html",code=500,title="Internal Server Error",message=getattr(e, "description", "Something went wrong on our end."),e=e), 500


@payment.route("/payment/status/<order_id>")
def payment_status(order_id):
    """
    Fetches payment status from Cashfree
    """
    try:
        res = Cashfree().PGFetchOrder(order_id)
        if res.data.get("order_status") == "PAID":
            return render_template("success.html")
        else:
            return render_template("failed.html")
    except Exception as e:
        print("Payment status error:", e)
        return render_template("404.html"), 500

# ---------- CASH ON DELIVERY ----------
@payment.route("/order/cod", methods=["POST"])
def cod_order():
    """
    Handles COD orders (just returns success for now)
    """
    # TODO: Save order to DB in future
    return render_template("success.html")

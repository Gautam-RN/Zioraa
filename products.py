from flask import Blueprint, render_template, render_template_string, redirect, url_for, session, abort
from db import get_db

products = Blueprint("products", __name__)

# ---------- HELPERS ----------
def login_required():
    return 'uid' in session

def alert(msg):
    return render_template_string(
        f"<script>alert('{msg}');history.back()</script>"
    )


def get_prod():
    db, cur = get_db()
    if not cur:
        return render_template("404.html"), 500
    try:
        cur.execute("SELECT * FROM products ORDER BY sold")
        rows = cur.fetchall()
        if not rows:
            abort(404)

        heading = (
        "pid","prodname","decrp","stock",
        "price","offer","sold","supplier",
        "ctgy","collection"
        )

        prods = []
        for row in rows:
            prod = dict(zip(heading, row))
            prod["prodname"] = prod["prodname"].title()

            cur.execute("SELECT link FROM images WHERE pid=%s", (prod["pid"],))
            data=cur.fetchall()
            if data:
                imgs = cur.fetchall()
            else:
                imgs = (("black.png",))
            l=[]
            for i in imgs:
                t="images/" + str(i)
                l.append(t)
            prod["images"] = l

            cur.execute("Select sum(star),count(*) from review where pid=%s", (prod["pid"],))
            prod['rating']=0
            s,n=cur.fetchone()
            if s is not None or n!=0:
                prod['rating']=round(s/n)
            prods.append(prod)
    finally:
        db.close()
    return prods


# ---------- HOME ----------
@products.route('/')
def home():
    data=get_prod()
    if data:
        return render_template("home.html", products=data[:3])
    else:
        return render_template("home.html", products=None)
    
# ---------- STORE ----------
@products.route('/store')
def store():
    db, cur = get_db()
    if not cur:
        return render_template("404.html"), 500

    try:
        cur.execute("SELECT Distinct catgy FROM products WHERE stock > 0")
        data = cur.fetchall()
        return render_template("store.html", products=get_prod(),ctgy=data)

    finally:
        db.close()

# ---------- PRODUCT DETAIL ----------
@products.route('/product/<int:pid>')
def product_detail(pid):
    db, cur = get_db()
    if not cur:
        return render_template("404.html"), 500

    try:
        cur.execute("SELECT * FROM products WHERE pid=%s", (pid,))
        heading = (
        "pid","prodname","decrp","stock",
        "price","offer","sold","supplier",
        "ctgy","collection"
        )
        data = cur.fetchone()
        prod = dict(zip(heading, data))
        prod['offer']=float(prod['price'])-(float(prod['price'])*float(prod['offer']))
        prod["prodname"] = prod["prodname"].title()

        cur.execute("SELECT link FROM images WHERE pid=%s", (prod["pid"],))
        imgs = cur.fetchall() or (("black.png",))
        prod["images"] = ["images/" + i[0] for i in imgs]

        cur.execute("Select sum(star),count(*) from review where pid=%s", (prod["pid"],))
        prod['rating']=0
        s,n=cur.fetchone()
        if s is not None or n!=0:
            prod['rating']=round(s/n)

        if not data:
            abort(404)

        return render_template("product.html", product=prod)

    finally:
        db.close()

# ---------- ADD TO WISHLIST ----------
@products.route('/add-wish/<int:pid>')
def add_wish(pid):
    if not login_required():
        return redirect(url_for('auth.login'))

    db, cur = get_db()
    if not cur:
        return render_template("404.html"), 500

    try:
        cur.execute("SELECT wid FROM wish WHERE uid=%s AND pid=%s", (session['uid'], pid))
        if cur.fetchone():
            return alert("Already in your wishlist")

        cur.execute("INSERT INTO wish (uid, pid) VALUES (%s, %s)", (session['uid'], pid))
        db.commit()
        return alert("Added to wishlist!")
    finally:
        db.close()

# ---------- ADD TO CART ----------
@products.route('/add-cart/<int:pid>')
def add_cart(pid):
    if not login_required():
        return redirect(url_for('auth.login'))

    db, cur = get_db()
    if not cur:
        return render_template("404.html"), 500

    try:
        cur.execute("SELECT cid FROM cart WHERE uid=%s AND pid=%s", (session['uid'], pid))
        if cur.fetchone():
            return alert("Already in your cart")

        cur.execute("INSERT INTO cart (uid, pid) VALUES (%s, %s)", (session['uid'], pid))
        db.commit()
        return alert("Added to cart!")
    finally:
        db.close()
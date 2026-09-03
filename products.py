from decimal import Decimal
import csv
import os
from flask import Blueprint,jsonify, render_template, render_template_string, redirect, url_for, session, abort, request
from db import get_db

products = Blueprint("products", __name__)

# ---------- HELPERS ----------
def login_required():
    return 'uid' in session

def alert(msg):
    return render_template_string(
        f"<script>alert('{msg}');history.back()</script>"
    )


def get_prod(end, start=0, randomize=False, connection=None, exclude_pid=None, ids=None):
    owns_connection = connection is None
    db, cur = connection or get_db()
    if not cur:
        return []

    try:
        query = """
            SELECT p.pid, p.prodname, p.description, p.stock, p.price,
                   p.offer, p.sold, p.supplier, p.catgy, p.collection,
                   COALESCE(image_data.links, ARRAY['black.png']) AS image_links,
                   COALESCE(rating_data.total_stars, 0) AS total_stars,
                   COALESCE(rating_data.review_count, 0) AS review_count
            FROM products AS p
            LEFT JOIN LATERAL (
                SELECT ARRAY_AGG(i.link ORDER BY i.iid) AS links
                FROM images AS i
                WHERE i.pid = p.pid
            ) AS image_data ON TRUE
            LEFT JOIN LATERAL (
                SELECT SUM(r.star) AS total_stars, COUNT(*) AS review_count
                FROM review AS r
                WHERE r.pid = p.pid
            ) AS rating_data ON TRUE
            {where_clause}
            {order_clause}
            LIMIT %s
        """

        if ids:
            where_clause = "WHERE p.pid = ANY(%s) AND p.stock > 0"
            order_clause = "ORDER BY array_position(%s, p.pid)"
            params = (ids, ids, end)
        elif randomize:
            where_clause = "WHERE p.stock > 0"
            params = (end,)
            if exclude_pid is not None:
                where_clause += " AND p.pid <> %s"
                params = (exclude_pid, end)
            order_clause = "ORDER BY RANDOM()"
        else:
            where_clause = "WHERE p.pid <= %s AND p.pid > %s"
            order_clause = "ORDER BY p.sold"
            params = (end, start, end)

        cur.execute(query.format(where_clause=where_clause, order_clause=order_clause), params)
        rows = cur.fetchall()
        if not rows:
            return []

        heading = (
            "pid","prodname","decrp","stock",
            "price","offer","sold","supplier",
            "ctgy","collection"
        )

        prods = []

        for row in rows:
            prod = dict(zip(heading, row[:10]))
            prod["prodname"] = prod["prodname"].title()

            prod["images"] = [f"images/{image}" for image in row[10]]
            total_stars, review_count = row[11], row[12]
            prod["rating"] = round(total_stars / review_count) if review_count else 0

            prods.append(prod)

        return prods

    except Exception as e:
        db.rollback()
        print("get_prod error:", e)
        return []

    finally:
        if owns_connection:
            db.close()



# ---------- HOME ----------
@products.route('/')
def home():
    data=get_prod(3, randomize=True)
    db,cur=get_db()
    if not cur:
        return render_template(
            "404.html",
            code=503,
            title="Store temporarily unavailable",
            message="We are having trouble connecting to the store right now. Please try again in a moment.",
            steps=[
                "Refresh the page after a few seconds",
                "Check your internet connection",
                "Contact our team if the issue continues",
            ],
            e="Database connection unavailable",
        ), 503
    cur.execute("Select * from collection")
    cltn=cur.fetchall()
    headings=['cid','name','image']
    collection=[]
    if cltn:
        for i in cltn:
            collect=dict(zip(headings,i))
            if not collect['image']:
                collect['image']="images/black.png"
            else:
                collect["image"]="images/"+collect["image"]
            collection.append(collect)
    else:
        collection=None
    if data:
        return render_template("home.html",products=data[:3],collections=collection)
    else:
        return render_template("home.html",collections=collection)
    
# ---------- STORE ----------
PRODUCTS_PER_PAGE=6
@products.route('/store')
def store():
    db, cur = get_db()
    if not cur:
        return render_template(
        "404.html",
        code=400,
        title="An Error Occurred",
        message="Databse Cursor not found",
        steps=[
            "Server side error, please contact our team as soon as possible",
        ],
        e="Database Cursor not found"
    )

    try:
        page = request.args.get('page', 1, type=int)

        limit = PRODUCTS_PER_PAGE
        start = (page - 1) * limit
        end = start + limit

        cur.execute("SELECT DISTINCT catgy FROM products WHERE stock > 0")
        data = cur.fetchall()

        products_list = get_prod(end, start, connection=(db, cur))

        has_more = len(products_list) == PRODUCTS_PER_PAGE

        return render_template(
            "store.html",
            products=products_list,
            ctgy=data,
            page=page,
            has_more=has_more
            )

    finally:
        db.close()

@products.route('/store/new-drop')
def new_drop_store():
    db, cur = get_db()
    if not cur:
        return render_template("404.html", code=503, title="Store temporarily unavailable",
                               message="We are having trouble connecting to the store right now.",
                               steps=["Refresh the page after a few seconds"],
                               e="Database connection unavailable"), 503

    try:
        csv_path = os.path.join(os.path.dirname(__file__), "static", "images", "new_drop", "products", "products.csv")
        ids = []
        with open(csv_path, newline="", encoding="utf-8") as file:
            for row in csv.DictReader(file):
                try:
                    product_id = int(row["pid"])
                except (KeyError, TypeError, ValueError):
                    continue
                if product_id not in ids:
                    ids.append(product_id)

        products_list = get_prod(len(ids), connection=(db, cur), ids=ids) if ids else []
        categories = sorted({product["ctgy"] for product in products_list if product.get("ctgy")})
        return render_template("store.html", products=products_list, ctgy=[(category,) for category in categories],
                               page=1, has_more=False, name="New Drop")
    finally:
        db.close()

@products.route('/collections/<int:cid>')
def collection_pop(cid):
    db, cur = get_db()
    if not cur:
        return render_template(
        "404.html",
        code=400,
        title="An Error Occurred",
        message="Databse Cursor not found",
        steps=[
            "Server side error, please contact our team as soon as possible",
        ],
        e="Database Cursor not found"
    )

    try:
        page = request.args.get('page', 1, type=int)
        limit = PRODUCTS_PER_PAGE
        offset = (page - 1) * limit

        cur.execute("SELECT name FROM collection WHERE cid=%s", (cid,))
        row = cur.fetchone()

        if not row:
            return render_template(
        "404.html",
        code=400,
        title="An Error Occurred",
        message="Databse table collection, no rows fetched",
        steps=[
            "Server side error, please contact our team as soon as possible",
        ],
        e="Databse table collection, no rows fetched",
    )

        name = row[0]

        cur.execute("""
            SELECT DISTINCT catgy
            FROM products
            WHERE stock > 0
            AND LOWER(TRIM(collection)) = LOWER(TRIM(%s))
        """, (name,))
        data = cur.fetchall() or []

        cur.execute("""
            SELECT pid, prodname, description, stock, price, offer, sold, supplier, catgy, collection
            FROM products
            WHERE stock > 0
            AND LOWER(TRIM(collection)) = LOWER(TRIM(%s))
            ORDER BY sold DESC
            LIMIT %s OFFSET %s
        """, (name, limit, offset))

        rows = cur.fetchall()

        heading = (
            "pid", "prodname", "decrp", "stock",
            "price", "offer", "sold", "supplier",
            "ctgy", "collection"
        )

        prods = []

        for row in rows:
            prod = dict(zip(heading, row))
            prod["prodname"] = prod["prodname"].title()

            cur.execute("SELECT link FROM images WHERE pid=%s", (prod["pid"],))
            imgs = cur.fetchall() or [("black.png",)]
            prod["images"] = [f"images/{i[0]}" for i in imgs]

            cur.execute(
                "SELECT SUM(star), COUNT(*) FROM review WHERE pid=%s",
                (prod["pid"],)
            )
            result = cur.fetchone()
            if result:
                s, n = result
                prod["rating"] = round(s / n) if s and n else 0
            else:
                prod["rating"] = 0

            prods.append(prod)

        has_more = len(prods) == limit

        return render_template(
            "store.html",
            products=prods,
            ctgy=data,
            page=page,
            has_more=has_more
        )

    except Exception as e:
        db.rollback()
        print("ERROR:", e)
        return render_template(
        "404.html",
        code=400,
        title="An Error Occurred",
        message=str(e),
        steps=[
            "Check the URL for any typing errors",
            "Refresh the page or try again after a moment",
            "Navigate back to our homepage to continue browsing",
            "Clear your browser cache if the issue persists"
        ],
        e=e
    )

    finally:
        db.close()

# ---------- PRODUCT DETAIL ----------
@products.route('/product/<int:pid>')
def product_detail(pid):
    db, cur = get_db()
    if not cur:
        db.rollback()
        return render_template(
        "404.html",
        code=400,
        title="An Error Occurred",
        message="Databse Cursor not found",
        steps=[
            "Server side error, please contact our team as soon as possible",
        ],
        e="Database Cursor not found"
    )
    try:
        cur.execute("SELECT pid,prodname,description,stock,price,offer,sold,supplier,catgy,collection FROM products WHERE pid=%s", (pid,))
        heading = (
        "pid","prodname","decrp","stock",
        "price","offer","sold","supplier",
        "ctgy","collection"
        )
        data = cur.fetchone()
        if not data:
            abort(404)
        prod = dict(zip(heading, data))
        prod['offer']=float(prod['price'])-(float(prod['price'])*float(prod['offer'])/100)
        prod["prodname"] = prod["prodname"].title()

        cur.execute("SELECT link FROM images WHERE pid=%s", (prod["pid"],))
        imgs = cur.fetchall() or [("black.png",)]
        prod["images"] = ["images/" + i[0] for i in imgs]

        cur.execute("Select sum(star),count(*) from review where pid=%s", (prod["pid"],))
        prod['rating']=0
        s,n=cur.fetchone()
        if s is not None and n != 0:
            prod['rating'] = round(s/n)

        cur.execute('Select "user",comment,star from review where pid=%s',(prod["pid"],))
        data=cur.fetchall()
        heading=("user","comment","star")
        l=[]
        for i in data:
            l.append(dict(zip(heading,i)))
        prod['reviews']=l

        recommended = get_prod(
            4,
            randomize=True,
            connection=(db, cur),
            exclude_pid=pid,
        )
        return render_template("product.html", product=prod, recommended=recommended)

    finally:
        db.close()



# ---------- ADD TO WISHLIST ----------
@products.route('/add-wish/<int:pid>')
def add_wish(pid):
    if not login_required():
        return redirect(url_for('auth.login'))

    db, cur = get_db()
    if not cur:
        db.rollback()
        return render_template(
        "404.html",
        code=400,
        title="An Error Occurred",
        message="Databse Cursor not found",
        steps=[
            "Server side error, please contact our team as soon as possible",
        ],
        e="Database Cursor not found"
    )

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
        db.rollback()
        return render_template(
        "404.html",
        code=400,
        title="An Error Occurred",
        message="Databse Cursor not found",
        steps=[
            "Server side error, please contact our team as soon as possible",
        ],
        e="Database Cursor not found"
    )

    try:
        cur.execute("SELECT cid FROM cart WHERE uid=%s AND pid=%s", (session['uid'], pid))
        if cur.fetchone():
            return alert("Already in your cart")

        cur.execute("INSERT INTO cart (uid, pid) VALUES (%s, %s)", (session['uid'], pid))
        db.commit()
        return alert("Added to cart!")
    finally:

        db.close()

#-------------review-------------
@products.route("/add_review/<int:pid>", methods=["POST"])
def add_review(pid):
    if not login_required():
        return redirect(url_for('auth.login'))
    conn,cur = get_db()
    
    star = request.form.get("star")
    comment = request.form.get("comment")

    cur.execute("Select username from users where uid=%s",(session['uid'],))
    username = cur.fetchone()[0]
    cur.execute(
        'INSERT INTO review (pid, star, comment, "user") VALUES (%s, %s, %s, %s)',
        (pid, star, comment, username)
    )

    conn.commit()
    cur.close()
    conn.close()

    return redirect(url_for("products.product_detail", pid=pid))

#-----------contact-----------
@products.route("/contact")
def contact():
    return render_template("contact.html")

#--------------cart-------
@products.route("/cart")
def cart():
    if not login_required():
        return redirect(url_for('auth.login'))
    db,cur = get_db()
    cur.execute("Select pid from cart where uid=%s",(session['uid'],))
    data=cur.fetchall()
    l=[]
    m=[]
    total=Decimal("0")
    discount=Decimal("0")
    for row in data:
        cur.execute(
            "SELECT pid, prodname, price, offer FROM products WHERE pid=%s",
            (row[0],)
        )
        product=cur.fetchone()
        if not product:
            continue

        pid, name, price, offer = product
        price=Decimal(str(price))
        offer=Decimal(str(offer or 0))
        offer=max(Decimal("0"), min(Decimal("100"), offer))
        item_discount=(price * offer / Decimal("100")).quantize(Decimal("0.01"))
        sale_price=(price - item_discount).quantize(Decimal("0.01"))

        cur.execute("SELECT link FROM images WHERE pid=%s", (pid,))
        img=cur.fetchone()
        l.append({
            "pid": pid,
            "name": name,
            "price": price,
            "offer": offer,
            "discount": item_discount,
            "sale_price": sale_price,
            "image": "images/" + str(img[0]) if img else "images/black.png",
        })
        m.append(pid)
        total += price
        discount += item_discount
    db.close()
    subtotal=total.quantize(Decimal("0.01"))
    discount=discount.quantize(Decimal("0.01"))
    grand_total=(subtotal - discount).quantize(Decimal("0.01"))
    return render_template("cart.html",cart=l,total=subtotal,i=m,offer=discount,sub=grand_total)

@products.route("/delcart/<int:pid>")
def delcart(pid):
    db,cur=get_db()
    cur.execute("Delete from cart where pid=%s",(pid,))
    db.commit()
    db.close()
    return redirect((url_for("products.cart")))

@products.route("/msg", methods=['POST'])
def msg():
    name = request.form["name"]
    mail = request.form["mail"]
    msg = request.form["msg"]

    conn, cur = get_db()

    cur.execute(
        "INSERT INTO messages (name, mail, msg) VALUES (%s, %s, %s)",
        (name, mail, msg)
    )

    conn.commit()
    conn.close()

    return alert("Message sent!")



#----------customize--------
@products.route("/custom")
def custom():

    if not login_required():
        return redirect(url_for('auth.login'))

    db, cur = get_db()

    try:

        cur.execute("""
            SELECT username, email, phone
            FROM users
            WHERE uid=%s
        """, (session["uid"],))

        u = cur.fetchone()

        cur.execute("""
            SELECT *
            FROM templates
        """)

        data = cur.fetchall()

        head = [
            "tid",
            "name",
            "image",
            "color"
        ]

        temps = []

        for i in data:

            l = list(i)

            if l[3]:
                l[3] = l[3].split()

            if not l[2]:
                l[2] = "images/black.png"

            else:
                l[2] = "images/" + l[2]

            temp = dict(zip(head, l))

            temps.append(temp)

        return render_template(
            "custom.html",
            templates=temps,
            user=u[0],
            email=u[1],
            phone=u[2]
        )

    finally:

        db.close()

@products.route("/customrequest", methods=["POST"])
def custom_request():

    if not login_required():
        return redirect(url_for('auth.login'))

    db, cur = get_db()

    try:

        template = request.form.get("temp")
        description = request.form.get("details")

        # USER DETAILS
        cur.execute("""
            SELECT
                username,
                email,
                phone
            FROM users
            WHERE uid=%s
        """, (session["uid"],))

        user = cur.fetchone()

        if not user:

            return jsonify({
                "status": "error",
                "message": "User not found"
            })

        username, email, phone = user

        # CLEAN DEFAULTS
        if not template:
            template = "Pre-Designed"

        if not description:
            description = "No description provided"

        # INSERT REQUEST
        cur.execute("""
            INSERT INTO custom
            (
                date,
                template,
                description,
                status,
                name,
                mail,
                phone
            )

            VALUES
            (
                CURRENT_DATE,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s
            )
        """, (
            template,
            description,
            "Pending",
            username,
            email,
            phone
        ))

        db.commit()

        return jsonify({
            "status": "success",
            "message": "Custom request submitted"
        })

    except Exception as e:

        db.rollback()

        print(e)

        return jsonify({
            "status": "error",
            "message": str(e)
        })

    finally:

        db.close()


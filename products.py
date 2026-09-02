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


def get_prod(end, start=0, randomize=False):
    db, cur = get_db()
    if not cur:
        return []

    try:
        if randomize:
            cur.execute("""
                SELECT pid,prodname,description,stock,price,offer,sold,supplier,catgy,collection
                FROM products
                WHERE stock > 0
                ORDER BY RANDOM()
                LIMIT %s
                """, (end,))
        else:
            cur.execute("""
                SELECT pid,prodname,description,stock,price,offer,sold,supplier,catgy,collection
                FROM products
                WHERE pid <= %s AND pid > %s
                ORDER BY sold
                """, (end, start))
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
            prod = dict(zip(heading, row))
            prod["prodname"] = prod["prodname"].title()

            cur.execute("SELECT link FROM images WHERE pid=%s", (prod["pid"],))
            imgs = cur.fetchall() or [("black.png",)]

            prod["images"] = [f"images/{i[0]}" for i in imgs]

            cur.execute(
                "SELECT SUM(star), COUNT(*) FROM review WHERE pid=%s",
                (prod["pid"],)
            )
            s, n = cur.fetchone()
            prod["rating"] = round(s / n) if s and n else 0

            prods.append(prod)

        return prods

    except Exception as e:
        db.rollback()
        print("get_prod error:", e)
        return []

    finally:
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

        products_list = get_prod(end, start)

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
    t=of=0
    for i in data:
        cur.execute("Select * from products where pid=%s",(i[0],))
        data=cur.fetchone()
        data=list(data)
        of+=(data[4]*data[5]/100)
        m.append(data[0])
        cur.execute("Select link from images where pid=%s",(data[0],))
        img=cur.fetchone()
        if img:
            data.append("images/"+str(img[0]))
        else:
            data.append("images/black.png")
        l.append(data)
        t+=data[4]
    db.close()
    st=t-of
    return render_template("cart.html",cart=l,total=t,i=m,offer=of,sub=st)

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


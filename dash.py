from flask import (
    Blueprint,
    jsonify,
    render_template,
    redirect,
    url_for,
    request,
    session
)

from db import get_db

dash = Blueprint("dash", __name__)

# =========================================================
# HELPERS
# =========================================================

def login_required():
    return 'uid' in session

def json_error(message):
    return jsonify({
        "status": "error",
        "message": message
    })

def json_success(message):
    return jsonify({
        "status": "success",
        "message": message
    })

# =========================================================
# MAIN DASHBOARD
# =========================================================

@dash.route("/dash")
def dashbd():

    if not login_required():
        return redirect(url_for("auth.login"))

    return render_template("dash.html")

# =========================================================
# DASHBOARD TABS
# =========================================================

@dash.route("/dash/dashboard")
def dashboard_tab():

    return render_template(
        "dash/dashboard.html",
        count=c(),
        revenue=rev()
    )

@dash.route("/dash/ord-request")
def ord_request_tab():

    return render_template(
        "dash/ord_request.html",
        customs=custom(),
        orders=orders()
    )

@dash.route("/dash/messages")
def messages_tab():

    return render_template(
        "dash/messages.html",
        msgs=msg()
    )

@dash.route("/dash/ord-find")
def ord_find_tab():

    return render_template(
        "dash/ord_find.html",
    )


@dash.route("/dash/prod-top")
def prod_top_tab():

    return render_template(
        "dash/prod_top.html",
        highs=high()
    )


@dash.route("/dash/prod-critic")
def prod_critic_tab():

    return render_template(
        "dash/prod_critic.html",
        lows=low()
    )

@dash.route("/dash/products")
def products_tab():

    return render_template("dash/products.html")

@dash.route("/dash/offers")
def offers_tab():

    db, cur = get_db()
    try:
        cur.execute("""
            SELECT pid, prodname, price, offer
            FROM products
            ORDER BY prodname
        """)
        products = cur.fetchall()
        return render_template("dash/offers.html", products=products)
    finally:
        db.close()

@dash.route("/dash/update-offers", methods=["POST"])
def update_offers():

    offer = request.form.get("offer", type=float)
    scope = request.form.get("scope")
    pid = request.form.get("pid", type=int)

    if offer is None or offer < 0 or offer > 100:
        return json_error("Offer must be between 0 and 100 percent")

    if scope == "product" and not pid:
        return json_error("Choose a product for a specific offer")

    db, cur = get_db()
    try:
        if scope == "product":
            cur.execute("UPDATE products SET offer=%s WHERE pid=%s", (offer, pid))
            message = "Offer updated for the selected product"
        else:
            cur.execute("UPDATE products SET offer=%s", (offer,))
            message = "Offer updated for all products"

        db.commit()
        return json_success(message)
    except Exception as e:
        db.rollback()
        return json_error(str(e))
    finally:
        db.close()

@dash.route("/dash/users")
def users_tab():

    return render_template("dash/users.html")

@dash.route("/dash/admin")
def admins_tab():

    db, cur = get_db()
    admins = []

    try:

        cur.execute("""
            SELECT uid, username, email, phone
            FROM users
            WHERE desig='w'
        """)

        rows = cur.fetchall()

        for row in rows:

            admins.append({
                "uid": row[0],
                "name": row[1],
                "email": row[2],
                "phone": row[3]
            })

    except Exception as e:

        print(e)

    finally:

        db.close()

    return render_template(
        "dash/admin.html",
        admins=admins
    )


@dash.route("/dash/password")
def pswd_request_tab():

    db, cur = get_db()
    reqs = []

    try:

        cur.execute("""
            SELECT email, password
            FROM password
        """)

        rows = cur.fetchall()

        for row in rows:

            reqs.append({
                "email": row[0],
                "pswd": row[1]
            })

    except Exception as e:

        print(e)

    finally:

        db.close()

    return render_template(
        "dash/password.html",
        reqs=reqs
    )


# =========================================================
# SEARCH ROUTES
# RETURNS HTML
# =========================================================

@dash.route("/search-user", methods=["POST"])
def search_user():

    db, cur = get_db()

    try:

        uid = request.form.get("uid")

        cur.execute("""
            SELECT uid, username, email, phone
            FROM users
            WHERE uid=%s
        """, (uid,))

        data = cur.fetchone()

        if not data:
            return json_error("No user found")

        found_user = {
            "uid": data[0],
            "name": data[1],
            "email": data[2],
            "phone": data[3]
        }

        return render_template(
            "dash/users.html",
            found_user=found_user
        )

    except Exception as e:

        print(e)
        return json_error(str(e))

    finally:

        db.close()


@dash.route("/search-order", methods=["POST"])
def search_order():

    db, cur = get_db()

    try:

        oid = request.form.get("oid")

        cur.execute("""
            SELECT oid, uid, pid, price, status
            FROM orders
            WHERE oid=%s
        """, (oid,))

        data = cur.fetchone()

        if not data:
            return json_error("No order found")

        found_order = {
            "oid": data[0],
            "uid": data[1],
            "pid": data[2],
            "price": data[3],
            "status": data[4]
        }

        # USER
        cur.execute("""
            SELECT username
            FROM users
            WHERE uid=%s
        """, (found_order["uid"],))

        user = cur.fetchone()

        found_order["name"] = (
            user[0]
            if user else "Unknown"
        )

        # PRODUCT
        if found_order["pid"] is None:

            found_order["product"] = "#CUSTOM_DESIGN"

        else:

            cur.execute("""
                SELECT prodname
                FROM products
                WHERE pid=%s
            """, (found_order["pid"],))

            product = cur.fetchone()

            found_order["product"] = (
                product[0]
                if product else "Unknown Product"
            )

        # PAYMENT
        cur.execute("""
            SELECT credit, debit
            FROM transactions
            WHERE title=%s
        """, (str(found_order["oid"]),))

        trans = cur.fetchall()

        pay = 0

        for t in trans:

            credit = t[0] or 0
            debit = t[1] or 0

            pay += credit - debit

        found_order["pay"] = pay

        return render_template(
            "dash/ord_find.html",
            orders=orders(),
            found_order=found_order
        )

    except Exception as e:

        print(e)
        return json_error(str(e))

    finally:

        db.close()


@dash.route("/search-product", methods=["POST"])
def search_prod():

    db, cur = get_db()

    try:

        pid = request.form.get("pid")

        cur.execute("""
            SELECT *
            FROM products
            WHERE pid=%s
        """, (pid,))

        data = cur.fetchone()

        if not data:
            return json_error("No product found")

        prod = {
            "pid": data[0],
            "name": data[1],
            "desc": data[2],
            "stock": data[3],
            "price": data[4],
            "offer": data[5],
            "sold": data[6],
            "supplier": data[7],
            "catgy": data[8],
            "collection": data[9],
            "colour": data[10]
        }

        return render_template(
            "dash/products.html",
            prod=prod
        )

    except Exception as e:

        print(e)
        return json_error(str(e))

    finally:

        db.close()


# =========================================================
# AJAX ROUTES
# RETURNS JSON
# =========================================================

@dash.route("/update-custom-status", methods=["POST"])
def update_custom_status():

    db, cur = get_db()

    try:

        cids = request.form.getlist("cid")

        for cid in cids:

            status = request.form.get(f"status_{cid}")

            cur.execute("""
                UPDATE custom
                SET status=%s
                WHERE cid=%s
            """, (status, cid))

        db.commit()

        return json_success(
            "Updated successfully"
        )

    except Exception as e:

        db.rollback()
        print(e)

        return json_error(str(e))

    finally:

        db.close()


@dash.route("/mark-replied", methods=["POST"])
def mark_replied():

    db, cur = get_db()

    try:

        mid = request.form.get("mid")

        cur.execute("""
            UPDATE messages
            SET replied=TRUE
            WHERE mid=%s
        """, (mid,))

        db.commit()

        return json_success(
            "Message marked replied"
        )

    except Exception as e:

        db.rollback()
        print(e)

        return json_error(str(e))

    finally:

        db.close()


@dash.route("/add-product", methods=["POST"])
def add_product():

    db, cur = get_db()

    try:

        cur.execute("""
            INSERT INTO products(
                prodname,
                description,
                stock,
                price,
                offer,
                sold,
                supplier,
                catgy,
                collection,
                colour
            )
            VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            request.form["name"],
            request.form["desc"],
            request.form["stock"],
            request.form["price"],
            request.form["offer"],
            request.form["sold"],
            request.form["supplier"],
            request.form["catgy"],
            request.form["collection"],
            request.form["colour"]
        ))

        db.commit()

        return json_success(
            "Product added successfully"
        )

    except Exception as e:

        db.rollback()
        print(e)

        return json_error(str(e))

    finally:

        db.close()


@dash.route("/update-product", methods=["POST"])
def update_prod():

    db, cur = get_db()

    try:

        cur.execute("""
            UPDATE products
            SET
                prodname=%s,
                description=%s,
                stock=%s,
                price=%s,
                offer=%s,
                sold=%s,
                supplier=%s,
                catgy=%s,
                collection=%s,
                colour=%s
            WHERE pid=%s
        """, (
            request.form["name"],
            request.form["desc"],
            request.form["stock"],
            request.form["price"],
            request.form["offer"],
            request.form["sold"],
            request.form["supplier"],
            request.form["catgy"],
            request.form["collection"],
            request.form["colour"],
            request.form["pid"]
        ))

        db.commit()

        return json_success(
            "Product updated successfully"
        )

    except Exception as e:

        db.rollback()
        print(e)

        return json_error(str(e))

    finally:

        db.close()

@dash.route("/update-requests", methods=["POST"])
def update_requests():

    if not login_required():
        return redirect(url_for("auth.login"))

    db,cur = get_db()

    # ==========================
    # UPDATE ORDERS
    # ==========================

    order_ids = request.form.getlist("oid")

    for oid in order_ids:

        pay = request.form.get(f"pay_{oid}")
        status = request.form.get(f"order_status_{oid}")

        cur.execute("""
            UPDATE orders
            SET status=%s
            WHERE oid=%s
        """, (
            status,
            oid
        ))

        if pay!="0":
            cur.execute("insert into transactions title,credit values('Customer pay',%s)",pay)
    # ==========================
    # UPDATE CUSTOM REQUESTS
    # ==========================

    custom_ids = request.form.getlist("cid")

    for cid in custom_ids:

        status = request.form.get(f"status_{cid}")

        cur.execute("""
            UPDATE custom
            SET status=%s
            WHERE cid=%s
        """, (
            status,
            cid
        ))

    db.commit()

    return jsonify({
        "success": True,
        "message": "Changes saved successfully"
    })

@dash.route("/delete-product", methods=["POST"])
def delete_prod():

    db, cur = get_db()

    try:

        pid = request.form.get("pid")

        cur.execute("""
            DELETE FROM products
            WHERE pid=%s
        """, (pid,))

        db.commit()

        return json_success(
            "Product deleted successfully"
        )

    except Exception as e:

        db.rollback()
        print(e)

        return json_error(str(e))

    finally:

        db.close()


@dash.route("/delete-user", methods=["POST"])
def delete_user():

    db, cur = get_db()

    try:

        uid = request.form.get("uid")

        cur.execute("""
            DELETE FROM users
            WHERE uid=%s
        """, (uid,))

        db.commit()

        return json_success(
            "User deleted successfully"
        )

    except Exception as e:

        db.rollback()
        print(e)

        return json_error(str(e))

    finally:

        db.close()


@dash.route("/add-order", methods=["POST"])
def add_order():

    db, cur = get_db()

    try:

        name = request.form.get("customer_name")
        email = request.form.get("customer_email")
        phone = request.form.get("customer_phone")
        address = request.form.get("address")

        product = request.form.get("product_name")
        price = request.form.get("price")
        catgy = request.form.get("category")
        status = request.form.get("status")
        desc = request.form.get("description")

        # Update existing user
        cur.execute(
            """
            UPDATE users
            SET phone=%s, address=%s, username=%s
            WHERE email=%s
            """,
            (phone, address, name, email)
        )

        # Insert if not exists
        if cur.rowcount == 0:
            cur.execute(
                """
                INSERT INTO users
                (username, email, phone, address)
                VALUES (%s, %s, %s, %s)
                """,
                (name, email, phone, address)
            )

        # Get uid
        cur.execute(
            "SELECT uid FROM users WHERE email=%s",
            (email,)
        )

        uid = cur.fetchone()[0]

        # Create product
        cur.execute(
            """
            INSERT INTO products
            (prodname, price, description, catgy)
            VALUES (%s, %s, %s, %s)
            RETURNING pid
            """,
            (product, price, desc, catgy)
        )

        pid = cur.fetchone()[0]

        # Create order
        cur.execute(
            """
            INSERT INTO orders
            (pid, uid, price, status)
            VALUES (%s, %s, %s, %s)
            """,
            (pid, uid, price, status)
        )

        db.commit()

        return json_success("Order added successfully")

    except Exception as e:
        db.rollback()
        print(e)
        return json_error(str(e))

    finally:
        db.close()

@dash.route("/add-admin", methods=["POST"])
def add_admin():

    db, cur = get_db()

    try:

        email = request.form.get("email")

        cur.execute("""
            UPDATE users
            SET desig='w'
            WHERE email=%s
        """, (email,))

        db.commit()

        return json_success(
            "Admin added successfully"
        )

    except Exception as e:

        db.rollback()
        print(e)

        return json_error(str(e))

    finally:

        db.close()



@dash.route("/done-request/<email>", methods=["POST"])
def done_request(email):

    db, cur = get_db()

    try:

        cur.execute("""
            DELETE FROM password
            WHERE email=%s
        """, (email,))

        db.commit()

        return json_success(
            "Request deleted successfully"
        )

    except Exception as e:

        db.rollback()
        print(e)

        return json_error(str(e))

    finally:

        db.close()


# =========================================================
# DATA HELPERS
# =========================================================

def rev():

    db, cur = get_db()

    try:

        cur.execute("""
            SELECT
                SUM(credit),
                SUM(debit)
            FROM transactions
        """)

        data = cur.fetchone()

        credit = data[0] or 0
        debit = data[1] or 0

        return credit - debit

    except Exception as e:

        print(e)
        return 0

    finally:

        db.close()


def c():

    db, cur = get_db()

    try:

        cur.execute("""
            SELECT COUNT(*)
            FROM orders
        """)

        return cur.fetchone()[0]

    except Exception as e:

        print(e)
        return 0

    finally:

        db.close()


def orders():

    db, cur = get_db()
    ods = []

    try:

        cur.execute("""
            SELECT oid, pid, uid, price, status
            FROM orders
            WHERE status!='Done'
            ORDER BY date
        """)

        rows = cur.fetchall()

        for row in rows:

            od = {
                "oid": row[0],
                "pid": row[1],
                "uid": row[2],
                "price": row[3],
                "status": row[4]
            }

            # USER
            cur.execute("""
                SELECT username
                FROM users
                WHERE uid=%s
            """, (od["uid"],))

            user = cur.fetchone()

            od["name"] = (
                user[0]
                if user else "Unknown"
            )

            # PRODUCT
            if od["pid"] is None:

                od["product"] = "#CUSTOM_ORDER"

            else:

                cur.execute("""
                    SELECT prodname
                    FROM products
                    WHERE pid=%s
                """, (od["pid"],))

                product = cur.fetchone()

                od["product"] = (
                    product[0]
                    if product else "Unknown Product"
                )

            # PAYMENT
            cur.execute("""
                SELECT credit, debit
                FROM transactions
                WHERE title=%s
            """, (str(od["oid"]),))

            trans = cur.fetchall()

            pay = 0

            for t in trans:

                credit = t[0] or 0
                debit = t[1] or 0

                pay += credit - debit

            od["pay"] = pay

            ods.append(od)

    except Exception as e:

        print(e)

    finally:

        db.close()

    return ods


def custom():

    db, cur = get_db()
    cust = []

    try:

        cur.execute("""
            SELECT *
            FROM custom
            WHERE status!='completed' and status!='cancelled' 
            ORDER BY date DESC
        """)

        rows = cur.fetchall()

        for row in rows:

            template = row[2]
            description = row[3]

            # CLEAN PAYMENT ENTRIES
            if template and "amount collect:" in template.lower():

                amount = (
                    template
                    .replace("amount collect:", "")
                    .strip()
                )

                template = "Product Purchase"

                description = (
                    f"Customer completed payment of ₹{amount}"
                )

            # CLEAN PRODUCT IDS
            if description and "," in str(description):

                try:

                    pids = [
                        int(pid.strip())
                        for pid in description.split(",")
                    ]

                    product_names = []

                    for pid in pids:

                        cur.execute("""
                            SELECT prodname
                            FROM products
                            WHERE pid=%s
                        """, (pid,))

                        product = cur.fetchone()

                        if product:

                            product_names.append(product[0])

                    if product_names:

                        description = ", ".join(product_names)

                except:
                    pass

            cust.append({

                "cid": row[0],

                "temp": template,

                "desc": description,

                "status": row[4],

                "name": row[5],

                "mail": row[6],

                "phone": row[7]
            })

    except Exception as e:

        print(e)

    finally:

        db.close()

    return cust

def msg():

    db, cur = get_db()
    msgs = []

    try:

        cur.execute("""
            SELECT *
            FROM messages
            WHERE replied=FALSE
        """)

        rows = cur.fetchall()

        for row in rows:

            msgs.append({
                "mid": row[0],
                "name": row[1],
                "mail": row[2],
                "msg": row[3],
                "status": row[4]
            })

    except Exception as e:

        print(e)

    finally:

        db.close()

    return msgs


def high():

    db, cur = get_db()
    products = []

    try:

        cur.execute("""
            SELECT pid, COUNT(*) as total
            FROM orders
            GROUP BY pid
            ORDER BY total DESC
        """)

        rows = cur.fetchall()

        for row in rows:

            pid = row[0]

            if pid is not None:

                cur.execute("""
                    SELECT pid, prodname, price, offer
                    FROM products
                    WHERE pid=%s
                """, (pid,))

                data = cur.fetchone()

                if data:

                    products.append({
                        "pid": data[0],
                        "name": data[1],
                        "price": data[2],
                        "offer": data[3]
                    })

    except Exception as e:

        print(e)

    finally:

        db.close()

    return products


def low():

    db, cur = get_db()
    lows = []

    try:

        cur.execute("""
            SELECT pid, AVG(star)
            FROM review
            GROUP BY pid
            HAVING AVG(star) < 3
        """)

        rows = cur.fetchall()

        for row in rows:

            pid = row[0]

            if pid is None:

                lows.append({
                    "pid": None,
                    "name": "#CUSTOM_ORDER",
                    "price": "-",
                    "offer": "-",
                    "rating": round(row[1], 1)
                })

                continue

            cur.execute("""
                SELECT pid, prodname, price, offer
                FROM products
                WHERE pid=%s
            """, (pid,))

            data = cur.fetchone()

            if data:

                lows.append({
                    "pid": data[0],
                    "name": data[1],
                    "price": data[2],
                    "offer": data[3],
                    "rating": round(row[1], 1)
                })

    except Exception as e:

        print(e)

    finally:

        db.close()

    return lows
from django.shortcuts import render
from flask import Flask, render_template
from dotenv import load_dotenv
import os

from auth import auth
from products import products
from payment import payment  # <--- import payment blueprint

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "zioraa_dev_secret_key")

# ---------- REGISTER BLUEPRINTS ----------
app.register_blueprint(auth)
app.register_blueprint(products)
app.register_blueprint(payment)  

@app.errorhandler(404)
def page_not_found(e):
    return render_template(
        "404.html",
        code=404,
        title="Page Not Found",
        message="The page you’re looking for may have been moved, renamed, or is temporarily unavailable.",
        steps=[
            "Check the URL for any typing errors",
            "Refresh the page or try again after a moment",
            "Navigate back to our homepage to continue browsing",
            "Clear your browser cache if the issue persists"
        ],
        e=e
    ), 404

@app.errorhandler(500)
def internal_error(e):
    return render_template(
        "404.html",
        code=500,
        title="Internal Server Error",
        message="Oops! Something went wrong on our end. Please try again later.",
        steps=None,
        e=e
    ), 500

@app.errorhandler(Exception)
def handle_exception(e):
    # Generic handler for other errors
    return render_template(
        "404.html",
        code=getattr(e, 'code', 400),
        title="An Error Occurred",
        message=str(e),
        steps=None,
        e=e
    ), getattr(e, 'code', 400)

@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/custom")
def custom():
    return render_template("custom.html")

# ---------- RUN ----------
if __name__ == "__main__":
    app.run(debug=True)

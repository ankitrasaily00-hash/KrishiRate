from flask import Blueprint, render_template


pages_bp = Blueprint(
    "pages",
    __name__,
)


@pages_bp.get("/")
def dashboard():
    return render_template("dashboard.html")


@pages_bp.get("/markets")
def markets():
    return render_template("markets.html")


@pages_bp.get("/products")
def products():
    return render_template("products.html")


@pages_bp.get("/prices")
def prices():
    return render_template("prices.html")
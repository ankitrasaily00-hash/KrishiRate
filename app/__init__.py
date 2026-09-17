from flask import Flask, render_template

from config import Config
from app.extensions import db, migrate


def create_app(config_class=Config):
    app = Flask(__name__)

    app.config.from_object(config_class)

    db.init_app(app)
    migrate.init_app(app, db)

    # Import models so Flask-Migrate can detect them.
    from app.models import Market, Product, Source, Price  # noqa: F401

    # Register API routes.
    from app.routes.api import api_bp

    app.register_blueprint(api_bp)

    # ==========================================================
    # FRONTEND ROUTES
    # ==========================================================

    @app.get("/")
    def index():
        return render_template("home.html")

    @app.get("/markets")
    def markets():
        return render_template("markets.html")

    @app.get("/products")
    def products():
        return render_template("products.html")

    @app.get("/prices")
    def prices():
        return render_template("prices.html")

    # ==========================================================
    # BACKGROUND SCHEDULER
    # ==========================================================

    from app.services.scheduler import start_scheduler

    start_scheduler(app)

    return app
import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_babel import Babel, gettext as _
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, time, timedelta
from dotenv import load_dotenv

load_dotenv()

db = SQLAlchemy()

def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url or db_url.startswith("postgresql"):
        db_url = "sqlite:///salon.db"
    app.config["SQLALCHEMY_DATABASE_URI"] = db_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["BABEL_DEFAULT_LOCALE"] = "pt"
    app.config["BABEL_SUPPORTED_LOCALES"] = ["pt", "en"]
    app.config["BABEL_TRANSLATION_DIRECTORIES"] = "translations"

    db.init_app(app)

    babel = Babel()

    def get_locale():
        lang = session.get("lang")
        if lang and lang in ["pt", "en"]:
            return lang
        return request.accept_languages.best_match(["pt", "en"], default="pt")

    babel.init_app(app, locale_selector=get_locale)

    from .routes import main
    app.register_blueprint(main)

    with app.app_context():
        db.create_all()
        from .models import seed_data
        seed_data()

    return app

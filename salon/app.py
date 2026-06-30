import ast
import os
import struct
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_babel import Babel, gettext as _
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, time, timedelta
from dotenv import load_dotenv


def _parse_po_string(value: str) -> str:
    return ast.literal_eval(value)


def _read_po_translations(po_path: str) -> dict[str, str]:
    translations = {}
    msgid = None
    msgstr = None
    state = None

    with open(po_path, "r", encoding="utf-8") as po_file:
        for raw_line in po_file:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            if line.startswith("msgid "):
                if msgid is not None and msgstr is not None:
                    translations[msgid] = msgstr
                msgid = _parse_po_string(line[6:])
                msgstr = ""
                state = "msgid"
                continue

            if line.startswith("msgstr "):
                msgstr = _parse_po_string(line[7:])
                state = "msgstr"
                continue

            if line.startswith('"') and state == "msgid":
                msgid += _parse_po_string(line)
            elif line.startswith('"') and state == "msgstr":
                msgstr += _parse_po_string(line)

    if msgid is not None and msgstr is not None:
        translations[msgid] = msgstr

    return translations


def _write_mo_file(mo_path: str, translations: dict[str, str]) -> None:
    keys = sorted(translations.keys())
    ids = b""
    strs = b""
    offsets = []

    for key in keys:
        encoded_key = key.encode("utf-8")
        encoded_str = translations[key].encode("utf-8")
        offsets.append((len(ids), len(encoded_key), len(strs), len(encoded_str)))
        ids += encoded_key + b"\0"
        strs += encoded_str + b"\0"

    keystream_offset = 7 * 4 + len(offsets) * 16
    trstream_offset = keystream_offset + len(ids)

    with open(mo_path, "wb") as mo_file:
        mo_file.write(struct.pack("Iiiiiii", 0x950412de, 0, len(offsets), keystream_offset, trstream_offset, 0, 0))
        for orig_offset, orig_length, trans_offset, trans_length in offsets:
            mo_file.write(struct.pack("IIII", orig_offset, orig_length, trans_offset, trans_length))
        mo_file.write(ids)
        mo_file.write(strs)


def _compile_translations(app: Flask) -> None:
    translations_dir = app.config.get("BABEL_TRANSLATION_DIRECTORIES", "translations")
    if not os.path.isabs(translations_dir):
        translations_dir = os.path.join(app.root_path, translations_dir)

    for lang in app.config.get("BABEL_SUPPORTED_LOCALES", []):
        po_path = os.path.join(translations_dir, lang, "LC_MESSAGES", "messages.po")
        mo_path = os.path.join(translations_dir, lang, "LC_MESSAGES", "messages.mo")

        if not os.path.exists(po_path):
            continue

        os.makedirs(os.path.dirname(mo_path), exist_ok=True)

        try:
            translations = _read_po_translations(po_path)
            _write_mo_file(mo_path, translations)
        except Exception as e:
            print(f"Erro ao compilar traduções {lang}: {e}")


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

    app.jinja_env.globals["_"] = lambda text: text

    #_compile_translations(app)

    #babel = Babel()

    #def get_locale():
    #    lang = session.get("lang")
     #   if lang and lang in ["pt", "en"]:
      #      return lang
       # return request.accept_languages.best_match(["pt", "en"], default="pt")

    #babel.init_app(app, locale_selector=get_locale)

    from .routes import main
    app.register_blueprint(main)

    with app.app_context():
        db.create_all()
        from .models import seed_data
        seed_data()

    return app

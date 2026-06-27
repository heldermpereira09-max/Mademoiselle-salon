import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from salon import app

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_ENV", "development") == "development"
    app.run(host="0.0.0.0", port=port, debug=debug)

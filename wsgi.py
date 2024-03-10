import os
from core import create_app, db
from waitress import serve
from dotenv import load_dotenv
import multiprocessing
from core.models import User

load_dotenv(".env")
mode = os.getenv("RUN_MODE")


app = create_app()
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    if mode == "development":
        app.run(host="0.0.0.0", port=8080, debug=True)
    else:
        serve(app, host="0.0.0.0", port=8080, threads=multiprocessing.cpu_count())

import os
from core import app
from waitress import serve
from dotenv import load_dotenv
import multiprocessing

load_dotenv(".env")
mode = os.getenv("RUN_MODE")

if __name__ == "__main__":
    if mode == "development":
        app.run(host="0.0.0.0", port=5000, debug=True)
    else:
        serve(app, host="0.0.0.0", port=8000, threads=multiprocessing.cpu_count())

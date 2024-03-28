from core import create_app, db
from core.common.variables import RUN_MODE
from waitress import serve
import multiprocessing


app = create_app()
with app.app_context():
    # db.reflect()
    # db.drop_all()
    db.create_all()

if __name__ == "__main__":
    if RUN_MODE == "development":
        app.run(host="0.0.0.0", port=8080, debug=True)
    else:
        serve(app, host="0.0.0.0", port=8080, threads=multiprocessing.cpu_count())

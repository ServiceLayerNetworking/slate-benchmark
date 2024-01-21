from flask import Flask, request, jsonify
import logging
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
import numpy as np

app = Flask(__name__)
# logging.basicConfig(level=logging.DEBUG)
# app.logger.setLevel(logging.INFO)
# werklog = logging.getLogger('werkzeug')
# werklog.setLevel(logging.DEBUG)
# app.logger.setLevel(logging.INFO)


def generate_random_matrix(rows, cols):
    return np.random.rand(rows, cols)

@app.get('/compute') # from wasm
def matmul():
    rows = request.headers.get('row')
    columns = request.headers.get('column')

    # Check if row and column are provided and are digits
    if not (rows and columns and rows.isdigit() and columns.isdigit()):
        return jsonify({"error": "Row and column headers must be provided and must be integers."}), 400

    rows, columns = int(rows), int(columns)

    # Generate two random matrices
    A = np.random.rand(rows, columns)
    B = np.random.rand(columns, rows)  # For matrix multiplication compatibility

    # Perform matrix multiplication
    C = np.dot(A, B)
    
    return jsonify({
        "Matrix A": A.tolist(),
        "Matrix B": B.tolist(),
        "Result": C.tolist()
    })

if __name__ == "__main__":
    # scheduler = BackgroundScheduler()
    # scheduler.add_job(func=write_trace_str_to_file, trigger="interval", seconds=5)
    # scheduler.start()
    # atexit.register(lambda: scheduler.shutdown())
    app.run(host='0.0.0.0', port=8080)
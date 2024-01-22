from flask import Flask, request, jsonify

import logging
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
import numpy as np
import time

app = Flask(__name__)
# logging.basicConfig(level=logging.DEBUG)
# app.logger.setLevel(logging.INFO)
# werklog = logging.getLogger('werkzeug')
# werklog.setLevel(logging.DEBUG)
# app.logger.setLevel(logging.INFO)

# Configure logging
app.logger.setLevel(logging.DEBUG)  # Set the desired logging level
#handler = logging.StreamHandler()  # Log to stderr
#formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
#handler.setFormatter(formatter)
#app.logger.addHandler(handler)


@app.get('/compute')
def light_matmul():
    rows = request.headers.get('row')
    columns = request.headers.get('column')
    # Check if row and column are provided and are digits
    if not (rows and columns and rows.isdigit() and columns.isdigit()):
        return jsonify({"error": "Row and column headers must be provided and must be integers."}), 400
    rows, columns = int(rows), int(columns)
    matmul_output, matmul_time = compute_matmul(rows, columns)
    return jsonify({
#        "Result": matmul_output.tolist(),
        "matmul_time": matmul_time 
    })

@app.post('/compute')
def heavy_matmul():
    rows = request.headers.get('row')
    columns = request.headers.get('column')
    # Check if row and column are provided and are digits
    if not (rows and columns and rows.isdigit() and columns.isdigit()):
        return jsonify({"error": "Row and column headers must be provided and must be integers."}), 400
    rows, columns = int(rows), int(columns)
    matmul_output, matmul_time = compute_matmul(rows, columns)
    return jsonify({
#        "Result": matmul_output.tolist(),
        "matmul_time": matmul_time 
    })

def compute_matmul(rows, columns):
    ts = time.time()
    A = np.random.rand(rows, columns)
    B = np.random.rand(columns, rows)  # For matrix multiplication compatibility
    C = np.dot(A, B)
    matmul_time = (time.time() - ts)*1000
    return C, matmul_time


if __name__ == "__main__":
    # scheduler = BackgroundScheduler()
    # scheduler.add_job(func=write_trace_str_to_file, trigger="interval", seconds=5)
    # scheduler.start()
    # atexit.register(lambda: scheduler.shutdown())
    app.run(host='0.0.0.0', port=8080)

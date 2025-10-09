from flask import Flask, request, jsonify, render_template
from .operations import sqrt, factorial, ln, power
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, '..', 'templates')

app = Flask(__name__, template_folder=TEMPLATE_DIR)
@app.get('/')
def index(): return render_template('index.html')
@app.get('/api/sqrt')
def api_sqrt():
    x=request.args.get('x',type=float)
    if x is None: return jsonify(error="Missing parameter x"),400
    try: return jsonify(result=sqrt(x))
    except Exception as e: return jsonify(error=str(e)),400
@app.get('/api/fact')
def api_fact():
    x=request.args.get('x')
    if x is None: return jsonify(error="Missing parameter x"),400
    try: return jsonify(result=factorial(x))
    except Exception as e: return jsonify(error=str(e)),400
@app.get('/api/ln')
def api_ln():
    x=request.args.get('x',type=float)
    if x is None: return jsonify(error="Missing parameter x"),400
    try: return jsonify(result=ln(x))
    except Exception as e: return jsonify(error=str(e)),400
@app.get('/api/pow')
def api_pow():
    x=request.args.get('x',type=float); b=request.args.get('b',type=float)
    if x is None or b is None: return jsonify(error="Missing x or b"),400
    try: return jsonify(result=power(x,b))
    except Exception as e: return jsonify(error=str(e)),400
def run(): app.run(host='0.0.0.0',port=5000)
if __name__=='__main__': run()

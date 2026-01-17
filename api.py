from flask import Flask, jsonify
import json

app = Flask(__name__)

@app.route("/api/products")
def products():
    with open("products.json", encoding="utf-8") as f:
        return jsonify(json.load(f))

if __name__ == "__main__":
    app.run()

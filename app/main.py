git push origin Data-Replication-and-Consistencyfrom flask import Flask, request
import os

app = Flask(__name__)

STORAGE = "Storage"
os.makedirs(STORAGE, exist_ok=True)

@app.route('/health')
def health():
    return "OK", 200


@app.route('/replicate', methods=['POST'])
def replicate():
    file = request.files['file']
    path = os.path.join(STORAGE, file.filename)
    file.save(path)

    print(f"📥 File received: {file.filename}")
    return "Saved", 200


if __name__ == "__main__":
    app.run(port=5001)
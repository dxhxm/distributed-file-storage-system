from app.services.replication_service import replicate_file

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['file']
    file_path = f"Storage/{file.filename}"

    file.save(file_path)

    # 🔥 REPLICATION CALL
    replicate_file(file_path, file.filename)

    return {"message": "File uploaded & replicated"}
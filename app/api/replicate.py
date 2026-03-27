@app.route('/replicate', methods=['POST'])
def replicate():
    file = request.files['file']
    file.save(f"Storage/{file.filename}")

    return {"message": "File replicated successfully"}
from flask import Flask, render_template, request, send_file
import os
import cv2

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route("/", methods=["GET", "POST"])
def upload_file():
    if request.method == "POST":
        uploaded_file = request.files["file"]
        if uploaded_file:
            file_path = os.path.join(UPLOAD_FOLDER, uploaded_file.filename)
            uploaded_file.save(file_path)
            img = cv2.imread(file_path)
            gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            grayimage_filepath = os.path.join(UPLOAD_FOLDER, "grayscale_img_" + uploaded_file.filename)
            cv2.imshow('Gray Image',gray_img)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
            cv2.imwrite(grayimage_filepath, gray_img)
    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)

import os
import requests

from flask import (
    Flask, render_template, request,
    redirect, url_for, session
)
from werkzeug.utils import secure_filename
from utils import generate_description

app = Flask(__name__)

app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY",
    "change-this-secret-before-deployment"
)

UPLOAD_FOLDER = os.path.join("static", "uploads")
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Paste your actual Colab ngrok URL here.
COLAB_API_URL = "https://unfazed-aerobics-cufflink.ngrok-free.dev"


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


# LOGIN
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")

        if username == "admin" and password == "1234":
            session["user"] = username
            return redirect(url_for("index"))

        return render_template("login.html", error="Invalid login")

    return render_template("login.html")


# LOGOUT
@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))


# MAIN DASHBOARD
@app.route("/", methods=["GET", "POST"])
def index():

    if "user" not in session:
        return redirect(url_for("login"))

    prediction = None
    confidence = None
    description = None
    image_path = None
    top3 = None
    error = None

    if request.method == "POST":

        file = request.files.get("file")

        if not file or file.filename == "":
            error = "Please select a bird image."

        elif not allowed_file(file.filename):
            error = "Please upload JPG, JPEG, PNG, or WEBP images."

        elif COLAB_API_URL == "PASTE_YOUR_COLAB_URL_HERE":
            error = "Please configure your Colab API URL in app.py."

        else:
            filename = secure_filename(file.filename)
            filepath = os.path.join(
                app.config["UPLOAD_FOLDER"], filename
            )

            try:
                file.save(filepath)

                # Send the image to Google Colab for prediction.
                with open(filepath, "rb") as image_file:
                    response = requests.post(
                        COLAB_API_URL.rstrip("/") + "/predict",
                        files={
                            "file": (
                                filename,
                                image_file,
                                file.mimetype or "image/jpeg"
                            )
                        },
                        timeout=120
                    )

                response.raise_for_status()
                result = response.json()

                if "error" in result:
                    raise ValueError(result["error"])

                prediction = result["prediction"]
                confidence = result["confidence"]

                top3 = [
                    (item["species"], item["confidence"])
                    for item in result["top3"]
                ]

                # Generate the bird description using your existing utility.
                try:
                    description = generate_description(prediction)
                except Exception as description_error:
                    print("Description error:", description_error)
                    description = (
                        f"{prediction} is a bird species identified "
                        "by the machine learning model."
                    )

                image_path = filepath.replace("\\", "/")

            except requests.exceptions.Timeout:
                error = "Prediction timed out. Please try again."

            except requests.exceptions.RequestException as api_error:
                print("Colab API error:", api_error)
                error = (
                    "Could not connect to the Colab prediction service. "
                    "Check that your Colab notebook is still running."
                )

            except Exception as prediction_error:
                print("Prediction error:", prediction_error)
                error = "Bird prediction failed. Please try another image."

    return render_template(
        "index.html",
        prediction=prediction,
        confidence=confidence,
        description=description,
        image_path=image_path,
        top3=top3,
        error=error
    )


if __name__ == "__main__":
    app.run(debug=True)
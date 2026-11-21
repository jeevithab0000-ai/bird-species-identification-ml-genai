import os
import json
import urllib.request
import urllib.error

import numpy as np
from PIL import Image
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY")


# Image preprocessing for MobileNetV2
def preprocess_image(path):

    img = Image.open(path).convert("RGB")
    img = img.resize((224, 224))

    img = np.array(img, dtype=np.float32) / 255.0
    img = np.expand_dims(img, axis=0)

    return img


# Load bird species labels
def load_labels():

    with open("labels.txt", "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


# Create preprocessing images
def create_preprocessing_images(image_path):

    output_folder = "static/processed"
    os.makedirs(output_folder, exist_ok=True)

    img = Image.open(image_path).convert("RGB")
    img = img.resize((224, 224))

    gray = img.convert("L")

    gray_path = os.path.join(output_folder, "gray.jpg")
    gray.save(gray_path)

    threshold = gray.point(
        lambda pixel: 255 if pixel > 127 else 0
    )

    thresh_path = os.path.join(output_folder, "thresh.jpg")
    threshold.save(thresh_path)

    return gray_path, thresh_path


# Generative AI bird description
def generate_description(bird_name):

    if not API_KEY:
        return "OpenAI API key is missing. Check your .env file."

    prompt = f"""
    The bird species is {bird_name}.

    Write four simple lines about:
    - Appearance
    - Habitat
    - Unique features
    - Interesting facts
    """

    payload = {
        "model": "gpt-5-mini",
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_completion_tokens": 150
    }

    try:
        data = json.dumps(payload).encode("utf-8")

        request = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {API_KEY}"
            },
            method="POST"
        )

        with urllib.request.urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))

        return result["choices"][0]["message"]["content"]

    except urllib.error.HTTPError as e:
        error_message = e.read().decode("utf-8", errors="replace")
        return f"OpenAI API error ({e.code}): {error_message}"

    except Exception as e:
        return f"Description generation failed: {str(e)}"
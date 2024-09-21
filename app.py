from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Dict, Tuple
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display
import uuid
import os

app = FastAPI()

# Ensure the output directory exists
OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Mount the output directory to serve static files
app.mount("/images", StaticFiles(directory=OUTPUT_DIR), name="images")

# Define the request model
class TextItem(BaseModel):
    content: str
    font_size: int = Field(..., gt=0)
    position: Tuple[int, int]  # (x, y) coordinates

class CertificateRequest(BaseModel):
    texts: Dict[str, TextItem]

# Endpoint to generate certificate
@app.post("/generate_certificate")
def generate_certificate(request: CertificateRequest):
    try:
        # Open the background image
        background_path = "background.jpg"
        if not os.path.exists(background_path):
            raise HTTPException(status_code=500, detail="Background image not found.")
        background = Image.open(background_path).convert("RGB")
        draw = ImageDraw.Draw(background)

        # Load fonts
        fonts = {}
        for key, item in request.texts.items():
            font_file = "./nazaninbold.ttf" if "bold" in key.lower() else "./nazanin.ttf"
            font_path = font_file
            if not os.path.exists(font_path):
                raise HTTPException(status_code=500, detail=f"Font file {font_path} not found.")
            fonts[key] = ImageFont.truetype(font_path, item.font_size)

        # Process and draw each text
        for key, item in request.texts.items():
            reshaped_text = arabic_reshaper.reshape(item.content)
            bidi_text = get_display(reshaped_text)
            font = fonts[key]
            bbox = draw.textbbox((0, 0), bidi_text, font=font)
            text_width = bbox[2] - bbox[0]
            adjusted_x = item.position[0] - text_width  # Adjust for RTL
            draw.text((adjusted_x, item.position[1]), bidi_text, font=font, fill="black")

        # Save the image with a unique filename
        image_id = uuid.uuid4().hex
        output_filename = f"certificate_{image_id}.jpg"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        background.save(output_path)

        # Construct the image URL
        image_url = f"/images/{output_filename}"

        return JSONResponse(content={"image_url": image_url})

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

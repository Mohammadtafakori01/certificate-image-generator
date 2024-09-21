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
        background_path = "./background.jpg"
        if not os.path.exists(background_path):
            raise HTTPException(status_code=500, detail="Background image not found.")
        
        background = Image.open(background_path).convert("RGB")
        draw = ImageDraw.Draw(background)

        # Load fonts
        fonts = {}
        for key, item in request.texts.items():
            # Choose font based on whether it's bold or not
            if "bold" in key.lower():
                font_file = "./nazaninbold.ttf"  # Ensure this font supports Persian
            else:
                font_file = "./nazanin.ttf"      # Ensure this font supports Persian
            
            if not os.path.exists(font_file):
                raise HTTPException(status_code=500, detail=f"Font file {font_file} not found.")
            
            fonts[key] = ImageFont.truetype(font_file, item.font_size)

        # Process and draw each text
        for key, item in request.texts.items():
            # Reshape and reorder the text for RTL
            reshaped_text = arabic_reshaper.reshape(item.content)
            bidi_text = get_display(reshaped_text)

            font = fonts[key]
            
            # Calculate text size
            text_width, text_height = draw.textsize(bidi_text, font=font)

            x, y = item.position

            # Adjust x-coordinate for RTL by subtracting text width
            adjusted_x = x - text_width

            # Draw the text onto the image
            draw.text((adjusted_x, y), bidi_text, font=font, fill="black")

        # Save the image with a unique filename
        image_id = uuid.uuid4().hex
        output_filename = f"certificate_{image_id}.jpg"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        background.save(output_path)

        # Construct the image URL
        image_url = f"/images/{output_filename}"

        return JSONResponse(content={"image_url": image_url})

    except HTTPException as he:
        # Re-raise HTTP exceptions to be handled by FastAPI
        raise he
    except Exception as e:
        # Catch-all for other exceptions
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

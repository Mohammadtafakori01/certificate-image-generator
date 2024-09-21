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
import logging

app = FastAPI()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        logger.info("Starting certificate generation")
        
        # Open the background image
        background_path = "./background.jpg"
        if not os.path.exists(background_path):
            logger.error("Background image not found.")
            raise HTTPException(status_code=500, detail="Background image not found.")
        
        background = Image.open(background_path).convert("RGB")
        draw = ImageDraw.Draw(background)
        logger.info("Background image loaded successfully.")
        
        # Load fonts
        fonts = {}
        for key, item in request.texts.items():
            if "bold" in key.lower():
                font_file = "./fonts/nazaninbold.ttf"  # Update path as needed
            else:
                font_file = "./fonts/nazanin.ttf"      # Update path as needed
            
            if not os.path.exists(font_file):
                logger.error(f"Font file {font_file} not found.")
                raise HTTPException(status_code=500, detail=f"Font file {font_file} not found.")
            
            fonts[key] = ImageFont.truetype(font_file, item.font_size)
            logger.info(f"Loaded font for {key}: {font_file} with size {item.font_size}")
        
        # Process and draw each text
        for key, item in request.texts.items():
            logger.info(f"Processing text for {key}")
            reshaped_text = arabic_reshaper.reshape(item.content)
            bidi_text = get_display(reshaped_text)
            font = fonts[key]
            
            x, y = item.position
            logger.info(f"Drawing text '{item.content}' at ({x}, {y}) with font size {item.font_size}")
            
            # Draw text with right alignment using anchor
            draw.text((x, y), bidi_text, font=font, fill="black", anchor="ra")  # 'ra' = right-aligned
            logger.info(f"Text '{item.content}' drawn successfully.")
        
        # Save the image with a unique filename
        image_id = uuid.uuid4().hex
        output_filename = f"certificate_{image_id}.jpg"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        background.save(output_path)
        logger.info(f"Certificate saved to {output_path}")
        
        # Construct the image URL
        image_url = f"/images/{output_filename}"
        logger.info(f"Image URL: {image_url}")
        
        return JSONResponse(content={"image_url": image_url})
    
    except HTTPException as he:
        logger.error(f"HTTPException: {he.detail}")
        raise he
    except Exception as e:
        logger.exception("An unexpected error occurred.")
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

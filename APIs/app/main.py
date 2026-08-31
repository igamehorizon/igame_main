from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends
from scripts import utils as util
from scripts.pydantic_model import StoryPrompt, AestheticsMessage, Text2ImgRequest, Img2ImgRequest
import time
from PIL import Image, ImageOps, ImageDraw, ImageFont
from io import BytesIO
import json
from fastapi import Header, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import StreamingResponse
from fastapi import Response
import sys
import asyncio
from scripts import aesthetics_sdxl_fast as aesth



if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


# Init Parameters
config = util.get_config()
tokenizer, model = util.load_model_and_tokenizer(config)
app = FastAPI(title="AI Functionalities API")

# Post Generate
@app.post("/generate_story")
async def generate_text(req: StoryPrompt):
    try:
        print(req)
        # Step 1: Format prompt
        start = time.time()
        max_new_tokens = 256
        text = util.build_prompt(req, max_new_tokens=max_new_tokens)


        # Step 2: generate response
        response = util.model_generation(text, model, tokenizer, max_new_tokens=max_new_tokens)
        end = time.time()
        print(f"Inference Time: {end - start:.2f} sec")



        return {"generated_story": response}

    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))
    

def parse_aesthetics_message(req: str = Form(...)) -> AestheticsMessage:
    """Parse JSON string from form data into AestheticsMessage"""
    try:
        data = json.loads(req)
        return AestheticsMessage(**data)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=422, detail=f"Invalid JSON: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid aesthetics data: {str(e)}")

'''
@app.post("/generate_image")
# def generate_image(req: AestheticsMessage, image: UploadFile = File(...)):
async def generate_image(
    image: UploadFile = File(...),
    req: AestheticsMessage = Depends(parse_aesthetics_message)
):   
    try:
        print(req)
        # Step 1: Format prompt
        start = time.time()
        #prompt = util.build_sd_prompts(req)
        prompt_text = util.build_sd_prompts(req)
        # Read file bytes
        data = await image.read()

        # Load PIL image (the line you asked about)
        img = Image.open(BytesIO(data))
        img = ImageOps.exif_transpose(img)  # fix orientation
        img = img.convert("RGB")            # ensure RGB (or use "RGBA" if you want alpha)

        
        out_img = util.model_generation_image(prompt_text, img)

        end = time.time()
        print(f"Inference Time: {end - start:.2f} sec")

        # ----- Return as PNG bytes -----
        buf = BytesIO()
        out_img.save(buf, format="PNG")
        buf.seek(0)

        # 'inline' helps browsers/Swagger show it; you can change filename
        headers = {"Content-Disposition": 'inline; filename="generated.png"'}

        return StreamingResponse(buf, media_type="image/png", headers=headers)
 
    except Exception as e:
            raise HTTPException(status_code=422, detail=str(e))
'''
# ---------------------------
# Multipart JSON parser (img2img)
# ---------------------------
def parse_img2img_message(req: str = Form(...)) -> Img2ImgRequest:
    """Parse JSON string from multipart form field 'req' into Img2ImgRequest."""
    try:
        data = json.loads(req)
        return Img2ImgRequest(**data)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=422, detail=f"Invalid JSON in 'req': {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid request data: {str(e)}")


# ---------------------------
# Helper: image loading
# ---------------------------
async def load_upload_as_pil_rgb(image: UploadFile) -> Image.Image:
    data = await image.read()
    try:
        img = Image.open(BytesIO(data))
    except Exception:
        raise HTTPException(status_code=422, detail="Uploaded file is not a valid image.")

    img = ImageOps.exif_transpose(img)   # normalize orientation
    img = img.convert("RGB")             # SDXL Turbo expects RGB
    return img


# ---------------------------
# Helper: strength mapping
# ---------------------------
def map_strength_ui_to_effective(strength_ui: float) -> float:
    """
    Map UI slider [0..1] into safer effective range.
    Keeps img2img stable and avoids extremes.
    """
    strength_ui = max(0.0, min(1.0, float(strength_ui)))
    lo, hi = 0.25, 0.85
    return lo + strength_ui * (hi - lo)

def parse_text2img_req(req: Text2ImgRequest) -> Text2ImgRequest:
    # plain JSON body, no form parsing needed
    return req

def parse_img2img_req(req: str = Form(...)) -> Img2ImgRequest:
    try:
        data = json.loads(req)
        return Img2ImgRequest(**data)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=422, detail=f"Invalid JSON: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid img2img data: {str(e)}")


# ---------------------------
# Helper: watermark
# ---------------------------
def add_watermark(img: Image.Image) -> Image.Image:
    draw = ImageDraw.Draw(img)
    text = "AI-GENERATED"
    font_size = max(18, img.width // 40)
    font = None
    for path in ["arial.ttf", "C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"]:
        try:
            font = ImageFont.truetype(path, font_size)
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font)
    text_h = bbox[3] - bbox[1]
    margin = 14
    x = margin
    y = img.height - text_h - bbox[1] - margin
    draw.text((x, y), text, font=font, fill=(255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0))
    return img


# ---------------------------
# Endpoint 1: text2img (JSON)
# ---------------------------
#@app.post("/v1/aesthetics/text2img")
@app.post("/generate_image")
async def generate_text2img(req: Text2ImgRequest):
    try:
        start = time.time()

        # Build prompt using your existing prompt builder
        # You will update util.build_sd_prompts() to accept this new req format.
        #prompt_text = aesth.build_prompt_text2img(req.style, req.prompt)
        prompt_text = util.build_sd_prompts_text2img(req.style, req.prompt)


        # Generate (no input image)
        out_img = aesth.text2img(prompt_text)
        #out_img = util.text2img(prompt_text)

        end = time.time()
        print(f"[text2img] Inference Time: {end - start:.2f} sec")

        out_img = add_watermark(out_img)
        buf = BytesIO()
        out_img.save(buf, format="PNG")
        buf.seek(0)
        headers = {"Content-Disposition": 'inline; filename="text2img.png"'}
        return StreamingResponse(buf, media_type="image/png", headers=headers)

    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))


# ---------------------------
# Endpoint 2: img2img (multipart)
# ---------------------------
#@app.post("/v1/aesthetics/img2img")
@app.post("/stylise_image")
async def generate_img2img(
    image: UploadFile = File(...),
    req: Img2ImgRequest = Depends(parse_img2img_message),
):
    try:
        start = time.time()

        img = await load_upload_as_pil_rgb(image)

        # Map strength and build prompt
        strength_effective = map_strength_ui_to_effective(float(req.strength))
        #prompt_text = aesth.build_prompt_img2img(req.style, req.prompt)
        prompt_text = util.build_sd_prompts_img2img(req.style, req.prompt)  # req.prompt = style notes

        # Generate using SDXL-fast img2img
        out_img = aesth.img2img(prompt_text, img, float(req.strength))
        #out_img = util.img2img(prompt_text, img, strength_effective)


        end = time.time()
        print(f"[img2img] Inference Time: {end - start:.2f} sec")

        out_img = add_watermark(out_img)
        buf = BytesIO()
        out_img.save(buf, format="PNG")
        buf.seek(0)
        headers = {"Content-Disposition": 'inline; filename="img2img.png"'}
        return StreamingResponse(buf, media_type="image/png", headers=headers)

    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))


# Get Health
@app.get("/health")
async def health():
    return {"status": "ok"}

@app.head("/health", include_in_schema=False)
def health_head():
    return Response(status_code=200)
'''

HEALTH_KEY = "put-a-long-random-string-here"

@app.get("/health", include_in_schema=False)
def health(x_health_key: str | None = Header(default=None)):
    if x_health_key != HEALTH_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return {"status": "ok"}

'''
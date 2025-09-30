from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends
from scripts import utils as util
from scripts.pydantic_model import StoryPrompt, AestheticsMessage
import time
from PIL import Image, ImageOps
from io import BytesIO
import json

from fastapi.responses import StreamingResponse
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



# Get Health
@app.get("/health")
async def health():
    return {"status": "ok"}


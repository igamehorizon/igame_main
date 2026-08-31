# app/scripts/aesthetics_sdxl_fast.py
import threading
import torch
from diffusers import AutoPipelineForText2Image, AutoPipelineForImage2Image
from PIL import Image

MODEL_ID = "stabilityai/sdxl-turbo"

_lock = threading.Lock()
_t2i = None
_i2i = None
_device = "cuda"
_dtype = torch.float16

STYLE_SUFFIX = {
    "retro": "retro game art, vintage color palette, subtle film grain, 1980s poster vibe",
    "cartoon": "clean cartoon style, bold outlines, simplified shading, vibrant flat colors",
    "minimalistic": "minimalist design, simple geometric shapes, flat colors, lots of negative space",
    "stylised": "stylized concept art, exaggerated forms, painterly textures, dramatic lighting",
    "realistic": "highly detailed, realistic materials, natural lighting, sharp focus, cinematic",
}

def _ensure_loaded():
    global _t2i, _i2i
    if _t2i is not None and _i2i is not None:
        return
    with _lock:
        if _t2i is not None and _i2i is not None:
            return
        _t2i = AutoPipelineForText2Image.from_pretrained(
            MODEL_ID,
            torch_dtype=_dtype,
            variant="fp16" if _dtype == torch.float16 else None,
        ).to(_device)

        _i2i = AutoPipelineForImage2Image.from_pretrained(
            MODEL_ID,
            torch_dtype=_dtype,
            variant="fp16" if _dtype == torch.float16 else None,
        ).to(_device)

def build_prompt_text2img(style: str, prompt: str) -> str:
    base = " ".join((prompt or "").split())
    suffix = STYLE_SUFFIX.get(style, "")
    return f"{base}, {suffix}" if suffix else base

def build_prompt_img2img(style: str, style_notes: str) -> str:
    suffix = STYLE_SUFFIX.get(style, "")
    notes = " ".join((style_notes or "").split())
    preserve = "Preserve the original composition, layout, and main shapes. Do not add new objects or text."
    parts = [preserve]
    if suffix:
        parts.append(f"Apply this style: {suffix}.")
    if notes:
        parts.append(f"Style notes: {notes}.")
    return " ".join(parts)

def map_strength_ui_to_effective(x: float) -> float:
    x = max(0.0, min(1.0, float(x)))
    lo, hi = 0.25, 0.85
    return lo + x * (hi - lo)

def text2img(prompt: str) -> Image.Image:
    _ensure_loaded()
    img = _t2i(
        prompt=prompt,
        num_inference_steps=4,
        guidance_scale=0.0,
        height=1024,
        width=1024,
    ).images[0]
    return img

def img2img(prompt: str, init_image: Image.Image, strength_ui: float) -> Image.Image:
    _ensure_loaded()
    strength = map_strength_ui_to_effective(strength_ui)
    img = _i2i(
        prompt=prompt,
        image=init_image,
        strength=strength,
        num_inference_steps=4,
        guidance_scale=0.0,
    ).images[0]
    return img

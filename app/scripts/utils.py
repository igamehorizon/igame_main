import torch
import yaml
from transformers import AutoTokenizer, AutoModelForCausalLM
from PIL import Image
from io import BytesIO
from diffusers import StableDiffusionImg2ImgPipeline
from typing import Optional, Union

# Keep your 5-style mapping exactly as in the demo config
STYLE_SUFFIX = {
    "retro": (
        "retro game art, vintage color palette, "
        "subtle film grain, 1980s poster vibe"
    ),
    "cartoon": (
        "clean cartoon style, bold outlines, "
        "simplified shading, vibrant flat colors"
    ),
    "minimalistic": (
        "minimalist design, simple geometric shapes, "
        "flat colors, lots of negative space"
    ),
    "stylised": (
        "stylized concept art, exaggerated forms, "
        "painterly textures, dramatic lighting"
    ),
    "realistic": (
        "highly detailed, realistic materials, "
        "natural lighting, sharp focus, cinematic"
    ),
}

# Optional: a gentle negative prompt to reduce artifacts (Turbo often uses guidance=0)
NEGATIVE_HINT = (
    "blurry, low resolution, jpeg artifacts, watermark, "
    "text artifacts, deformed, extra limbs, distorted"
)

def _clean(s: Optional[str]) -> str:
    """Collapse whitespace, tolerate None."""
    return " ".join((s or "").split()).strip()


def _style_suffix(style: str) -> str:
    """Resolve style id to suffix text."""
    s = _clean(style).lower()

    # accept both UI keys and old enum labels
    aliases = {
        "retro style": "retro",
        "cartoon style": "cartoon",
        "minimalistic style": "minimalistic",
        "stylised style": "stylised",
        "realistic style": "realistic",
    }
    s = aliases.get(s, s)

    return STYLE_SUFFIX.get(s, "")

def build_sd_prompts_text2img(style: str, prompt: str) -> str:
    """
    Text2img:
    - user describes the scene/subject/mood
    - we append the chosen style suffix
    """
    base = _clean(prompt)
    suffix = _style_suffix(style)
    #suffix = STYLE_SUFFIX.get(_style_key(style), "")
    '''
    if not base and not suffix:
        return ""
    if suffix:
        return f"{base}, {suffix}" if base else suffix
    return base
    '''
    if base and suffix:
        return f"{base}, {suffix}"
    return base or suffix


def build_sd_prompts_img2img(style: str, style_notes: Optional[str] = "") -> str:
    """
    Img2img:
    - user does NOT need to describe the image content
    - we internally add a "preserve structure" scaffold to reduce semantic drift
    - user prompt is treated as *style notes only*
    """
    suffix = _style_suffix(style)
    #suffix = STYLE_SUFFIX.get(_style_key(style), "")
    notes = _clean(style_notes)

    # LONG
    '''
    preserve = (
        "Preserve the original image content, subject, and scene. "
        "Preserve the composition, layout, and main shapes/edges. "
        "Do not add, remove, or replace objects. "
        "Only change rendering style, colors, materials, shading, and texture."
    )

    parts = [preserve]
    if suffix:
        parts.append(f"Apply this style: {suffix}.")
    if notes:
        parts.append(f"Style notes: {notes}.")
    return " ".join(parts)
    '''

    #SHORT
    preserve = (
        "Preserve the original subject and scene. Preserve composition and main shapes. "
        "Do not add, remove, or replace objects. Only change colors, textures, lighting, and rendering style."
    )

    # Keep it SHORT to avoid CLIP truncation
    parts = [preserve]
    if suffix:
        parts.append(suffix)
    if notes:
        parts.append(notes)

    return ", ".join(parts)


def build_negative_prompt(use_negative: bool = False) -> Optional[str]:
    """
    For SDXL-turbo you usually run guidance_scale=0.0.
    Negative prompts have little effect at guidance=0; keep this off by default.
    """
    return NEGATIVE_HINT if use_negative else None


TOKENS = 128

# Load configuration
def get_config():
    with open("config/config.yaml") as f:
        config = yaml.safe_load(f)
    return config

# Load Model and Tokenizer
def load_model_and_tokenizer(config):
    # Check for GPU
    
    if config["model"]["device"] == "cuda":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = "cpu"
    print('Device: ', device)

    # Check for bfloat16
    if config["model"]["dtype"] == "bfloat16":
        if torch.cuda.is_bf16_supported():
            torch_dtype = torch.bfloat16
        else:
            torch_dtype = torch.float16
    else:
        torch_dtype = torch.float16

    model = AutoModelForCausalLM.from_pretrained(
            config["model"]["base_model_path"],
            device_map=device,
            torch_dtype=torch_dtype,
            trust_remote_code=True,
        )

    model.eval().to(device)
    total_bytes = sum(p.numel() * p.element_size() for p in model.parameters())
    model_size_gb = total_bytes / (1024 ** 3)
    print(f"Estimated model size: {model_size_gb:.2f} GB")
    print("---Successfully Merged and Unload Peft Model.---")
    tokenizer = AutoTokenizer.from_pretrained(config["model"]["base_model_path"])

    return tokenizer, model


# Model generation
def model_generation(text, model, tokenizer, max_new_tokens=TOKENS):



    messages = [
    {"role": "user", "content":text}
    ]
    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )

    inputs = tokenizer(text, return_tensors="pt").to(model.device)
    with torch.no_grad():
        output = model.generate(
        **inputs,
        max_new_tokens=max_new_tokens,
        temperature=0.2,
        top_p=0.8,
        do_sample=True
        )
    input_len = inputs['input_ids'].shape[1]
    response = tokenizer.decode(output[0][input_len:], skip_special_tokens=True)

    return response
   

# Construct chat prompt

def build_prompt(message, max_new_tokens=TOKENS):
    """
    Build a clean, production-ready storytelling prompt from a StoryPrompt-like object.
    Expected attrs on `message`:
      - objectives (str | None)
      - genre (str | None)
      - plot (str | None)              # plot archetype
      - tone (str | None)
      - extra_prompt (str | None)
    """
    from scripts.pydantic_model import PLOT_INFO, PlotTitle

    def line(label, value):
        value = (value or "").strip()
        return f"{label}: {value}\n" if value else ""

    # Core header
    prompt_parts = [
        "You are a gifted storyteller. Produce polished, original fiction that follows the brief exactly and never explains its private reasoning.",
        "When uncertain, make the best good-faith assumption and proceed—no clarifying questions.\n",
        "Do not include explanations, thinking or meta text—return only the requested output. Take into account the following characteristics of the story\n",
    ]

    # Brief (include only when present)
    brief = ""
    brief += line("Objective", getattr(message, "objectives", None))
    brief += line("Genre", getattr(message, "genre", None))

    # Handle plot with detailed info
    plot_title = getattr(message, "plot", None)
    if plot_title:
        plot_title_str = (plot_title or "").strip()
        # Try to find matching plot in PLOT_INFO
        plot_info_found = False
        for plot_enum, (description, reference) in PLOT_INFO.items():
            if plot_enum.value.casefold() == plot_title_str.casefold():
                brief += f"Plot Archetype: {plot_enum.value}\n"
                brief += f"Plot Description: {description}\n"
                brief += f"Universal Reference: {reference}\n"
                plot_info_found = True
                break

        # If not found in PLOT_INFO, just use the raw value
        if not plot_info_found:
            brief += line("Plot Archetype", plot_title)

    brief += line("Tone", getattr(message, "tone", None))
    brief += line("Additional Notes", getattr(message, "usr_prompt", None))
    if brief:
        prompt_parts.append(brief)

    # Lightweight constraints (tweak as needed)
    prompt_parts.append(
        "Constraints:\n"
        f"- Target length: {max_new_tokens} tokens maximum.\n"
        #"- Clear arc with beginning → middle → end.\n"
        #"- Show, don't tell; concrete sensory detail; strong verbs.\n"
        #"- Avoid clichés and generic filler; keep it culturally respectful.\n"
        #"- End with a resonant image or line that ties back to the Objective.\n"
    )
    """
    # Output format (helps models stay on track)
    prompt_parts.append(
        "Return:\n"
        "1) A compelling title (on its own line).\n"
        "2) The story (no meta commentary).\n"
    )
    """
    prompt = "\n".join(part.strip() for part in prompt_parts if part and part.strip())

    print(prompt)

    return prompt


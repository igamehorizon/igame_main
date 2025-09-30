import torch
import yaml
from transformers import AutoTokenizer, AutoModelForCausalLM
from PIL import Image
from io import BytesIO
from diffusers import StableDiffusionImg2ImgPipeline

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
   
       
def model_generation_image(prompt, image):
       
    device = "cuda"
    pipe = StableDiffusionImg2ImgPipeline.from_pretrained("nitrosocke/Ghibli-Diffusion", torch_dtype=torch.float16).to(
        device
    )

    generator = torch.Generator(device=device).manual_seed(1024)
    image = pipe(prompt=prompt, image=image, strength=0.75, guidance_scale=7.5, generator=generator).images[0]
    
    return image


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


# ---------- Prompt builder ----------
def build_sd_prompts(msg):

    def _part(label, value):
        return f"{label}: {value}" if value else None

    # Generate prompt from aesthetics template
    tech = msg.technology.value if msg.technology else "2D/3D"
    bits = [f"{tech} game visual"]
    if msg.char_env_item:
        bits.append(f"{msg.char_env_item.value.lower()} for characters, environments, and items")
    if msg.typo_menu:
        bits.append(f"{msg.typo_menu.value.lower()} for typography and menus")
    if msg.maps:
        bits.append(f"{msg.maps.value.lower()} for maps")
    core = ", ".join(bits).rstrip(", ") + "."
    

    constraints = list(filter(None, [
        _part("Game Visual Style (Characters/Environments/Items)", msg.char_env_item.value if msg.char_env_item else None),
        _part("Typography & Menus", msg.typo_menu.value if msg.typo_menu else None),
        _part("Maps", msg.maps.value if msg.maps else None),
        _part("Art Technology", msg.technology.value if msg.technology else None),
    ]))

    constraint_block = ""
    if constraints:
        constraint_block = "\n\n[Style Constraints]\n" + "\n".join(constraints)

    positive_prompt = core + constraint_block

    return positive_prompt
    
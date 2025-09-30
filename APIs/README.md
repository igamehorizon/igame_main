# AI Functionalities API

A FastAPI service for AI-powered story generation and image aesthetics, featuring:
- **Story Generation**: Create interactive fiction using advanced language models
- **Image Aesthetics**: Generate stylized game visuals with customizable parameters

- Try the API in http://160.40.52.45:8000/docs#/default

## Table of Contents
- [API Endpoints](#api-endpoints)
- [Installation & Setup](#installation--setup)
- [Configuration](#configuration)
- [Project Structure](#project-structure)
- [Hardware Requirements](#hardware-requirements)

---

## API Endpoints

### POST `/generate_story`
Generate interactive stories with customizable parameters.

**Request Body:**
```json
{
  "objectives": "Create an adventure story",
  "genre": "Action-Adventure",
  "plot": "In Search of Treasure",
  "tone": "Dramatic",
  "usr_prompt": "A young explorer discovers an ancient map"
}
```

**Available Options:**
- **Genres**: Action-Adventure, Platform, Puzzle, Role Playing, Simulation, Strategy, Survival
- **Tones**: Active, Serious, Ironic, Humorous, Fantastic, Popular, Elevated, Loving, Magic, Dramatic
- **Plot Archetypes**: In Search of Treasure, The Return to Home, Self-Knowledge, The Pact with the Devil, and more

**Response:**
```json
{
  "generated_story": "Title: The Cartographer's Legacy\n\nStory content here..."
}
```

### POST `/generate_image`
Generate stylized game visuals from uploaded images. The prompt is automatically generated from the aesthetics parameters using a template.

**Request Format:** `multipart/form-data`

**Parameters:**
- `image`: Upload file (PNG/JPG) - **Required**
- `req`: JSON string with aesthetics parameters - **Required**

**Aesthetics JSON Structure:**
```json
{
  "char_env_item": "Retro style",
  "typo_menu": "Minimalistic style",
  "maps": "Realistic style",
  "technology": "Pixel Art"
}
```

**Available Style Options:**
- **Visual Styles** (for `char_env_item`, `typo_menu`, `maps`):
  - `"Retro style"`
  - `"Cartoon style"`
  - `"Minimalistic style"`
  - `"Stylised style"`
  - `"Realistic style"`
- **Technology Options** (for `technology`):
  - `"Pixel Art"`
  - `"2D Illustration"`
  - `"Vectorised"`
  - `"Polygons"`
  - `"Voxels"`
  - `"2.5D"`

**Response:** PNG image file (image/png)

**Important Notes:**
- The prompt for image generation is **automatically constructed** from the aesthetics parameters using a template
- All aesthetics fields are optional - the system will use defaults if not provided
- The JSON string must be properly formatted and passed as a form field

### GET `/health`
Service health check.

**Response:**
```json
{
  "status": "ok"
}
```

---

## Installation & Setup

### Prerequisites
- Python 3.10+
- NVIDIA GPU with CUDA support (recommended)
- 12+ GB RAM
- You will need your Hugging Face User Access Token to create the yaml file
- Model: Qwen/Qwen3-1.7B



### Installation
```bash
# Clone the repository
git clone <your-repo-url>
cd app

# Install dependencies
pip install -r requirements.txt

# Configure your model settings
# Edit config/config.yaml as needed
```

### Running the API
```bash
# Start the development server
python main.py

# Or use uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8000

# The service will be available at http://localhost:8000
```

---

## Configuration

### Environment Variables
- `DEVICE`: Set to "cuda" for GPU or "cpu" for CPU-only
- `HF_HOME`: Hugging Face cache directory (default: `/app/cache`)

### Model Configuration
Edit `config/config.yaml` to customize:
- Model paths and parameters
- Device settings
- Generation parameters

---

## Project Structure

```
app/
├── main.py                   # FastAPI application
├── scripts/
│   ├── utils.py             # Model utilities & prompt building
│   ├── pydantic_model.py    # Request/response models
│   └── __init__.py
├── config/
│   └── config.yaml          # Model configuration
├── jupyters/                # Development notebooks
│   ├── milestone1_exploration.ipynb
│   └── milestone2_finetuning.ipynb
├── requirements.txt         # Python dependencies
└── README.md               # This file
```

---

## Hardware Requirements

### Minimum Requirements
- **CPU**: 4-core x86_64 processor
- **RAM**: 12 GB system memory
- **GPU**: NVIDIA GPU with 8GB+ VRAM (for optimal performance)
- **Disk**: 10 GB free space for models and cache

### Recommended Configuration
- **CPU**: 8+ core processor (AMD Ryzen 7, Intel i7+)
- **RAM**: 16-32 GB system memory
- **GPU**: NVIDIA RTX 3080/4070 or better
- **Disk**: 20+ GB SSD storage

### CPU-Only Mode
- **CPU**: 8+ core processor
- **RAM**: 16+ GB system memory
- **Disk**: 15+ GB free space
- **Note**: Significantly slower inference times

---

## Usage Examples

### Story Generation
```bash
curl -X POST http://localhost:8000/generate_story \
  -H "Content-Type: application/json" \
  -d '{
    "objectives": "Create a magical adventure",
    "genre": "Fantasy",
    "plot": "In Search of Treasure",
    "tone": "Magic",
    "usr_prompt": "A wizard seeks the lost crystal of power"
  }'
```

### Image Generation
```bash
curl -X POST http://localhost:8000/generate_image \
  -F "image=@input.jpg" \
  -F 'req={"technology": "Pixel Art", "char_env_item": "Stylised style", "typo_menu": "Minimalistic style", "maps": "Retro style"}' \
  --output generated_image.png
```

---

## Development

### Development Mode
```bash
# Install dependencies
pip install -r requirements.txt

# Start with auto-reload for development
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### API Documentation
Once running, visit:
- Interactive docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

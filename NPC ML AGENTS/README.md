# ML-Agents Docker Setup Guide

This guide documents the full installation and setup of **Unity ML-Agents** using Docker.  
It includes instructions for building the Docker container, running training, and handling common issues like NumPy deprecation warnings.

---


## 1️⃣ Docker Setup

### Step 1: Install Docker
- Ensure Docker is installed on your machine (tested with version 28.0.1).  
- GPU support is optional; this guide focuses on CPU-only setup.

### Step 2: Dockerfile

Example Dockerfile for ML-Agents:

```dockerfile
FROM python:3.9-slim
WORKDIR /ml-agents

RUN apt-get update && apt-get install -y git wget unzip \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip setuptools wheel
RUN git clone --branch release_20 https://github.com/Unity-Technologies/ml-agents.git
RUN pip install -e ml-agents/ml-agents-envs \
    && pip install -e ml-agents/ml-agents
RUN pip install tensorflow-cpu
RUN pip install --no-cache-dir --force-reinstall --no-deps protobuf==3.20.*
RUN pip install --no-cache-dir --force-reinstall "numpy<2"

# Patch deprecated np.float globally
RUN echo "import numpy as np; np.float = float" > /usr/local/lib/python3.9/site-packages/sitecustomize.py

CMD ["/bin/bash"]

## 3. Build the Docker Image:

cd <repo-root>/MLAgentsDemo/mlagents-docker
docker build -t ml-agents-docker .
docker run -it --rm \
  -v <repo-root>/MLAgentsDemo:/mnt/project \
  ml-agents-docker \
  mlagents-learn /mnt/project/mlagents-docker/trainer_config.yaml \
  --env /mnt/project/MLAgentsDemo.exe \
  --run-id=MLDemoRun \
  --time-scale=20 \
  --no-graphics

Notes:

Replace <repo-root> with the path where you cloned the repository.

--run-id is a unique identifier for the training session.

--time-scale controls how fast the simulation runs.

--no-graphics disables Unity rendering for faster training.


docker run -it --rm \
  -v <repo-root>/MLAgentsDemo:/mnt/project \
  ml-agents-docker


Optional: Interactive Container

To explore the container interactively:

docker run -it --rm \
  -v <repo-root>/MLAgentsDemo:/mnt/project \
  ml-agents-docker


Inside the container, you can run:

mlagents-learn /mnt/project/mlagents-docker/trainer_config.yaml \
  --env /mnt/project/MLAgentsDemo.exe \
  --run-id=TestRun \
  --no-graphics


4️⃣ Notes & Troubleshooting

NumPy np.float Deprecation: Already patched in the Docker image via sitecustomize.py. NumPy version inside the container is <2.0.

Unity Environment: Build your Unity project before training. Place the .exe (Windows) or .x86_64 (Linux) inside the root of MLAgentsDemo/.

Trainer Config: Located at mlagents-docker/trainer_config.yaml. Adjust hyperparameters as needed (learning rate, batch size, buffer size, etc.).

Docker Mount Paths: Ensure you mount the correct folder into /mnt/project. GPU support requires NVIDIA Container Toolkit and drivers.




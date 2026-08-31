## 🔍 Overview

The NPC Training Module allows you to decouple AI training from your local machine by running reinforcement learning models inside a Docker container on a dedicated remote server.

> **Port Note:** The communication pipeline uses fixed port `5004` across all steps (Unity Editor, SSH Tunneling, and Docker) .

---

## ⚙️ Unity Project Configuration

### Phase 1: Build the Foundation
Before setting up the ML-Agents infrastructure, make sure your core game loop is fully functioning :
* Physics and environmental layout
* Controls and interactions 
* Win/loss and reset logic 

### Phase 2: Setting Up the Agent Logic

1. **Configure Communication Port in Unity:**
   - Locate your ML-Agents settings (`ProjectSettings/ML-Agents` or a `.settings` file).
   - Enable **Connect Trainer** and set the **Editor Port** to `5004`.

2. **Add Component: `Behavior Parameters`**
   - **Behavior Name:** Set a unique identifier (this name must match your section title inside your `.yaml` configuration file) .
   - **Vector Observation:** Define `Space Size` (the exact number of state values your agent sees) .
   - **Actions:** Set your `Continuous` or `Discrete` action branches depending on your controls.

3. **Create Your Custom Agent Script:**
   Create a C# script inheriting from `Agent` instead of `MonoBehaviour` and override these core methods:
   - `OnEpisodeBegin()`: Resets the agent and targets to starting positions when a round end.
   - `CollectObservations(VectorSensor sensor)`: Passes real-time world data to the brain.
   - `OnActionReceived(ActionBuffers actions)`: Converts brain outputs into movement forces and assigns rewards via `SetReward()` or `AddReward()`.

4. **Add Component: `Decision Requester`**
   - Attach a `Decision Requester` component to your Agent GameObject [cite: 1]. Without this, your agent will not request actions from the brain and will remain frozen during Play mode [cite: 1].

---

## 🚀 Server Training Workflow (SSH & Docker)

### Step 1: Upload Your Training Configuration
Open a Command Prompt on your local machine and upload your YAML file to your remote workspace folder on the server:

```bash
scp "C:\Path\To\your_config.yaml" orestiss@160.40.54.131:/home/orestiss/workspace/config/
```

### Step 2: Establish the SSH Tunnel
Open a second, separate Command Prompt window on your local machine and start the SSH tunnel [cite: 1]. Keep this window open throughout your entire training session:

```bash
ssh -L 5004:localhost:5004 orestiss@160.40.54.131
```

### Step 3: Launch the Docker Trainer
Inside your main SSH terminal session connected to the server, run the Docker container:

```bash
docker run --name agent_trainer -it --rm \
  -p 5004:5004 \
  -v /home/orestiss/workspace/results:/results \
  -v /home/orestiss/workspace/config:/config \
  igame-npc-trainer mlagents-learn /config/your_config.yaml \
  --run-id=run1 --results-dir=/results --torch
```

Once the terminal initializes and displays:
`[INFO] Listening on port 5004. Start training by pressing the Play button in the Unity Editor...` 

Go to Unity and press **Play** [cite: 1]. Your agent will immediately start training.

---

## 📥 Retrieving and Deploying the Trained Model

Training will automatically complete when it hits `max_steps`, or you can manually stop it anytime by pressing `Ctrl + C` in the server terminal.

1. **Locate Your Trained Model:**
   Your finished model is saved in your workspace output folder:
   `/home/orestiss/workspace/results/run1/` 

2. **Download the ONNX File:**
   Use Command Prompt on your local machine to download the trained brain directly to your project asset directory:
   ```bash
   scp orestiss@160.40.54.131:/home/orestiss/workspace/results/run1/[YourBehaviorName]/*.onnx "C:\Path\To\UnityProject\Assets\Models"
   ```

3. **Deploy in Unity:**
   - Drag the downloaded `.onnx` file into your Unity Project .
   - Drop it into the **Model** slot of your agent's `Behavior Parameters` component.
   - Press **Play** in Unity to watch your trained AI in action!

---

## 🛠️ Troubleshooting & Best Practices

* **Port Conflicts:** Ensure port `5004` is set consistently across Unity Editor Port, SSH tunnel (`5004:localhost:5004`), and Docker `-p 5004:5004` mapping.
* **Container Name In Use:** If the terminal reports a container name conflict, clear it with: `docker rm -f agent_trainer` .
* **Data Persistence:** Workspace folders are volume-mapped (`-v`), meaning your training checkpoints and `.onnx` files are saved on the server even if the container stops .
* **Updating Hyperparameters:** If you modify your `.yaml` file, re-upload it via SCP to the server before restarting your training command.

---

## 🔄 Summary Loop

1. **Design Agent:** Decide what your AI can observe and what actions it can take .
2. **Write Agent Script:** Implement `OnEpisodeBegin`, `CollectObservations`, and `OnActionReceived` .
3. **Push YAML:** Upload your configuration parameters to the server .
4. **Train:** Open the SSH tunnel, start Docker on port `5004`, and press Play in Unity .
5. **Deploy:** Download the `.onnx` file, attach it to `Behavior Parameters`, and test your AI .

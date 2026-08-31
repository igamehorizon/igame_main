## 🔍 Overview

This module enables real-time LLM inference inside Unity scenes [cite: 1]. NPCs maintain consistent personalities, backstory knowledge, and dialogue styles while dynamically responding to player inputs [cite: 1].

---

## 🏗️ Architecture Summary

* **Personality Configuration:** Define backstories, secrets, and tone via structured prompts or JSON files [cite: 1].
* **Prompt Engineering:** System-level constraints guide character boundaries and line limits [cite: 1].
* **Real-Time Inference:** Direct binding between player UI input fields and LLM character instances [cite: 1].

---

## 🛠️ Implementation Steps

### 1. LLM Manager Setup
1. Create an empty GameObject in your scene named `LLM Manager` [cite: 1].
2. Attach the `LLM` script component to it [cite: 1].
3. Enable `Dont Destroy On Load` if persisting across scenes [cite: 1].

### 2. Model Selection & Loading
* **Selected Model:** `Llama 3.2 3B` (or equivalent GGUF weights) [cite: 1].
* **Chat Template:** Select `Llama 3 (chat)` [cite: 1].
* **Trade-off Consideration:** Smaller models (<3B) yield faster execution suitable for lightweight NPCs, while larger models provide richer dialogue at the cost of processing latency [cite: 1].

### 3. Profile & Background Configuration
Attach the `LLM Character` script to any interactive NPC GameObject [cite: 1]:
* Link the `LLM Manager` reference [cite: 1].
* Set character identity parameters [cite: 1]:
  - **Name & Occupation** [cite: 1]
  - **Personality Traits** [cite: 1]
  - **Goals & Secrets** [cite: 1]
  - **Dialogue Style & Line Limits** [cite: 1]

### 4. Automated Batch Allocation (JSON)
For multi-NPC environments, manage profiles centrally using a structured JSON file [cite: 1]:

```json
{
  "profiles": [
    {
      "character_id": "npc_001",
      "name": "Aya",
      "role": "Freelance Graphic Designer",
      "background": "Works from cafes and studios on small creative gigs.",
      "personality": "Calm, witty, and focused.",
      "goals": "Wants to grow her design brand and find steady clients.",
      "dialogue_style": "Replies in short, friendly sentences — never more than two lines."
    },
    {
      "character_id": "npc_002",
      "name": "Marcus",
      "role": "Rideshare Driver",
      "background": "Knows the city by heart from endless rides.",
      "personality": "Relaxed, humorous, quick thinker.",
      "goals": "Dreams of publishing a small story collection.",
      "dialogue_style": "Keeps it casual and brief — a few words, a quick joke, done."
    }
  ]
}
```

Assign profiles in batch using the `NPC Data Assigner` script attached to an empty `NPC Manager` GameObject [cite: 1]:
1. Assign the JSON file to `Json File` [cite: 1].
2. Drag NPC GameObjects into the `Npc Objects` array in matching order [cite: 1].

### 5. User Interface Setup
Connect UI components (e.g., `TMP_InputField`, `TextMeshProUGUI`) via the `AI Response UI` controller component to display real-time streaming dialogue [cite: 1].

### 6. Animation & State Integration
Map NPC response triggers to Mecanim Animator states to mirror conversation tone [cite: 1]:
* **Recommended States:** `Idle`, `Speaking`, `Happy`, `Angry`, `Curious`, `Thinking`, `Neutral Reaction` [cite: 1].

---

## 🎨 Recommended External Resources

* **3D Rigged Characters & Animations:** [Mixamo](https://www.mixamo.com) for rigged assets and conversational motion clips [cite: 1].
* **Environments & Props:** [Sketchfab](https://sketchfab.com) for 3D props and interactive scene elements [cite: 1].

# LLM for Unity — NPC Interaction Overview

This Unity project demonstrates using **LLM for Unity** to create intelligent, dynamic NPCs that interact with the player in a natural, context-aware way.  

---

## 🚀 Key Features

1. **Dynamic NPC Dialogue**  
   - NPCs respond to player input using a connected **Large Language Model (LLM)**.  
   - Dialogue is context-aware and adapts based on NPC personality or role.  

2. **NPC Backgrounds & Profiles**  
   - Assign **unique traits** to each NPC (name, role, goals, personality).  
   - Automatically load NPC profiles from a **Game Design Document (GDD)** in JSON or structured text format.  
   - Dialogue style and behavior are consistent with the background information.  

3. **Dialogue-Driven Animations**  
   - NPCs can **play animations** that match the tone or style of their dialogue.  
   - Supports custom animations, Mixamo, or Unity animation clips.  
   - Animation triggers can be linked to emotions or dialogue intensity.  

4. **Automated Dialogue Flow**  
   - Player input → LLM generates response → NPC displays reply → NPC plays animation.  
   - Optional logging and analytics for reviewing and balancing interactions.  

---

## ⚙️ How It Works

1. **Assign NPC Traits**  
   Each NPC has a profile (personality, role, goals). These influence the LLM when generating dialogue.  

2. **Load Background Info from GDD**  
   NPC profiles can be automatically populated from the GDD.  
   Example:  
   ```json
   {
     "name": "Alyra",
     "role": "Village Healer",
     "personality": "Kind, patient, curious",
     "goals": "Protect villagers, learn new herbs"
   }
````

This profile is passed to the LLM at runtime to shape NPC dialogue.

3. **Define Dialogue-Linked Animations**

   * Connect animations (happy, sad, idle, etc.) to LLM response tags.
   * Example: “excited” reply → trigger animation clip for cheering.

4. **Interaction Flow**

   ```
   Player Input → LLM → NPC Dialogue → NPC Animation → (Optional) Save Log
   ```

---

## 🎯 Benefits

* Simplifies **NPC creation** by combining AI-driven dialogue and predefined behavior.
* Ensures **consistent personalities** across scenes.
* Reduces manual scripting for dialogue/animations.
* Directly integrates **game design documents (GDDs)** into NPC behavior.


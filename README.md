i-Game AI & VR Modules

This repository contains the implementation of the core AI-driven and VR authoring modules developed within the i-Game project. Each module is designed as a reusable component that integrates with Unity and the i-Game platform, supporting co-creation, accessibility, and inclusivity in game development. The repository is structured into separate folders, each with its own codebase and documentation:

World Builder – The central VR authoring tool that allows developers and creators to design immersive environments directly in Unity. It supports importing and editing 3D assets, media, and environmental settings, and integrates seamlessly with the AI Plugin System for adaptive NPCs, storytelling, and procedural content.

NPC Training – Provides reinforcement learning setups using Unity ML-Agents in Dockerized environments, enabling adaptive NPC behavior training and deployment.

NPC Interactions & Dialogues – An LLM-based toolkit for Unity that generates persona-driven NPC conversations, with traits and dialogue auto-extracted from the Game Design Document (GDD).

XAI for Game Balance – A tool that simulates gameplay across diverse player profiles, using explainable AI (e.g. SHAP, LIME) to highlight balance issues in accessible, human-readable ways.

Storytelling Tools – A backend module that generates plots, synopses, and narrative elements from structured co-creation inputs, supporting collaborative GDD authoring.

Aesthetic Tools – A Stable Diffusion–powered service for generating concept art and visual inspiration aligned with chosen game elements and stylistic preferences.

Each folder contains source code, setup instructions, and examples to support integration into Unity workflows.
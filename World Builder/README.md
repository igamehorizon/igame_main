
# World Builder

World Builder is a Unity-based VR scene authoring tool that allows users to create, edit, and experience interactive 3D environments. It supports dynamic runtime asset import, prefab-based instantiation, a powerful scene inspector UI, and VR integration.

# Features
# Scene Creation

- Start from a welcome screen with options to:

- Create Scene: Configure lighting, skybox, plane size, and environment presets.

- Edit Scene: Load a previously saved JSON file and continue editing.

- Play in VR: Launch a scene directly in VR from a JSON file.

# Main Editor Window

Unity-like UI with:

- Bottom toolbar for asset creation.

- Left hierarchy panel listing all scene assets with show/hide and delete options.

- Right inspector panel for editing position, rotation, scale, font size, colors, and world settings.

- Dynamic free camera controls (pan, tilt, zoom).

# Asset Management

All assets are based on prefabs and instantiated dynamically at runtime.

- 3D Models: Import .OBJ and .FBX with textures (auto-loads .MTL if available). Full transform controls and shader editing.

- Images: Import .PNG and .JPEG with full transform controls.

- Videos: Import .MP4, .AVI, .MKV. Play/pause button updates between play and pause sprites at runtime.

- Audio: Import .MP3 and .WAV. Playable inside the editor and VR.

- Text: Add editable text prefabs with a dedicated Text Inspector for font, size, color, and language (English, Spanish, Greek). Integration with FlexibleColorPicker for real-time color editing.

# VR Integration

Configurable XR Rig prefab sets starting VR position and controls.

Export scenes to VR for immersive playback.

# Save / Load System

Scenes are serialized into JSON files containing:

Asset hierarchy and paths

Transform data (position, rotation, scale)

Material and font settings

Scene-wide settings (lighting, skybox, environment, VR position)

JSON files can be reloaded for continued editing or direct VR playback.

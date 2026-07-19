# 🛸 Talon UAV Dataset Generator - Setup & Usage Guide

[![Unreal Engine](https://img.shields.io/badge/Unreal%20Engine-5.5-brightgreen.svg?style=flat-square&logo=unrealengine)](https://www.unrealengine.com)
[![Python](https://img.shields.io/badge/Python-3.x-blue.svg?style=flat-square&logo=python)](https://www.python.org)
[![UE4SS](https://img.shields.io/badge/Modding-UE4SS-orange.svg?style=flat-square)](https://github.com/UE4SS-RE/RE-UE4SS)
[![License](https://img.shields.io/badge/License-MIT-green.svg?style=flat-square)](https://opensource.org/licenses/MIT)

An advanced, high-performance dataset generation pipeline designed for the **Talon UAV (BPP_AIDroneTalon_C)** in *Drones of War*. This system captures high-quality, zero-motion-blur, fullscreen-safe screenshots at a constant 1920x1080 resolution for AI object detection (e.g., YOLO) and coordinate training.

> [!IMPORTANT]
> **🛡️ Built-in Menu Safety (IsInMenu Guard):** 
> Thanks to our smart memory-scanner, the mod instantly detects if you are in the Main Menu, Drone Selection, Lobby, or Pause Screens. It automatically restores all game visual settings and physics, ensuring your UI and menus remain **100% visible, active, and clickable at all times!**
>
> **💾 Smart Index Continuation (Anti-Overwrite):** 
> The Python controller scans the `dataset/` directory at startup, detects the highest existing capture index (e.g., `talon_0150.png`), and automatically starts numbering from `talon_0151.png`. Your files are completely safe!

---

## ⚙️ Automatic Installation

Integrating the mod into your game directory is automated using our helper setup script:

1. Extract the `talon_dataset` folder anywhere on your computer.
2. Right-click inside the folder and select **Open in Terminal** (or open PowerShell/CMD).
3. Execute the setup installer script:
   ```bash
   python setup_installer.py
   ```
4. Enter the absolute path to your game's `Binaries\Win64` directory when prompted:
   * *Example Path:* `C:\Users\Zeylo\Desktop\drones_of_war\Drones of War Teknofest\DronesOfWar\Binaries\Win64`
5. The script will copy files, configure directories, and enable the mod! (`[SUCCESS]` message will be displayed).

---

## 🚀 Execution & Usage Flow

Run the system in your PowerShell terminal using the steps below:

### 1️⃣ STEP: Launch the Game
Open PowerShell and run these commands to launch the game in its shipping environment:

```powershell
# 1. Define the Win64 binary path
$win64 = "C:\Users\Zeylo\Desktop\drones_of_war\Drones of War Teknofest\DronesOfWar\Binaries\Win64"

# 2. Change directory
cd "$win64"

# 3. Launch the game executable
.\DronesOfWar-Win64-Shipping.exe
```

### 2️⃣ STEP: Open the Drone Control GUI (Optional)
If you want to use the customized drone interface panel, open a new PowerShell window and run:

```powershell
# 1. Move to the game directory
cd "C:\Users\Zeylo\Desktop\drones_of_war"

# 2. Launch the Python GUI panel
python drone_gui.py
```

### 3️⃣ STEP: Start the Auto-Capture Controller
Once you spawn the Talon UAV in-game, enter **Spectator Mode**, fly near the drone, and run the capture script in your terminal:

```powershell
python c:\Users\Zeylo\Desktop\talon_dataset\capture_controller.py
```
> [!NOTE]
> The terminal window will automatically minimize itself upon launch to prevent any screen overlap. Quickly click back on the game window and press **F11** to make the game **Tam Ekran (Fullscreen)**!

---

## ⚠️ Important Precautions & Parameters

* **F11 Fullscreen Check:** Make sure the game is strictly running in **F11 Fullscreen** to maintain proper DPI scaling and capture images in flawless 1920x1080 dimensions.
* **Freeze & Fly Interval:** The script freezes the drone and captures 50 unique camera/lighting combinations. Once done, it unfreezes the physics and lets the drone fly freely for exactly **2.5 seconds** (`10 ticks * 250ms`) to transition to a completely new zone in the map before freezing it again.
* **Leak-Free Architecture:** The system has zero memory leaks. It cleans up temporary assets and file systems after every single tick, allowing it to run for days without performance degradation.

---

## 💻 Unreal Engine Developer Console Commands

Open the Unreal console in-game using the tilde (`~` or `"`) key. You can use these specialized developer commands to interact with the Talon UAV and camera system:

```javascript
/**
 * PlayersOnly
 * Freezes all AI actors, physical components, and tick processes in the world.
 * Only the Spectator camera remains unfrozen to move around.
 */

/**
 * ToggleDebugCamera
 * Activates or deactivates the free-roaming developer camera, 
 * decoupled from standard gameplay control.
 */

/**
 * pause
 * Completely pauses the entire game state. Run again to resume.
 */

/**
 * talon_find
 * Searches the active level memory, detects the Talon UAV (BPP_AIDroneTalon_C),
 * and caches its coordinates.
 */

/**
 * talon_stop
 * Instantly freezes the physical movement, momentum, and motors of the Talon UAV.
 */

/**
 * talon_x [value]
 * Snaps the X-axis (Forward/Backward) world coordinates of the Talon UAV to the specified value.
 */

/**
 * talon_y [value]
 * Snaps the Y-axis (Right/Left) world coordinates of the Talon UAV to the specified value.
 */

/**
 * talon_up [value]
 * Teleports the Talon UAV vertically upwards (Z-axis) by the specified units.
 * Example usage: talon_up 2000
 */

/**
 * talon_down [value]
 * Teleports the Talon UAV vertically downwards (Z-axis) by the specified units.
 * Example usage: talon_down 3000
 */

/**
 * talon_move
 * Resumes physics simulation and unfreezes the Talon UAV.
 */

/**
 * talon_front [value]
 * Snaps the Spectator camera directly in front of the Talon UAV at the specified distance.
 * Example usage: talon_front 4000
 */

/**
 * talon_pitch [value]
 * Rotates the vertical pitch angle of the Talon UAV in degrees.
 * Example usage: talon_pitch 20
 */

/**
 * talon_yaw [value]
 * Rotates the horizontal heading angle of the Talon UAV in degrees.
 * Example usage: talon_yaw 45
 */

/**
 * talon_roll [value]
 * Rotates the roll tilt angle of the Talon UAV in degrees.
 * Example usage: talon_roll 30
 */

/**
 * talon_rot
 * Prints the current rotation parameters (Pitch, Yaw, Roll) of the UAV to the console.
 */

/**
 * talon_here
 * Instantly teleports the Talon UAV directly to the Spectator camera's current coordinate.
 */
```

---

*Authored by your AI pair programmer, Antigravity. Have a premium dataset generation session abiciğim! 🚀*

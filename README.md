# CASI (Cunha Artificial Software Intelligence) Agent

A lightweight standalone Windows Desktop Agent that monitors a Firebase collection for pending tasks and utilizes Antigravity capabilities (Computer Use / Browser Tool) to automate local desktop or portal workflows.

## Features

1. **Persistent Listener**: Monitors the `casi_local_tasks` collection on Firebase for tasks mapping to `platform == 'local'` and `status == 'pending'`.
2. **Execution Engine**: Loads textual skill instructions from `.agent/skills/` and runs predefined tool macros.
3. **Safety Guard**: Triggers a Windows system tray toast notification, requiring explicit timeout or intervention before critical "Submit" or "Payment" actions.
4. **Reporting**: Automatically captures a full-screen confirmation page screenshot and uploads it to the local Antigravity Artifact directory as proof, upding the Firebase record to `"status": "completed"`.
5. **Portability**: Packaged as a lightweight, no-console system tray executable utilizing CASI branding.

## Installation / Setup

1. **Prerequisites**: Ensure you have Python installed. The `requirements.txt` file outlines library dependencies (`pyautogui`, `firebase-admin`, `plyer`, `pystray`, `Pillow`, and `pyinstaller`). 

2. **Credentials**: You **must** download your Firebase service account JSON key and rename it to `serviceAccountKey.json`. Place it in the root `c:\CASI_agent` directory. The listener will start automatically when it detects these valid credentials.

3. **Skills definition**: Place any Markdown (`.md`) workflow instructions inside the `c:\CASI_agent\.agent\skills\` directory. The agent parses this directory organically upon triggering a task.

## Compiling to an Executable

To compile CASI to a standalone Windows module:

1. Double-click or run `build_exe.bat` through your shell.
2. The batch script bundles all requirements via `pip` and utilizes `PyInstaller` internally.
3. The packaged agent will output to `c:\CASI_agent\dist\casi_agent.exe`. It includes the auto-generated dark-blue metallic logo in the tray build!

## Running on Windows Startup

1. Open File Explorer.
2. Type `shell:startup` in the address bar to open the Windows Startup folder.
3. Create a shortcut to `dist\casi_agent.exe` and drop it in the Startup folder. Every time your machine boots, CASI will implicitly hide itself in your icon tray and start connecting onto the cloud node.


# Phase 7: Deployment — Sprint 1 (Desktop Packaging)

**To:** Lead AI Developer
**From:** Project Manager
**Date:** March 3, 2026
**Phase:** 7 — Deployment
**Goal:** Package the entire LECAT system (Python + Streamlit + Dependencies) into a standalone executable for distribution to non-technical users.

---

## 1. Objective
Create a "one-click" experience for end-users.
Instead of requiring them to install Python, `pip`, and run command-line scripts, they will receive a zipped folder containing an executable (e.g., `LECAT_Trader.exe`).
When launched, this executable will:
1.  Silently start the backend server.
2.  Automatically open the dashboard in their default web browser.
3.  Clean up processes when closed.

---

## 2. Required File Structure
Add the following files to the project root:

```text
root/
├── run_desktop.py       # The entry point script (bootstrapper)
├── lecat.spec           # PyInstaller build configuration
└── hooks/               # Custom hooks directory (if needed for hidden imports)

```

---

## 3. Implementation Tasks

### Task 1: The Bootstrapper (`run_desktop.py`)

Create a Python script that orchestrates the application launch.

* **Logic:**
1. **Find the Path:** Locate the `lecat/dashboard/app.py` file relative to the executable (handle both "frozen" PyInstaller mode and standard dev mode).
2. **Launch Server:** Use `subprocess.Popen` to run `streamlit run app.py` on a specific port (e.g., 8501).
3. **Launch Browser:** Wait 2 seconds, then use `webbrowser.open("http://localhost:8501")`.
4. **Loop:** Keep the script running to prevent the console window from closing immediately.
5. **Cleanup:** Ensure the streamlit subprocess is killed when the main window closes.



### Task 2: PyInstaller Spec (`lecat.spec`)

Configure the build process to include all necessary data.

* **Hidden Imports:** Explicitly list `streamlit`, `altair`, `plotly`, `pandas`, `sqlite3`, and `lecat` modules.
* **Data Files (`datas`):**
* Map `lecat/dashboard` -> `lecat/dashboard` (The UI code)
* Map `lecat/data/schema.sql` -> `lecat/data` (Database schema)
* Map `lecat/config.yaml` -> `lecat` (Configuration)
* Map `.streamlit/config.toml` -> `.streamlit` (Theme settings)


* **Metadata:** Use `copy_metadata` for:
* `streamlit`
* `plotly`
* `tqdm`
* `regex`
* `packaging`



### Task 3: Build Automation (`Makefile`)

Add a target to the Makefile for easy building.

* **Command:** `make build-desktop`
* **Steps:**
1. Install `pyinstaller`.
2. Clean previous builds (`rm -rf build dist`).
3. Run `pyinstaller lecat.spec --clean --noconfirm`.
4. (Optional) Zip the resulting `dist/LECAT_Trader` folder.



---

## 4. Acceptance Criteria

**Case A: The "Clean Machine" Test**

* **Action:** Copy the `dist/LECAT_Trader` folder to a generic Windows/Mac machine (or a fresh VM) that does **not** have Python installed.
* **Action:** Double-click the executable.
* **Check:**
1. A terminal window opens (can be hidden later, but good for debug now).
2. The default web browser opens to `localhost:8501`.
3. The Dashboard loads and functions correctly (e.g., upload a CSV, run a backtest).



**Case B: Data Persistence**

* **Action:** In the desktop app, upload a CSV file.
* **Check:** Close the app and reopen it. The CSV should still be available (verifies `lecat.db` is being created in a writable location, not inside the temporary `_MEI` folder).

---

**Action:** Generate the code for `run_desktop.py` and `lecat.spec`.


# Phase 5: Release Engineering — Final Polish & Handoff

**To:** Lead AI Developer
**From:** Project Manager
**Date:** March 3, 2026
**Phase:** 5 — Release
**Goal:** Finalize code quality, polish documentation, and prepare the repository for "Release 1.0".

---

## 1. Objective
1.  **Standardize:** Apply strict code formatting (Black/Isort) to ensure the codebase looks professional and consistent.
2.  **Document:** Rewrite the root `README.md` to be a comprehensive landing page (with badges, screenshots placeholders, and quickstart).
3.  **Package:** Create a `pyproject.toml` or `setup.py` so the project can be installed via `pip install .`.
4.  **Verify:** Run the full test suite one last time to ensure no regressions before tagging v1.0.

---

## 2. Required File Structure
Add/Update the following:

```text
root/
├── README.md            # Update: Final Master documentation
├── pyproject.toml       # New: Modern Python packaging config
├── LICENSE              # New: MIT License
├── Makefile             # New: Shortcuts (make test, make format, make run)
└── .gitignore           # Update: Ensure all artifacts are ignored

```

---

## 3. Implementation Tasks

### Task 1: Code Quality (`black` & `isort`)

The code works, but let's make it beautiful.

* **Action:** Run `black lecat/ tests/` and `isort lecat/ tests/`.
* **Config:** Add tool configuration to `pyproject.toml` to enforce line length (88 or 100 chars).

### Task 2: The Master README (`README.md`)

This is the face of the project. It should replace the current incremental updates.

* **Sections Required:**
* **Header:** Project Name & One-line pitch ("Evolutionary Trading Strategy Compiler").
* **Features:** Bullet points (DSL, Time-Travel, Genetic Engine, Web Dashboard).
* **Quickstart:** 3 commands to get running (`pip install`, `streamlit run`).
* **The Language:** A cheat sheet of valid syntax (`RSI(14) > 80`).
* **Architecture:** A simplified Mermaid diagram of the pipeline.
* **Screenshots:** Placeholders for Dashboard images.



### Task 3: Packaging (`pyproject.toml`)

Make it installable.

* Define build system (setuptools).
* Define dependencies (copy from `requirements.txt`).
* Define entry points (optional, e.g., `lecat = lecat.main:main`).

### Task 4: Developer Convenience (`Makefile`)

Create a `Makefile` for common tasks:

* `make install`: Install dependencies.
* `make format`: Run black/isort.
* `make test`: Run pytest.
* `make run`: Launch the dashboard.
* `make clean`: Remove `__pycache__` and logs.

---

## 4. Acceptance Criteria

**Case A: The Clean Install**

* **Action:** `pip install .` inside a fresh virtualenv.
* **Check:** `import lecat` works immediately.

**Case B: The Visual Check**

* **Action:** Open `README.md`.
* **Check:** It looks like a professional GitHub repository (structured, clear headers, code blocks).

**Case C: The Final Test**

* **Action:** `make test`.
* **Check:** All 235 tests pass with Green status.

---

**Action:** Generate the `pyproject.toml`, `Makefile`, and the finalized `README.md`.
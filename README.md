# Project Title (e.g., Automated Screenshot Tool)

   Brief description of the project.

   ## Features

   *   Automatic and manual screenshot capture.
   *   Optional blurring of sensitive information (Numbers, potentially PII based on labels).
   *   Configurable settings via `config.ini`.
   *   Secure storage of API keys via `.env`.
   *   Export captured screenshots to a Word document.
   *   Upload documents/evidence to JIRA and JTMF.
   *   Global hotkeys for common actions.
   *   Logging for diagnostics.

   ## Setup

   1.  **Clone the repository:**
       ```bash
       git clone <your-repository-url>
       cd your_project_root
       ```
   2.  **Create a virtual environment:**
       ```bash
       python -m venv venv
       source venv/bin/activate  # On Windows use `venv\Scripts\activate`
       ```
   3.  **Install dependencies:**
       ```bash
       pip install -r requirements.txt
       ```
   4.  **Install Tesseract OCR:**
       Follow instructions for your OS: [https://tesseract-ocr.github.io/tessdoc/Installation.html](https://tesseract-ocr.github.io/tessdoc/Installation.html)
       Ensure the `tesseract` command is in your system's PATH or update the path in the code if necessary.
   5.  **Download SpaCy Model:**
       ```bash
       python -m spacy download en_core_web_sm
       ```
   6.  **Configure:**
       *   Create a `.env` file (copy `.env.example` if provided) and add your API tokens/secrets.
       *   Review and adjust `config.ini` for settings like save directory, intervals, etc.
   7.  **Place Assets:** Ensure `assets/cd_logo.png` exists.

   ## Usage

   Run the main application:
   ```bash
   python src/main.py
   ```

   *(Add details about hotkeys, UI buttons, etc.)*

   ## Structure

   *   `src/main.py`: Entry point of the application.
   *   `src/app.py`: Main `ScreenshotApp` class and core GUI logic.
   *   `src/config/`: Configuration loading (`.ini`, `.env`) and logging setup.
   *   `src/core/`: Core non-UI logic like hotkey management.
   *   `src/features/`: Modules for specific features (screenshotting, uploading).
   *   `src/ui/`: UI elements like dialogs and separate windows.
   *   `src/utils/`: Utility classes and functions (file handling, image utils).
   *   `assets/`: Static files like icons.
   *   `config.ini`: User-configurable settings.
   *   `.env`: Secret keys (DO NOT COMMIT).
   *   `requirements.txt`: Project dependencies.
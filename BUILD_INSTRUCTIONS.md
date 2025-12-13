# How to Build the Windows Executable

Since this project was developed in a Linux environment, you need to build the final `.exe` file on your Windows machine to ensure compatibility.

## Prerequisites

1.  **Python Installed:** Ensure you have Python installed on your Windows machine.
2.  **Dependencies:** Install the required packages.
    ```powershell
    pip install -r requirements.txt
    ```

## Building the Executable

1.  Open your terminal (Command Prompt or PowerShell) and navigate to the project folder.
2.  Run the following command:

    ```powershell
    pyinstaller --noconfirm --onefile --windowed --name "InvoiceAutomator" gui_launcher.py
    ```

    *   `--onefile`: Bundles everything into a single `.exe` file.
    *   `--windowed`: Hides the console window (since we have a GUI).
    *   `--add-data "config.json;."`: Ensures the config file is bundled (or at least accounted for). *Note: On Windows use `;`, on Linux use `:`.*

## Running the App

1.  Go to the `dist/` folder.
2.  You will find `InvoiceAutomator.exe`.
3.  Run it!

# Project Pipeline: Automated Web Data Extraction

**Goal:** To automate clicking multiple items on a webpage, opening new tabs, extracting data from those tabs, de-duplicating entries, and saving the results to a CSV file.

**Key Constraints & User Preferences:**
*   **User-Friiendliness:** The script must be simple to run for a non-technical user, requiring no complex browser or system setup.
*   **Browser Interaction:** The script must operate on an *existing, logged-in browser session*.
*   **Tab Management:** Original clicked tabs should **NOT** be closed for safety/reference.
*   **Scraping Method Priority:** `Ctrl+A`, `Ctrl+C` on the rendered page content is preferred for perceived speed and simplicity, despite warnings about fragility.
*   **Variable Row Heights:** Handled by over-clicking and content-based de-duplication.

---

### **Phase 1: One-Time Guided Setup**

1.  **Coordinate Capture:** The script will guide the user to provide initial `x, y` coordinates for the first clickable item and the second clickable item.
2.  **Automatic Calculation:** The script calculates `start_x`, `start_y`, and `vertical_spacing` based on user input.
3.  **Configuration Saving:** These coordinates, along with the `NUMBER_OF_CLICKS` (defaulting to e.g., 23 to allow for over-clicking), will be saved to a local configuration file (`config.json` or similar) for persistent use.

---

### **Phase 2: Automated Execution Workflow**

1.  **Countdown:** A 5-second countdown will provide the user time to navigate to and focus on the initial webpage.
2.  **Initial Clicks:**
    *   Using `pyautogui`, the script will perform `NUMBER_OF_CLICKS` (e.g., 23) `Ctrl+Click` actions, opening this many new tabs in the browser.
3.  **Data Extraction & De-duplication Loop:**
    *   The script will then iterate through the newly opened tabs, processing them in reverse order (using `Ctrl+Shift+Tab` to navigate).
    *   For each tab:
        a.  **Wait for Page Content:** A configurable `time.sleep()` pause (e.g., 1-2 seconds) will be implemented to allow page content to render fully.
        b.  **Copy Content:** `pyautogui.hotkey('ctrl', 'a')` followed by `pyautogui.hotkey('ctrl', 'c')` to copy all visible content to the clipboard.
        c.  **Retrieve Content:** `pyperclip.paste()` will retrieve the copied content.
        d.  **De-duplication:** The copied text will be compared against a stored set of previously processed content.
            *   If **duplicate**, the tab is skipped, and the script moves to the next.
            *   If **unique**, the content is added to the "seen" set, and processing continues.
        e.  **Extract Specific Data:** This crucial step requires user-defined patterns (e.g., regular expressions, string splitting) to extract desired fields from the unstructured copied text.
        f.  **Navigate:** `pyautogui.hotkey('ctrl', 'shift', 'tab')` to move to the previous tab for the next iteration.

4.  **Final Output:**
    *   All unique, extracted data will be collected.
    *   The data will be saved into a CSV file (e.g., `extracted_data.csv`).
    *   The full path to the CSV file will be displayed in the terminal.
    *   A completion sound will be played using `beepy`.

---

### **Next Steps:**
*   **Define Data Extraction Patterns:** User needs to provide explicit rules for extracting specific data points from the `Ctrl+A` copied text.
*   **Implementation:** Begin writing the Python script based on this detailed pipeline.

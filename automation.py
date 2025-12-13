import time
import os
import tkinter as tk
from tkinter import messagebox
import pyautogui
import pyperclip
from clicker import perform_clicks
from extractor import parse_invoice_text, format_to_csv_block

# Configuration
OUTPUT_FILE = "extracted_data.csv"
PAGE_LOAD_WAIT = 2.0  # Seconds to wait for a tab to load content

def get_row_count():
    """
    Opens a custom, larger GUI window to ask for the row count.
    """
    # Create the main window
    root = tk.Tk()
    root.title("Invoice Automation Tool")
    
    # Set window size (Width x Height) - Wider as requested
    root.geometry("550x350")
    
    # Variable to store the result
    result = {"count": 20} # Default

    def on_submit(event=None):
        try:
            val = entry.get().strip()
            if not val:
                result["count"] = 20 # Default if empty
            else:
                result["count"] = int(val)
            root.destroy()
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid number.")

    def on_close():
        result["count"] = None # Signal cancellation
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)

    # Main container frame with 7mm-ish padding (approx 25px)
    main_frame = tk.Frame(root, padx=25, pady=25)
    main_frame.pack(fill="both", expand=True)

    # 1. Description Label
    desc_text = (
        "AUTOMATED INVOICE SCRAPER V1.0\n\n"
        "This tool automates the extraction of invoice data.\n"
        "It will click through rows, open tabs, and scrape details.\n\n"
        "Please ensure your browser is open to the list view."
    )
    lbl_desc = tk.Label(main_frame, text=desc_text, justify="center", font=("Helvetica", 11), pady=10)
    lbl_desc.pack(fill="x")

    # 2. Input Frame
    frame_input = tk.Frame(main_frame, pady=20)
    frame_input.pack()

    lbl_prompt = tk.Label(frame_input, text="Rows to process:", font=("Helvetica", 11, "bold"))
    lbl_prompt.pack(side="left", padx=10)

    entry = tk.Entry(frame_input, width=10, font=("Helvetica", 11))
    entry.insert(0, "20") # Default value
    entry.pack(side="left", padx=10)
    entry.bind('<Return>', on_submit) # Allow pressing Enter key
    entry.focus_set()

    # 3. Start Button - FIXED HEIGHT
    # Removed ipady from constructor, applied it via pack()
    btn_start = tk.Button(main_frame, text="START AUTOMATION", command=on_submit, 
                          bg="#4CAF50", fg="white", font=("Helvetica", 12, "bold"), 
                          cursor="hand2", width=20) 
    # Use ipady here to increase vertical size internally
    btn_start.pack(pady=10, ipady=10)

    # Center the window on screen
    root.eval('tk::PlaceWindow . center')

    root.mainloop()
    return result["count"]

def save_data(all_data):
    """Saves the collected data blocks to the CSV file."""
    # Convert all parsed data dictionaries to the formatted CSV blocks
    csv_content = ""
    for data in all_data:
        csv_content += format_to_csv_block(data) + "\n"
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(csv_content)
    
    return os.path.abspath(OUTPUT_FILE)

def main():
    # 1. Get User Input
    row_count = get_row_count()
    if not row_count:
        print("Operation cancelled.")
        return

    print(f"Preparing to process {row_count} rows.")

    # 2. Perform Clicks (Opens tabs)
    # This function handles the 5-second countdown internally
    perform_clicks(row_count)

    # 3. Extraction Loop
    print("\n--- Starting Extraction Loop ---")
    
    collected_data = []
    seen_ids = set() # For de-duplication

    # We iterate through the tabs. 
    # Since we are on the LAST tab opened, we process and then move to PREVIOUS.
    for i in range(row_count):
        print(f"Processing tab {i+1}/{row_count}...")
        
        # A. Wait for content to render
        time.sleep(PAGE_LOAD_WAIT)

        # B. Copy Content (Ctrl+A, Ctrl+C)
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(0.5) 
        pyautogui.hotkey('ctrl', 'c')
        time.sleep(0.5) # Wait for clipboard to update

        # C. Get Text
        raw_text = pyperclip.paste()

        # D. Parse
        parsed_data = parse_invoice_text(raw_text)

        # E. De-duplication Check
        # We use the internal_id or invoice_number as a unique key
        unique_key = parsed_data.get('internal_id')
        if not unique_key or unique_key == "N/A":
            unique_key = parsed_data.get('invoice_number')
        
        if unique_key and unique_key in seen_ids:
            print(f"  -> Duplicate found ({unique_key}). Skipping.")
        else:
            if unique_key:
                seen_ids.add(unique_key)
            collected_data.append(parsed_data)
            print(f"  -> Extracted: {parsed_data.get('invoice_number', 'Unknown')}")

        # F. Navigate to Previous Tab (Ctrl+Shift+Tab)
        if i < row_count - 1: # Don't switch after the last one
            pyautogui.hotkey('ctrl', 'shift', 'tab')
            time.sleep(0.5)

    # 4. Save Results
    if collected_data:
        saved_path = save_data(collected_data)
        print(f"\nSUCCESS! Data saved to:\n{saved_path}")
        # Play success sound (System Bell)
        print('\a')
    else:
        print("\nNo unique data was extracted.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nScript stopped by user.")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
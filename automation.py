import time
import os
import math
import tkinter as tk
from tkinter import messagebox
import pyautogui
import pyperclip
import beepy
from clicker import perform_clicks
from extractor import parse_invoice_text, format_to_csv_block
from config_manager import load_config

# Configuration
OUTPUT_FILE = "extracted_data.csv"
PAGE_LOAD_WAIT = 2.0  # Seconds to wait for a tab to load content

def get_row_count(default_count=20):
    """
    Opens a custom, larger GUI window to ask for the row count.
    """
    # Create the main window
    root = tk.Tk()
    root.title("Invoice Automation Tool")
    
    # Set window size (Width x Height)
    root.geometry("550x350")
    
    # Variable to store the result
    result = {"count": default_count}

    def on_submit(event=None):
        try:
            val = entry.get().strip()
            if not val:
                result["count"] = default_count
            else:
                result["count"] = int(val)
            root.destroy()
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid number.")

    def on_close():
        result["count"] = None # Signal cancellation
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)

    # Main container frame
    main_frame = tk.Frame(root, padx=25, pady=25)
    main_frame.pack(fill="both", expand=True)

    # 1. Description Label
    desc_text = (
        "AUTOMATED INVOICE SCRAPER V1.1\n\n"
        "1. Enter number of rows.\n"
        "2. Script will click rows + 15% extra.\n"
        "3. Scrapes tabs until returning to original page.\n\n"
        "Ensure browser is open to the list view."
    )
    lbl_desc = tk.Label(main_frame, text=desc_text, justify="center", font=("Helvetica", 11), pady=10)
    lbl_desc.pack(fill="x")

    # 2. Input Frame
    frame_input = tk.Frame(main_frame, pady=20)
    frame_input.pack()

    lbl_prompt = tk.Label(frame_input, text="Rows to process:", font=("Helvetica", 11, "bold"))
    lbl_prompt.pack(side="left", padx=10)

    entry = tk.Entry(frame_input, width=10, font=("Helvetica", 11))
    entry.insert(0, str(default_count)) 
    entry.pack(side="left", padx=10)
    entry.bind('<Return>', on_submit) 
    entry.focus_set()

    # 3. Start Button
    btn_start = tk.Button(main_frame, text="START AUTOMATION", command=on_submit, 
                          bg="#4CAF50", fg="white", font=("Helvetica", 12, "bold"), 
                          cursor="hand2", width=20) 
    btn_start.pack(pady=10, ipady=10)

    root.eval('tk::PlaceWindow . center')
    root.mainloop()
    return result["count"]

def save_data(all_data):
    """Saves the collected data blocks to the CSV file."""
    csv_content = ""
    for data in all_data:
        csv_content += format_to_csv_block(data) + "\n"
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(csv_content)
    
    return os.path.abspath(OUTPUT_FILE)

def main():
    # Load Config
    config = load_config()
    default_rows = config.get("row_count", 20)

    # 1. Get User Input
    row_count = get_row_count(default_rows)
    if not row_count:
        print("Operation cancelled.")
        return

    # Calculate clicks (Rows + 15%)
    click_count = math.ceil(row_count * 1.15)
    print(f"Target Rows: {row_count} | Performing {click_count} clicks (+15% buffer)")

    # 2. Countdown & Capture Original Page
    print("\nIMPORTANT: Please switch to your browser NOW.")
    print("Capturing 'Original Page' state in 5 seconds...")
    for i in range(5, 0, -1):
        print(f"{i}...", end="", flush=True)
        time.sleep(1)
    print(" Capturing...")

    # Capture logic
    pyautogui.hotkey('ctrl', 'a')
    time.sleep(0.5)
    pyautogui.hotkey('ctrl', 'c')
    time.sleep(0.5)
    orig_pg = pyperclip.paste().strip()
    print("Original page captured. Starting Clicker sequence...")
    
    # 3. Perform Clicks
    perform_clicks(click_count)

    # 4. Extraction Loop
    print("\n--- Starting Extraction Loop (Reverse Order) ---")
    print("Navigating to last tab...")
    
    # Move to the last opened tab (Reverse navigation)
    # Assuming the clicker opened tabs in background, we are still on orig page.
    # Ctrl+Shift+Tab once goes to the last tab.
    pyautogui.hotkey('ctrl', 'shift', 'tab')
    
    collected_data = []
    seen_content_set = set() # Global de-duplication
    tab_index = 0

    while True:
        tab_index += 1
        print(f"Processing tab {tab_index}...")
        
        # A. Wait for content
        time.sleep(PAGE_LOAD_WAIT)

        # B. Copy Content
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(0.5) 
        pyautogui.hotkey('ctrl', 'c')
        time.sleep(0.5)

        # C. Get Text
        current_content = pyperclip.paste().strip()

        # D. STOP CONDITION: Check if we are back at the original page
        if current_content == orig_pg:
            print(">> LOOP COMPLETE: Returned to original page.")
            break
        
        # E. DE-DUPLICATION: Check against ALL previously seen content
        # We use a hash or a substring to check, but comparing full text is safer if memory allows.
        if current_content in seen_content_set:
            print("  -> Duplicate found (Seen before). Skipping.")
        else:
            # Mark as seen
            seen_content_set.add(current_content)
            
            # Parse and Store
            parsed_data = parse_invoice_text(current_content)
            collected_data.append(parsed_data)
            inv_num = parsed_data.get('invoice_number', 'Unknown')
            print(f"  -> Extracted: {inv_num}")

        # F. Navigate Reverse (Previous Tab)
        pyautogui.hotkey('ctrl', 'shift', 'tab')

    # 5. Save Results
    if collected_data:
        saved_path = save_data(collected_data)
        print(f"\nSUCCESS! Data saved to:\n{saved_path}")
        try:
            beepy.beep(sound=1) # Default sound
        except Exception as e:
            print(f"Sound error: {e}")
    else:
        print("\nNo unique data was extracted.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nScript stopped by user.")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
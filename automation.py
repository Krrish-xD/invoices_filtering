import time
import os
import math
# import sys # Removed
import pyautogui
import pyperclip
import winsound # Added
from clicker import perform_clicks
from extractor import parse_invoice_text, format_to_csv_block
from config_manager import load_config

# Configuration
OUTPUT_FILE = "extracted_data.csv"
PAGE_LOAD_WAIT = 2.0  # Seconds to wait for a tab to load content

def play_sound():
    """Plays a system beep using winsound (Windows-specific)."""
    try:
        winsound.MessageBeep()
    except Exception:
        pass

def save_data(all_data):
    """Saves the collected data blocks to the CSV file."""
    csv_content = ""
    for data in all_data:
        csv_content += format_to_csv_block(data) + "\n"
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(csv_content)
    
    return os.path.abspath(OUTPUT_FILE)

def run_automation_logic(row_count, logger=print):
    """
    The main logic for the automation, callable from an external GUI.
    logger: A function to output text (defaults to print).
    """
    
    # Calculate clicks (Rows + 15%)
    click_count = math.ceil(row_count * 1.15)
    logger(f"Target Rows: {row_count} | Performing {click_count} clicks (+15% buffer)")

    # 2. Countdown & Capture Original Page
    logger("\nIMPORTANT: Please switch to your browser NOW.")
    logger("Capturing 'Original Page' state in 5 seconds...")
    for i in range(5, 0, -1):
        logger(f"{i}...")
        time.sleep(1)
    logger(" Capturing...")

    # Capture logic
    pyautogui.hotkey('ctrl', 'a')
    time.sleep(0.5)
    pyautogui.hotkey('ctrl', 'c')
    time.sleep(0.5)
    orig_pg = pyperclip.paste().strip()
    logger("Original page captured. Starting Clicker sequence...")
    
    # 3. Perform Clicks
    # Note: We might need to redirect clicker's print statements if we want them in the GUI too.
    # For now, we trust the clicker to just do its job.
    perform_clicks(click_count)

    # 4. Extraction Loop
    logger("\n--- Starting Extraction Loop (Reverse Order) ---")
    # Move to the first tab (Forward navigation)
    logger("Navigating to first tab...")
    pyautogui.hotkey('ctrl', 'tab')
    time.sleep(0.8) # Pause after moving to new tab
    
    collected_data = []
    seen_content_set = set() # Global de-duplication
    tab_index = 0
    
    # Safety: Ensure we don't stop immediately if the first tab resembles the original
    # or if we haven't actually moved yet.
    has_moved_past_start = False

    while True:
        tab_index += 1
        logger(f"Processing tab {tab_index}...")
        
        # A. Wait for content
        time.sleep(PAGE_LOAD_WAIT)

        # B. Copy Content (With Retry Logic)
        def capture_content():
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.5) 
            pyautogui.hotkey('ctrl', 'c')
            time.sleep(0.5)
            return pyperclip.paste().strip()

        current_content = capture_content()

        # RETRY MECHANISM for blank pages
        if not current_content:
            logger("  -> Page seems blank/loading. Waiting extra 2.5s...")
            time.sleep(2.5)
            current_content = capture_content()
            if not current_content:
                logger("  -> Still blank. Skipping this tab (might be not loaded).")
                # We don't break, we just move on.
                # But we should be careful not to trigger "Stop Condition" on a blank page if orig_pg wasn't blank.

        # D. STOP CONDITION: Check if we are back at the original page
        # We only check this if we are confident we have processed at least one unique tab 
        # OR if we've gone through enough tabs (sanity check).
        # But primarily, we check if content matches orig_pg.
        
        is_original_page = (current_content == orig_pg)
        
        if is_original_page:
            if not has_moved_past_start:
                 # We are still seeing the original page content? 
                 # Maybe the Ctrl+Tab didn't register? Or the first tab is a duplicate of the list?
                 # We'll treat it as a duplicate for now but WON'T stop the loop yet.
                 logger("  -> Content matches Original Page, but strictly inside first few checks. Continuing...")
            else:
                logger(">> LOOP COMPLETE: Returned to original page.")
                break
        else:
            # If we see content that is DIFFERENT from original, we mark that we have successfully left the start.
            has_moved_past_start = True
        
        # E. DE-DUPLICATION
        if current_content in seen_content_set:
            logger("  -> Duplicate found (Seen before). Skipping.")
        else:
            # Mark as seen (Only if it's valid content)
            if current_content:
                seen_content_set.add(current_content)
                
                # Parse and Store
                parsed_data = parse_invoice_text(current_content)
                collected_data.append(parsed_data)
                inv_num = parsed_data.get('invoice_number', 'Unknown')
                logger(f"  -> Extracted: {inv_num}")

        # F. Navigate Forward (Next Tab)
        pyautogui.hotkey('ctrl', 'tab')
        time.sleep(0.8) # Pause after moving to new tab

    # 5. Save Results
    if collected_data:
        saved_path = save_data(collected_data)
        logger(f"\nSUCCESS! Data saved to:\n{saved_path}")
        play_sound()
    else:
        logger("\nNo unique data was extracted.")

def main():
    # Load Config
    config = load_config()
    default_rows = config.get("row_count", 20)
    
    # If running directly, we still want a prompt or just run with defaults
    # Since we moved the GUI out, let's just use input() for the standalone version
    try:
        val = input(f"Enter rows to process (Default {default_rows}): ").strip()
        if not val:
            row_count = default_rows
        else:
            row_count = int(val)
    except ValueError:
        print("Invalid input, using default.")
        row_count = default_rows
        
    run_automation_logic(row_count)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nScript stopped by user.")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
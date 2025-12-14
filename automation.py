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
PAGE_LOAD_WAIT = 1.0  # Seconds to wait for a tab to load content

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

def perform_initial_tab_load(tab_count, logger=print):
    """
    Cycles through all opened tabs to trigger loading, then returns to the first tab.
    """
    logger(f"  [Init] cycling through {tab_count} tabs to trigger loading...")
    
    # Cycle through all tabs to load them
    for i in range(tab_count):
        pyautogui.hotkey('ctrl', 'tab')
        # Small delay to let the browser register the tab switch and start rendering
        time.sleep(0.3) 
        
    logger("  [Init] Returning to first tab, then moving to first invoice...")
    # Jump to the first tab, then one forward to start
    pyautogui.hotkey('ctrl', '2')
    time.sleep(0.5)

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
    perform_clicks(click_count)

    # 4. Extraction Loop
    logger("\n--- Starting Extraction Loop (Reverse Order) ---")
    
    # --- PRE-LOOP INITIALIZATION ---
    # Trigger loading for ALL tabs before starting processing
    perform_initial_tab_load(click_count, logger)

    collected_data = []
    seen_content_set = set() # Global de-duplication
    tab_index = 0
    
    has_moved_past_start = False

    while True:
        tab_index += 1
        logger(f"Processing tab {tab_index}...")
        
        # A. Wait for content
        time.sleep(PAGE_LOAD_WAIT)

        # B. Copy Content (With Progressive Retry Logic)
        def capture_with_retries():
            # Retry delays as requested
            delays = [0.2, 0.4, 0.6, 0.8, 1.0]
            
            for attempt, delay in enumerate(delays + [None]): # + [None] for the final attempt
                # Perform Copy
                pyautogui.hotkey('ctrl', 'a')
                time.sleep(0.5) 
                pyautogui.hotkey('ctrl', 'c')
                time.sleep(0.5)
                
                content = pyperclip.paste().strip()
                
                # Immediate success if it matches original page (Stop condition)
                if content == orig_pg:
                    return content

                # Check for "Partial Load" (Too short or too few lines)
                is_loaded = True
                if not content:
                    is_loaded = False
                elif len(content) < 250:
                    # logger(f"    (Content too short: {len(content)} chars)")
                    is_loaded = False
                elif content.count('\n') < 25:
                    # logger(f"    (Too few lines: {content.count('\n')})")
                    is_loaded = False

                if is_loaded:
                    return content
                
                # If content is invalid and we have delays left, wait and retry
                if delay is not None:
                    logger(f"  -> Page not fully loaded (Partial/Blank). Retrying in {delay}s (Attempt {attempt+1}/5)...")
                    time.sleep(delay)
            
            return "" # Give up

        current_content = capture_with_retries()

        if not current_content:
            logger("  -> Failed to capture content after 5 retries. Skipping tab.")
            # We don't break, just continue to next iteration but perform warmup/nav first
        
        # D. STOP CONDITION
        is_original_page = (current_content == orig_pg)
        
        if is_original_page:
            if not has_moved_past_start:
                 logger("  -> Content matches Original Page, but strictly inside first few checks. Continuing...")
            else:
                logger(">> LOOP COMPLETE: Returned to original page.")
                break
        else:
            has_moved_past_start = True
        
        # E. DE-DUPLICATION
        if current_content in seen_content_set:
            logger("  -> Duplicate found (Seen before). Skipping.")
        else:
            if current_content:
                seen_content_set.add(current_content)
                parsed_data = parse_invoice_text(current_content)
                collected_data.append(parsed_data)
                inv_num = parsed_data.get('invoice_number', 'Unknown')
                logger(f"  -> Extracted: {inv_num}")
                
        # F. Navigate Forward (Next Tab) with Wiggle (Forward 3, Back 2)
        # Net movement: +1 (The immediate next tab)
        # Purpose: Trigger loading of subsequent tabs
        pyautogui.hotkey('ctrl', 'tab')
        time.sleep(0.2)
        pyautogui.hotkey('ctrl', 'tab')
        time.sleep(0.2)
        pyautogui.hotkey('ctrl', 'tab')
        time.sleep(0.2)
        pyautogui.hotkey('ctrl', 'shift', 'tab')
        time.sleep(0.2)
        pyautogui.hotkey('ctrl', 'shift', 'tab')
        time.sleep(0.8) 

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
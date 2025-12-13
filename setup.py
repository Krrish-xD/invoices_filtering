import pyautogui
import time
from config_manager import save_config, load_config

def get_mouse_position(prompt):
    print(prompt)
    print("Place your mouse over the target point in 5 seconds...")
    for i in range(5, 0, -1):
        print(f"{i}...", end=" ", flush=True)
        time.sleep(1)
    print("Capture!")
    x, y = pyautogui.position()
    print(f"Captured: ({x}, {y})")
    return x, y

def main():
    print("--- Invoice Scraper Setup Wizard ---")
    print("This setup will configure the click coordinates.")
    
    # 1. Capture First Item
    start_x, start_y = get_mouse_position("\nStep 1: We need the coordinates of the FIRST clickable item.")
    
    # 2. Capture Second Item
    end_x, end_y = get_mouse_position("\nStep 2: We need the coordinates of the SECOND clickable item (immediately below the first).")
    
    # Calculate spacing
    vertical_spacing = abs(end_y - start_y)
    print(f"\nCalculated vertical spacing: {vertical_spacing} pixels")
    
    # 3. Get Row Count
    while True:
        try:
            val = input("\nStep 3: Enter the default number of rows to process (e.g., 20): ").strip()
            row_count = int(val)
            break
        except ValueError:
            print("Invalid input. Please enter a number.")
            
    config = {
        "start_x": start_x,
        "start_y": start_y,
        "vertical_spacing": vertical_spacing,
        "row_count": row_count
    }
    
    save_config(config)
    print("\nSetup complete! You can now run 'python automation.py'.")

if __name__ == "__main__":
    main()

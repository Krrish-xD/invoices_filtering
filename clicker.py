import pyautogui
import random
import time

def human_random(
    base_delay=721, std_dev=81, min_delay=418, max_delay=1176,
    outlier_chance=0.16, outlier_factor=2.4, recursion_limit=100
):
    """
    Returns a human-like delay in seconds.
    Uses recursive resampling instead of clamping.
    """
    if recursion_limit <= 0:
        return round(base_delay / 1000, 3)

    delay = random.gauss(base_delay, std_dev)

    if random.random() < outlier_chance:
        if random.random() < 0.5:
            delay += outlier_factor * std_dev
        else:
            delay -= outlier_factor * std_dev

    if delay < min_delay or delay > max_delay:
        return human_random(
            base_delay=base_delay, std_dev=std_dev, min_delay=min_delay,
            max_delay=max_delay, outlier_chance=outlier_chance,
            outlier_factor=outlier_factor, recursion_limit=recursion_limit - 1,
        )

    return round(delay / 1000, 3)

def click_at(x, y):
    """Moves the mouse to the specified coordinates and performs a Ctrl+Click."""
    pyautogui.moveTo(x, y, duration=random.uniform(0.1, 0.3))
    pyautogui.keyDown('ctrl')
    pyautogui.click()
    pyautogui.keyUp('ctrl')
    print(f"Ctrl+Clicked at: ({round(x, 2)}, {round(y, 2)})")

def perform_clicks(num_clicks=20):
    """
    Performs a series of human-like clicks in a vertical list.
    """
    # Parameters for clicking
    x_min = 414
    x_max = 1414
    y_orig = 518
    y_margin = 4  # Max vertical offset
    row_height = 22 # Vertical distance between rows

    # X-axis logic: focus on the middle 100 pixels
    x_center = (x_min + x_max) / 2
    x_click_zone_half_width = 50

    # Standard deviations for the normal distribution
    x_std_dev = 15  
    y_std_dev = y_margin / 2 

    print(f"--- STARTING {num_clicks} REAL CLICKS ---")
    print(f"Starting in 5 seconds...")
    for i in range(5, 0, -1):
        print(f"{i}...", end="", flush=True)
        time.sleep(1)
    print(" Go!")

    for i in range(num_clicks):
        # Calculate mean coordinates for this row
        mean_x = x_center
        mean_y = y_orig + (i * row_height)

        # Generate coordinates using a normal distribution
        target_x = random.gauss(mean_x, x_std_dev)
        target_y = random.gauss(mean_y, y_std_dev)

        # Ensure clicks don't go too far out of the intended zone
        target_x = max(x_center - x_click_zone_half_width, min(target_x, x_center + x_click_zone_half_width))
        
        # Perform the actual click
        click_at(target_x, target_y)

        # Get human-like delay
        delay = human_random()
        print(f"Waiting {delay}s...")
        time.sleep(delay)

    print(f"All {num_clicks} clicks completed.")

if __name__ == '__main__':
    try:
        perform_clicks()
    except Exception as e:
        print(f"An error occurred: {e}")

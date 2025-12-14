import pyautogui
import random
import time

def human_random(
    base_delay=521, std_dev=81, min_delay=200, max_delay=1176,
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

    # Corrected recursive call from human_delay to human_random
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

from config_manager import load_config

def perform_clicks(num_clicks=23):
    """
    Performs a series of human-like clicks in a vertical list using configured coordinates.
    """
    config = load_config()
    
    # Base coordinates from config
    start_x = config.get("start_x", 0)
    y_orig = config.get("start_y", 0)
    row_height = config.get("vertical_spacing", 23.5)
    
    # Parameters for clicking
    y_margin = 3      # Max vertical offset for randomization

    # X-axis logic
    # We use the captured start_x as the center. 
    # Add a small session-based random offset to the X center to vary slightly between runs.
    randomized_session_center_x = start_x + random.uniform(-10, 10)

    # Standard deviations for normal distribution
    x_std_dev = 15
    y_std_dev = y_margin / 2

    print(f"--- Clicking Automation Starting ---")
    print(f"Randomized session X-center for all clicks: {randomized_session_center_x:.2f}")
    print(f"Performing {num_clicks} clicks now...")

    for i in range(num_clicks):
        # Calculate mean coordinates for this row
        mean_y = y_orig + (i * row_height)
        mean_x = randomized_session_center_x

        # Generate coordinates using a normal distribution
        target_x = random.gauss(mean_x, x_std_dev)
        target_y = random.gauss(mean_y, y_std_dev)

        # Clamp y deviation to the max y_margin
        target_y = max(mean_y - y_margin, min(target_y, mean_y + y_margin))
        # Clamp x deviation to the session click zone (e.g. +/- 50 pixels)
        target_x = max(mean_x - 50, min(target_x, mean_x + 50))

        # Perform the click
        click_at(target_x, target_y)

        # Wait for a human-like delay
        delay = human_random()
        print(f"Waited for {delay} seconds.")
        time.sleep(delay)

    print(f"All {num_clicks} clicks completed.")

if __name__ == '__main__':
    try:
        # Re-enabled the actual click automation
        perform_clicks()
    except Exception as e:
        print(f"An error occurred: {e}")
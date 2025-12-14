import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import threading
import sys
from config_manager import load_config, save_config
import setup
import automation

class RedirectText(object):
    """Redirects print statements to a tkinter Text widget."""
    def __init__(self, text_widget):
        self.output = text_widget

    def write(self, string):
        self.output.insert(tk.END, string)
        self.output.see(tk.END)

    def flush(self):
        pass

class AutomationApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Invoice Automation Dashboard")
        self.root.geometry("600x650")

        # Load existing config
        self.config = load_config()

        # Styles
        self.header_font = ("Helvetica", 12, "bold")
        self.normal_font = ("Helvetica", 10)
        self.pad_opts = {'padx': 10, 'pady': 5}

        # --- SECTION 1: SETUP & CONFIG ---
        self.create_setup_section()

        # --- SECTION 2: EXECUTION ---
        self.create_execution_section()

        # --- SECTION 3: LOGS ---
        self.create_log_section()

    def create_setup_section(self):
        frame = tk.LabelFrame(self.root, text="Configuration & Setup", font=self.header_font, padx=10, pady=10)
        frame.pack(fill="x", padx=15, pady=10)

        # Row Count
        row_frame = tk.Frame(frame)
        row_frame.pack(fill="x", pady=5)
        tk.Label(row_frame, text="Rows to Process:", font=self.normal_font).pack(side="left")
        self.row_entry = tk.Entry(row_frame, width=10)
        self.row_entry.insert(0, str(self.config.get("row_count", 20)))
        self.row_entry.pack(side="left", padx=10)

        # Coordinate Setup
        coord_frame = tk.Frame(frame)
        coord_frame.pack(fill="x", pady=5)
        tk.Label(coord_frame, text="Coordinates:", font=self.normal_font).pack(side="left")
        
        btn_capture = tk.Button(coord_frame, text="Run Coordinate Capture Wizard", 
                                command=self.run_setup_wizard, bg="#2196F3", fg="white")
        btn_capture.pack(side="left", padx=10)
        
        self.coord_status = tk.Label(coord_frame, text="Ready", fg="gray")
        self.coord_status.pack(side="left")

        # Extra File Path
        file_frame = tk.Frame(frame)
        file_frame.pack(fill="x", pady=5)
        tk.Label(file_frame, text="Extra File Path:", font=self.normal_font).pack(side="left")
        
        self.file_entry = tk.Entry(file_frame, width=30)
        self.file_entry.insert(0, self.config.get("extra_file_path", ""))
        self.file_entry.pack(side="left", padx=5)
        
        btn_browse = tk.Button(file_frame, text="Browse", command=self.browse_file)
        btn_browse.pack(side="left")

        # Save Config Button
        btn_save = tk.Button(frame, text="Save Settings", command=self.save_settings, bg="#E0E0E0")
        btn_save.pack(anchor="e", pady=5)

    def create_execution_section(self):
        frame = tk.LabelFrame(self.root, text="Automation Control", font=self.header_font, padx=10, pady=10)
        frame.pack(fill="x", padx=15, pady=5)

        self.btn_start = tk.Button(frame, text="START AUTOMATION", command=self.start_automation, 
                                   bg="#4CAF50", fg="white", font=("Helvetica", 14, "bold"), height=2)
        self.btn_start.pack(fill="x")
        
        tk.Label(frame, text="Ensure your browser is open and focused immediately after clicking Start.", 
                 fg="red", font=("Helvetica", 9)).pack(pady=5)

    def create_log_section(self):
        frame = tk.LabelFrame(self.root, text="Logs", font=self.header_font, padx=10, pady=10)
        frame.pack(fill="both", expand=True, padx=15, pady=10)

        self.log_area = scrolledtext.ScrolledText(frame, height=10, state='normal', font=("Consolas", 9))
        self.log_area.pack(fill="both", expand=True)

        # Redirect stdout to the log area
        sys.stdout = RedirectText(self.log_area)

    def browse_file(self):
        filename = filedialog.askopenfilename(title="Select File")
        if filename:
            self.file_entry.delete(0, tk.END)
            self.file_entry.insert(0, filename)

    def save_settings(self):
        try:
            row_count = int(self.row_entry.get())
            extra_path = self.file_entry.get()
            
            self.config["row_count"] = row_count
            self.config["extra_file_path"] = extra_path
            
            save_config(self.config)
        except ValueError:
            messagebox.showerror("Error", "Row count must be a number.")

    def run_setup_wizard(self):
        # We run this in a thread so the GUI doesn't freeze, 
        # but setup currently uses print() which we've redirected.
        # Ideally setup wizard should probably be its own window or just printed to logs.
        # Since it requires user interaction (move mouse), let's block or handle carefully.
        
        if messagebox.askyesno("Coordinate Setup", "This will minimize the window and guide you to capture coordinates. Ready?"):
            self.root.iconify() # Minimize window
            
            def task():
                try:
                    new_config = setup.run_setup_wizard()
                    # Update internal config
                    self.config.update(new_config)
                    
                    # Update GUI on main thread
                    self.root.after(0, self.on_setup_complete)
                except Exception as e:
                    print(f"Setup Error: {e}")
                    self.root.after(0, self.root.deiconify)

            threading.Thread(target=task, daemon=True).start()

    def on_setup_complete(self):
        self.root.deiconify()
        messagebox.showinfo("Setup Complete", "Coordinates captured and saved.")
        # Reload config to ensure we have latest
        self.config = load_config()

    def start_automation(self):
        # Save current UI settings first
        self.save_settings()
        
        row_count = self.config.get("row_count", 20)
        
        self.btn_start.config(state="disabled", text="Running...")
        
        def task():
            try:
                # We can pass a custom logger if we want, but stdout is already redirected
                automation.run_automation_logic(row_count)
            except Exception as e:
                print(f"Error during automation: {e}")
            finally:
                self.root.after(0, self.reset_ui)

        threading.Thread(target=task, daemon=True).start()

    def reset_ui(self):
        self.btn_start.config(state="normal", text="START AUTOMATION")
        messagebox.showinfo("Finished", "Automation cycle finished.")

if __name__ == "__main__":
    root = tk.Tk()
    app = AutomationApp(root)
    root.mainloop()

import tkinter as tk
from tkinter import ttk, simpledialog, messagebox, filedialog
import json
import os
import re

SAVE_DIRECTORY = "shiny_saves"

class PokemonTracker(ttk.Frame):
    """
    A single widget frame for tracking one Pokemon.
    Contains: Name Entry, Decrement Button, Count Label, Increment Button, 'Got it!' Button.
    """

    def __init__(self, parent, name="Pikachu", count=0, obtained=False):
        super().__init__(parent, padding=5)

        # Store data variables
        self.name_var = tk.StringVar(value=name)
        self.count_var = tk.IntVar(value=count)
        self.obtained_var = tk.BooleanVar(value=obtained)

        # Configure grid layout
        self.columnconfigure(0, weight=1)  # Name entry should expand

        # Create widgets
        self.name_entry = ttk.Entry(self, textvariable=self.name_var, width=30)
        self.btn_decrement = ttk.Button(self, text="-", width=3, command=self.decrement_count)
        self.lbl_count = ttk.Label(self, textvariable=self.count_var, width=6, anchor="center")
        self.btn_increment = ttk.Button(self, text="+", width=3, command=self.increment_count)
        self.btn_got_it = ttk.Button(self, text="Got it!", command=self.mark_obtained)

        # Place widgets on the grid
        self.name_entry.grid(row=0, column=0, padx=(0, 5), sticky="ew")
        self.btn_decrement.grid(row=0, column=1, padx=(0, 2))
        self.lbl_count.grid(row=0, column=2, padx=2)
        self.btn_increment.grid(row=0, column=3, padx=(2, 5))
        self.btn_got_it.grid(row=0, column=4)

        # Set initial state if already obtained
        if self.obtained_var.get():
            self.lock_as_obtained()

    def increment_count(self):
        """Increases the counter by 1."""
        self.count_var.set(self.count_var.get() + 1)

    def decrement_count(self):
        """Decreases the counter by 1, but not below 0."""
        current_count = self.count_var.get()
        if current_count > 0:
            self.count_var.set(current_count - 1)

    def mark_obtained(self):
        """Locks the tracker, displays the final message, and highlights the frame."""
        self.obtained_var.set(True)
        self.lock_as_obtained()

    def lock_as_obtained(self):
        """Helper function to set the visual state to 'obtained'."""
        name = self.name_var.get()
        count = self.count_var.get()

        suffix = "try" if count == 1 else "tries"
        final_text = f"Shiny {name} obtained in {count} {suffix}!"

        self.name_var.set(final_text)
        self.name_entry.config(state="readonly")

        self.btn_decrement.config(state="disabled")
        self.btn_increment.config(state="disabled")
        self.btn_got_it.config(state="disabled")
        self.lbl_count.grid_remove()
        self.config(style="Obtained.TFrame")

    def get_data(self):
        """Returns the tracker's data for saving."""
        if self.obtained_var.get():
            text = self.name_var.get()
            match = re.search(r"Shiny (.*) obtained in (\d+)", text)
            if match:
                name = match.group(1)
                count = int(match.group(2))
            else:
                name = "Unknown"
                count = self.count_var.get()
        else:
            name = self.name_var.get()
            count = self.count_var.get()

        return {
            "name": name,
            "count": count,
            "obtained": self.obtained_var.get()
        }


class ScrollableFrame(ttk.Frame):
    """
    A reusable widget that puts a frame inside a canvas with a scrollbar.
    Widgets should be added to `self.scrollable_frame`.
    """

    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        self.canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)  # Windows/macOS
        self.canvas.bind_all("<Button-4>", self._on_mousewheel)  # Linux (scroll up)
        self.canvas.bind_all("<Button-5>", self._on_mousewheel)  # Linux (scroll down)

    def _on_mousewheel(self, event):
        """Handle cross-platform mouse wheel scrolling."""
        if event.num == 5 or event.delta == -120:
            self.canvas.yview_scroll(1, "units")
        elif event.num == 4 or event.delta == 120:
            self.canvas.yview_scroll(-1, "units")


class PokemonTab(ttk.Frame):
    """
    A single tab page.
    Contains a control bar (Add Tracker) and a scrollable list of trackers.
    """

    def __init__(self, parent, tab_name):
        super().__init__(parent, padding=10)
        self.tab_name = tab_name
        self.trackers = []

        control_frame = ttk.Frame(self)
        control_frame.pack(fill="x", pady=(0, 10))

        btn_add = ttk.Button(control_frame, text="Add Pokemon Tracker", command=self.add_tracker)
        btn_add.pack(side="left")

        self.tracker_list_frame = ScrollableFrame(self)
        self.tracker_list_frame.pack(fill="both", expand=True)

    def add_tracker(self, name="New Pokemon", count=0, obtained=False):
        """Adds a new PokemonTracker widget to the scrollable list."""
        tracker = PokemonTracker(
            self.tracker_list_frame.scrollable_frame,
            name=name,
            count=count,
            obtained=obtained
        )
        tracker.pack(fill="x", expand=True, padx=5, pady=5)

        self.trackers.append(tracker)

    def get_data(self):
        """Collects data from all trackers in this tab for saving."""
        tracker_data = [t.get_data() for t in self.trackers]
        return {
            "tab_name": self.tab_name,
            "trackers": tracker_data
        }


class App(tk.Tk):
    """
    The main application window.
    Manages the Notebook (tabs) and save/load operations.
    """

    def __init__(self):
        super().__init__()
        self.title("Pokemon Egg Tries for Shiny")
        self.geometry("700x500")

        if not os.path.exists(SAVE_DIRECTORY):
            os.makedirs(SAVE_DIRECTORY)

        style = ttk.Style()
        style.configure("Obtained.TFrame",
                        relief="solid",
                        borderwidth=2,
                        bordercolor="green")

        top_controls = ttk.Frame(self, padding=10)
        top_controls.pack(fill="x")

        btn_add_tab = ttk.Button(top_controls, text="New Tab", command=self.add_tab)
        btn_add_tab.pack(side="left", padx=5)

        btn_load_tab = ttk.Button(top_controls, text="Load Tab", command=self.load_tab_from_file)
        btn_load_tab.pack(side="left", padx=5)

        btn_save_tab = ttk.Button(top_controls, text="Save Current Tab", command=self.save_current_tab)
        btn_save_tab.pack(side="left", padx=5)

        btn_remove_tab = ttk.Button(top_controls, text="Remove Current Tab", command=self.remove_current_tab)
        btn_remove_tab.pack(side="right", padx=5)


        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=(0, 10))


        self.load_all_tabs_on_startup()


        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _get_filename_for_tab(self, tab_name):
        """Generates a safe filename from a tab name."""
        safe_name = re.sub(r'[^\w\-_\. ]', '_', tab_name).strip()
        safe_name = safe_name.lower().replace(" ", "_")
        return os.path.join(SAVE_DIRECTORY, f"{safe_name}.json")

    def _create_and_add_tab(self, name, data=None):
        """Internal helper to create and add a tab to the notebook."""
        tab = PokemonTab(self.notebook, tab_name=name)

        if data and "trackers" in data:
            for tracker_data in data["trackers"]:
                tab.add_tracker(
                    name=tracker_data.get("name", "Error"),
                    count=tracker_data.get("count", 0),
                    obtained=tracker_data.get("obtained", False)
                )

        self.notebook.add(tab, text=name)
        self.notebook.select(tab)
        return tab

    def add_tab(self):
        """Asks user for a new tab name and creates it."""
        name = simpledialog.askstring(
            "New Tab",
            "Enter tab name (e.g., 'Pokemon Glazed'):",
            parent=self
        )
        if name:
            self._create_and_add_tab(name)

    def remove_current_tab(self):
        """Removes the currently selected tab and deletes its save file."""
        try:
            current_tab_id = self.notebook.select()
            if not current_tab_id:
                messagebox.showwarning("No Tab", "No tab is selected to remove.")
                return

            tab_widget = self.notebook.nametowidget(current_tab_id)
            tab_name = tab_widget.tab_name

            if messagebox.askyesno("Confirm Remove",
                                   f"Are you sure you want to remove the tab '{tab_name}'?\n"
                                   "This will also delete the save file (if it exists).",
                                   parent=self):

                filename = self._get_filename_for_tab(tab_name)
                if os.path.exists(filename):
                    try:
                        os.remove(filename)
                    except OSError as e:
                        messagebox.showerror("Error", f"Could not delete save file: {e}")

                self.notebook.forget(current_tab_id)

        except tk.TclError:
            messagebox.showwarning("Error", "Could not find the selected tab to remove.")

    def save_current_tab(self):
        """Saves the data of the currently active tab to a JSON file."""
        try:
            current_tab_id = self.notebook.select()
            if not current_tab_id:
                messagebox.showwarning("No Tab", "No tab is selected to save.")
                return

            tab_widget = self.notebook.nametowidget(current_tab_id)
            data = tab_widget.get_data()
            filename = self._get_filename_for_tab(tab_widget.tab_name)

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)

            messagebox.showinfo("Saved", f"Tab '{tab_widget.tab_name}' saved to file.", parent=self)

        except tk.TclError:
            messagebox.showwarning("Error", "Could not find the selected tab to save.")
        except Exception as e:
            messagebox.showerror("Save Error", f"An error occurred while saving: {e}", parent=self)

    def load_tab_from_file(self):
        """Opens a file dialog to load a tab from a .json file."""
        filename = filedialog.askopenfilename(
            initialdir=SAVE_DIRECTORY,
            title="Load Tab",
            filetypes=(("JSON files", "*.json"), ("All files", "*.*")),
            parent=self
        )

        if not filename:
            return

        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)

            tab_name = data.get("tab_name", "Untitled")

            # Check if tab with this name already exists
            for tab_id in self.notebook.tabs():
                tab = self.notebook.nametowidget(tab_id)
                if tab.tab_name == tab_name:
                    messagebox.showwarning("Already Open", f"The tab '{tab_name}' is already open.", parent=self)
                    self.notebook.select(tab)
                    return

            self._create_and_add_tab(tab_name, data)

        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to load file: {e}", parent=self)

    def load_all_tabs_on_startup(self):
        """Scans the save directory and loads all .json files as tabs."""
        print(f"Loading saves from {os.path.abspath(SAVE_DIRECTORY)}...")
        for f in os.listdir(SAVE_DIRECTORY):
            if f.endswith(".json"):
                filepath = os.path.join(SAVE_DIRECTORY, f)
                try:
                    with open(filepath, 'r', encoding='utf-8') as file:
                        data = json.load(file)
                        tab_name = data.get("tab_name", "Error Loading")
                        self._create_and_add_tab(tab_name, data)
                except Exception as e:
                    print(f"Failed to load tab {filepath}: {e}")

    def on_closing(self):
        """Called when the user clicks the window's 'X' button."""
        if messagebox.askyesno("Quit", "Do you want to save all tabs before quitting?", parent=self):
            try:
                for tab_id in self.notebook.tabs():
                    tab_widget = self.notebook.nametowidget(tab_id)
                    data = tab_widget.get_data()
                    filename = self._get_filename_for_tab(tab_widget.tab_name)
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=4)
            except Exception as e:
                messagebox.showerror("Save Error", f"An error occurred while saving all tabs: {e}", parent=self)

        self.destroy()


if __name__ == "__main__":
    app = App()
    app.mainloop()
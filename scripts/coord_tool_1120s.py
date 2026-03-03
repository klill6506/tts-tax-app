#!/usr/bin/env python3
"""
IRS Form 1120-S Coordinate Mapping Tool

Visual GUI for placing and adjusting field coordinates on IRS PDF templates.
Uses PyMuPDF to render the PDF and Tkinter for the interactive canvas.

Usage:
    cd D:\\dev\\tts-tax-app\\server
    poetry run python ../scripts/coord_tool_1120s.py

    # Open a specific page (0-indexed):
    poetry run python ../scripts/coord_tool_1120s.py --page 2

    # Open a different form:
    poetry run python ../scripts/coord_tool_1120s.py --pdf ../resources/irs_forms/2025/f1065.pdf

Controls:
    Click on canvas:     Print PDF coordinates to stdout (click-to-print mode)
    Click a target:      Select it (highlighted in green)
    Drag a target:       Move it to new position
    Arrow keys:          Nudge selected target by 1 point
    Shift+Arrow:         Nudge by 10 points
    Ctrl+Arrow:          Nudge by 0.5 points
    Ctrl+S:              Save mapping to JSON
    Ctrl+Z:              Undo last move
    Delete/Backspace:    Remove selected target
    N:                   Add new target at center of view
    Tab:                 Cycle through targets
    1/2/3:               Set zoom to 100%/150%/200%

Coordinate System:
    PDF/ReportLab: origin at bottom-left, y increases upward
    Tkinter canvas: origin at top-left, y increases downward
    This tool converts between the two automatically.
"""

import argparse
import json
import sys
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog

import fitz  # PyMuPDF
from PIL import Image, ImageTk

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PDF = REPO_ROOT / "resources" / "irs_forms" / "2025" / "f1120s.pdf"
DEFAULT_JSON_DIR = REPO_ROOT / "scripts" / "coord_maps"
PAGE_WIDTH = 612.0   # US Letter width in points
PAGE_HEIGHT = 792.0  # US Letter height in points

TARGET_RADIUS = 6
TARGET_COLOR = "#e63946"       # Red crosshair
TARGET_SELECTED = "#2a9d8f"    # Green when selected
TARGET_LABEL_OFFSET = 10

ZOOM_LEVELS = [1.0, 1.5, 2.0, 2.5, 3.0]


@dataclass
class FieldTarget:
    """A named field with PDF coordinates."""
    name: str
    page: int
    pdf_x: float
    pdf_y: float
    width: float = 120.0
    alignment: str = "right"
    font_size: int = 10


class CoordTool:
    """Main application for coordinate mapping."""

    def __init__(self, pdf_path: str, page: int = 0, json_path: str | None = None):
        self.pdf_path = Path(pdf_path)
        self.current_page = page
        self.zoom_index = 0  # index into ZOOM_LEVELS
        self.scale = ZOOM_LEVELS[0]

        # Targets
        self.targets: list[FieldTarget] = []
        self.selected_target: FieldTarget | None = None
        self.undo_stack: list[tuple[FieldTarget, float, float]] = []

        # JSON path
        if json_path:
            self.json_path = Path(json_path)
        else:
            form_name = self.pdf_path.stem  # e.g. "f1120s"
            self.json_path = DEFAULT_JSON_DIR / f"{form_name}_page{page}.json"

        # Dragging state
        self._drag_target: FieldTarget | None = None
        self._drag_offset_x = 0
        self._drag_offset_y = 0

        # Load PDF
        self.doc = fitz.open(str(self.pdf_path))
        if page >= len(self.doc):
            print(f"ERROR: PDF only has {len(self.doc)} pages (requested page {page})")
            sys.exit(1)

        # Build UI
        self._build_ui()

        # Load existing JSON if present
        if self.json_path.exists():
            self._load_json(self.json_path)
        else:
            # Try to import from the Python coordinate file
            self._import_from_python_coords()

        self._render_page()

    # -------------------------------------------------------------------
    # UI construction
    # -------------------------------------------------------------------

    def _build_ui(self):
        self.root = tk.Tk()
        self.root.title(
            f"Coordinate Tool — {self.pdf_path.name} — Page {self.current_page}"
        )
        self.root.geometry("1200x900")

        # Top toolbar
        toolbar = tk.Frame(self.root, bg="#1d3557", height=36)
        toolbar.pack(fill=tk.X, side=tk.TOP)

        tk.Label(toolbar, text=f"  {self.pdf_path.name}  |", fg="white",
                 bg="#1d3557", font=("Consolas", 10)).pack(side=tk.LEFT)

        # Page selector
        tk.Label(toolbar, text="  Page:", fg="white", bg="#1d3557",
                 font=("Consolas", 10)).pack(side=tk.LEFT)
        self.page_var = tk.StringVar(value=str(self.current_page))
        page_spin = tk.Spinbox(
            toolbar, from_=0, to=len(self.doc) - 1,
            textvariable=self.page_var, width=3,
            command=self._on_page_change, font=("Consolas", 10)
        )
        page_spin.pack(side=tk.LEFT, padx=4)

        # Zoom buttons
        tk.Label(toolbar, text="  Zoom:", fg="white", bg="#1d3557",
                 font=("Consolas", 10)).pack(side=tk.LEFT)
        for i, z in enumerate(ZOOM_LEVELS):
            btn = tk.Button(
                toolbar, text=f"{int(z*100)}%",
                command=lambda idx=i: self._set_zoom(idx),
                font=("Consolas", 9), width=4
            )
            btn.pack(side=tk.LEFT, padx=1)

        self.zoom_label = tk.Label(
            toolbar, text=f"  [{int(self.scale*100)}%]", fg="#a8dadc",
            bg="#1d3557", font=("Consolas", 10, "bold")
        )
        self.zoom_label.pack(side=tk.LEFT)

        # Save button
        tk.Button(toolbar, text="Save JSON", command=self._save_json,
                  font=("Consolas", 9), bg="#2a9d8f", fg="white").pack(
            side=tk.RIGHT, padx=6, pady=2
        )

        # Add target button
        tk.Button(toolbar, text="+ Target", command=self._add_target_dialog,
                  font=("Consolas", 9), bg="#457b9d", fg="white").pack(
            side=tk.RIGHT, padx=2, pady=2
        )

        # Status bar (bottom)
        self.status_frame = tk.Frame(self.root, bg="#1d3557", height=28)
        self.status_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.coord_label = tk.Label(
            self.status_frame,
            text="  Click anywhere to see PDF coordinates  |  "
                 "Arrow keys to nudge  |  Ctrl+S to save",
            fg="#a8dadc", bg="#1d3557", font=("Consolas", 9), anchor="w"
        )
        self.coord_label.pack(fill=tk.X, side=tk.LEFT, padx=4)

        self.target_label = tk.Label(
            self.status_frame, text="", fg="#f1faee", bg="#1d3557",
            font=("Consolas", 9, "bold"), anchor="e"
        )
        self.target_label.pack(side=tk.RIGHT, padx=8)

        # Target list panel (right side)
        right_panel = tk.Frame(self.root, width=220, bg="#f1faee")
        right_panel.pack(fill=tk.Y, side=tk.RIGHT)
        right_panel.pack_propagate(False)

        tk.Label(right_panel, text="Fields", bg="#f1faee",
                 font=("Consolas", 11, "bold")).pack(pady=4)

        list_frame = tk.Frame(right_panel, bg="#f1faee")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=4)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.target_listbox = tk.Listbox(
            list_frame, yscrollcommand=scrollbar.set,
            font=("Consolas", 9), selectmode=tk.SINGLE,
            bg="white", fg="#1d3557"
        )
        self.target_listbox.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.target_listbox.yview)
        self.target_listbox.bind("<<ListboxSelect>>", self._on_listbox_select)

        # Canvas with scrollbars
        canvas_frame = tk.Frame(self.root)
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        self.h_scroll = tk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL)
        self.h_scroll.pack(fill=tk.X, side=tk.BOTTOM)
        self.v_scroll = tk.Scrollbar(canvas_frame, orient=tk.VERTICAL)
        self.v_scroll.pack(fill=tk.Y, side=tk.RIGHT)

        self.canvas = tk.Canvas(
            canvas_frame, bg="#e8e8e8",
            xscrollcommand=self.h_scroll.set,
            yscrollcommand=self.v_scroll.set,
        )
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.h_scroll.config(command=self.canvas.xview)
        self.v_scroll.config(command=self.canvas.yview)

        # Bind events
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Motion>", self._on_motion)

        self.root.bind("<Key>", self._on_key)
        self.root.bind("<Control-s>", lambda e: self._save_json())
        self.root.bind("<Control-z>", lambda e: self._undo())

    # -------------------------------------------------------------------
    # Coordinate conversion
    # -------------------------------------------------------------------

    def _pdf_to_canvas(self, pdf_x: float, pdf_y: float) -> tuple[float, float]:
        """Convert PDF coordinates (bottom-left origin) to canvas pixels (top-left origin)."""
        cx = pdf_x * self.scale
        cy = (PAGE_HEIGHT - pdf_y) * self.scale
        return cx, cy

    def _canvas_to_pdf(self, cx: float, cy: float) -> tuple[float, float]:
        """Convert canvas pixels to PDF coordinates."""
        pdf_x = cx / self.scale
        pdf_y = PAGE_HEIGHT - (cy / self.scale)
        return pdf_x, pdf_y

    # -------------------------------------------------------------------
    # Rendering
    # -------------------------------------------------------------------

    def _render_page(self):
        """Render the current PDF page and draw all targets."""
        page = self.doc[self.current_page]
        # Render at higher DPI for zoom
        dpi = 72 * self.scale
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat)

        # Convert to PIL Image then to Tkinter PhotoImage
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        self._photo = ImageTk.PhotoImage(img)

        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self._photo)
        self.canvas.config(scrollregion=(0, 0, pix.width, pix.height))

        # Draw targets for this page
        self._draw_all_targets()
        self._update_listbox()

    def _draw_all_targets(self):
        """Draw crosshair targets for all fields on the current page."""
        self.canvas.delete("target")
        for t in self.targets:
            if t.page != self.current_page:
                continue
            self._draw_target(t)

    def _draw_target(self, t: FieldTarget):
        """Draw a single crosshair target on the canvas."""
        cx, cy = self._pdf_to_canvas(t.pdf_x, t.pdf_y)
        r = TARGET_RADIUS
        is_selected = (t is self.selected_target)
        color = TARGET_SELECTED if is_selected else TARGET_COLOR
        width = 2 if is_selected else 1

        # Crosshair
        self.canvas.create_line(cx - r, cy, cx + r, cy, fill=color,
                                width=width, tags="target")
        self.canvas.create_line(cx, cy - r, cx, cy + r, fill=color,
                                width=width, tags="target")
        # Circle
        self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                                outline=color, width=width, tags="target")

        # Label
        label_text = t.name
        if is_selected:
            label_text += f"  ({t.pdf_x:.1f}, {t.pdf_y:.1f})"
        self.canvas.create_text(
            cx + TARGET_LABEL_OFFSET, cy - TARGET_LABEL_OFFSET,
            text=label_text, fill=color, anchor=tk.SW,
            font=("Consolas", 8 if not is_selected else 9, "bold" if is_selected else ""),
            tags="target"
        )

        # Width indicator (small right-edge tick)
        if t.alignment == "right":
            rx = cx + t.width * self.scale
            self.canvas.create_line(rx, cy - 3, rx, cy + 3, fill=color,
                                    width=1, tags="target", dash=(2, 2))

    # -------------------------------------------------------------------
    # Event handlers
    # -------------------------------------------------------------------

    def _on_click(self, event):
        """Handle click on canvas."""
        # Get canvas coordinates (account for scroll)
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        pdf_x, pdf_y = self._canvas_to_pdf(cx, cy)

        # Check if clicking on an existing target
        clicked_target = self._find_target_at(cx, cy)

        if clicked_target:
            self.selected_target = clicked_target
            self._drag_target = clicked_target
            tcx, tcy = self._pdf_to_canvas(clicked_target.pdf_x, clicked_target.pdf_y)
            self._drag_offset_x = cx - tcx
            self._drag_offset_y = cy - tcy
            self._update_status_selected()
            # Highlight in listbox
            self._select_in_listbox(clicked_target)
        else:
            # Click-to-print mode
            self.selected_target = None
            self._drag_target = None
            print(f"PDF coords: ({pdf_x:.1f}, {pdf_y:.1f})  |  "
                  f"Canvas: ({cx:.0f}, {cy:.0f})  |  Page {self.current_page}")

        self._draw_all_targets()
        self._update_status(pdf_x, pdf_y, cx, cy)

    def _on_drag(self, event):
        """Handle drag to move a target."""
        if not self._drag_target:
            return
        cx = self.canvas.canvasx(event.x) - self._drag_offset_x
        cy = self.canvas.canvasy(event.y) - self._drag_offset_y
        pdf_x, pdf_y = self._canvas_to_pdf(cx, cy)

        self._drag_target.pdf_x = round(pdf_x, 1)
        self._drag_target.pdf_y = round(pdf_y, 1)

        self._draw_all_targets()
        self._update_status(pdf_x, pdf_y, cx, cy)
        self._update_status_selected()

    def _on_release(self, event):
        """Handle mouse release after drag."""
        if self._drag_target:
            # Save undo state
            self.undo_stack.append(
                (self._drag_target, self._drag_target.pdf_x, self._drag_target.pdf_y)
            )
        self._drag_target = None

    def _on_motion(self, event):
        """Update coordinate display on mouse move."""
        cx = self.canvas.canvasx(event.x)
        cy = self.canvas.canvasy(event.y)
        pdf_x, pdf_y = self._canvas_to_pdf(cx, cy)
        self._update_status(pdf_x, pdf_y, cx, cy)

    def _on_key(self, event):
        """Handle keyboard input."""
        if not self.selected_target:
            # Number keys for zoom
            if event.char in "12345":
                idx = int(event.char) - 1
                if idx < len(ZOOM_LEVELS):
                    self._set_zoom(idx)
            return

        t = self.selected_target

        # Determine nudge amount
        nudge = 1.0
        if event.state & 0x1:  # Shift
            nudge = 10.0
        elif event.state & 0x4:  # Ctrl
            nudge = 0.5

        moved = False
        if event.keysym == "Left":
            t.pdf_x = round(t.pdf_x - nudge, 1)
            moved = True
        elif event.keysym == "Right":
            t.pdf_x = round(t.pdf_x + nudge, 1)
            moved = True
        elif event.keysym == "Up":
            t.pdf_y = round(t.pdf_y + nudge, 1)  # Up in PDF = increase y
            moved = True
        elif event.keysym == "Down":
            t.pdf_y = round(t.pdf_y - nudge, 1)  # Down in PDF = decrease y
            moved = True
        elif event.keysym in ("Delete", "BackSpace"):
            self._remove_target(t)
            return
        elif event.keysym == "Tab":
            self._cycle_target()
            return
        elif event.char == "n":
            self._add_target_dialog()
            return
        elif event.char in "12345":
            idx = int(event.char) - 1
            if idx < len(ZOOM_LEVELS):
                self._set_zoom(idx)
            return

        if moved:
            self._draw_all_targets()
            self._update_status_selected()

    def _on_page_change(self):
        """Handle page spinner change."""
        try:
            new_page = int(self.page_var.get())
        except ValueError:
            return
        if 0 <= new_page < len(self.doc):
            self.current_page = new_page
            self.selected_target = None
            self.root.title(
                f"Coordinate Tool -- {self.pdf_path.name} -- Page {self.current_page}"
            )
            self._render_page()

    def _on_listbox_select(self, event):
        """Handle selection in the target listbox."""
        sel = self.target_listbox.curselection()
        if not sel:
            return
        # Find the target by name from the listbox
        name = self.target_listbox.get(sel[0]).split(" ")[0]
        for t in self.targets:
            if t.name == name and t.page == self.current_page:
                self.selected_target = t
                self._draw_all_targets()
                self._update_status_selected()
                # Scroll canvas to show target
                cx, cy = self._pdf_to_canvas(t.pdf_x, t.pdf_y)
                self.canvas.xview_moveto(max(0, (cx - 300)) / (PAGE_WIDTH * self.scale))
                self.canvas.yview_moveto(max(0, (cy - 300)) / (PAGE_HEIGHT * self.scale))
                break

    # -------------------------------------------------------------------
    # Target management
    # -------------------------------------------------------------------

    def _find_target_at(self, cx: float, cy: float, radius: float = 12) -> FieldTarget | None:
        """Find a target near the given canvas coordinates."""
        best = None
        best_dist = radius
        for t in self.targets:
            if t.page != self.current_page:
                continue
            tcx, tcy = self._pdf_to_canvas(t.pdf_x, t.pdf_y)
            dist = ((cx - tcx) ** 2 + (cy - tcy) ** 2) ** 0.5
            if dist < best_dist:
                best = t
                best_dist = dist
        return best

    def _add_target_dialog(self):
        """Prompt for a new target name and add it."""
        name = simpledialog.askstring("New Target", "Field name:", parent=self.root)
        if not name:
            return
        name = name.strip()
        if not name:
            return

        # Check for duplicate
        for t in self.targets:
            if t.name == name and t.page == self.current_page:
                messagebox.showwarning("Duplicate", f"Target '{name}' already exists on this page.")
                return

        # Place at center of current view
        x0 = self.canvas.canvasx(0) + self.canvas.winfo_width() / 2
        y0 = self.canvas.canvasy(0) + self.canvas.winfo_height() / 2
        pdf_x, pdf_y = self._canvas_to_pdf(x0, y0)

        t = FieldTarget(name=name, page=self.current_page,
                        pdf_x=round(pdf_x, 1), pdf_y=round(pdf_y, 1))
        self.targets.append(t)
        self.selected_target = t
        self._draw_all_targets()
        self._update_listbox()
        self._update_status_selected()

    def _remove_target(self, t: FieldTarget):
        """Remove a target after confirmation."""
        if messagebox.askyesno("Remove", f"Remove target '{t.name}'?"):
            self.targets.remove(t)
            if self.selected_target is t:
                self.selected_target = None
            self._draw_all_targets()
            self._update_listbox()

    def _cycle_target(self):
        """Select the next target on this page."""
        page_targets = [t for t in self.targets if t.page == self.current_page]
        if not page_targets:
            return
        if self.selected_target in page_targets:
            idx = page_targets.index(self.selected_target)
            idx = (idx + 1) % len(page_targets)
        else:
            idx = 0
        self.selected_target = page_targets[idx]
        self._draw_all_targets()
        self._update_status_selected()
        self._select_in_listbox(self.selected_target)

    def _select_in_listbox(self, t: FieldTarget):
        """Highlight the given target in the listbox."""
        for i in range(self.target_listbox.size()):
            item_name = self.target_listbox.get(i).split(" ")[0]
            if item_name == t.name:
                self.target_listbox.selection_clear(0, tk.END)
                self.target_listbox.selection_set(i)
                self.target_listbox.see(i)
                break

    def _undo(self):
        """Undo the last target move."""
        if not self.undo_stack:
            return
        target, old_x, old_y = self.undo_stack.pop()
        target.pdf_x = old_x
        target.pdf_y = old_y
        self.selected_target = target
        self._draw_all_targets()
        self._update_status_selected()

    # -------------------------------------------------------------------
    # Status updates
    # -------------------------------------------------------------------

    def _update_status(self, pdf_x: float, pdf_y: float, cx: float, cy: float):
        """Update the status bar with current coordinates."""
        self.coord_label.config(
            text=f"  PDF: ({pdf_x:.1f}, {pdf_y:.1f})  |  "
                 f"Canvas: ({cx:.0f}, {cy:.0f})  |  "
                 f"Page {self.current_page}  |  "
                 f"Zoom {int(self.scale*100)}%"
        )

    def _update_status_selected(self):
        """Update the target info display."""
        if self.selected_target:
            t = self.selected_target
            self.target_label.config(
                text=f"[{t.name}]  x={t.pdf_x:.1f}  y={t.pdf_y:.1f}  "
                     f"w={t.width}  align={t.alignment}  size={t.font_size}"
            )
        else:
            self.target_label.config(text="")

    def _update_listbox(self):
        """Refresh the target listbox for the current page."""
        self.target_listbox.delete(0, tk.END)
        page_targets = sorted(
            [t for t in self.targets if t.page == self.current_page],
            key=lambda t: (-t.pdf_y, t.pdf_x)  # top to bottom, left to right
        )
        for t in page_targets:
            self.target_listbox.insert(
                tk.END, f"{t.name}  ({t.pdf_x:.1f}, {t.pdf_y:.1f})"
            )

    # -------------------------------------------------------------------
    # Zoom
    # -------------------------------------------------------------------

    def _set_zoom(self, idx: int):
        """Set zoom level by index."""
        if 0 <= idx < len(ZOOM_LEVELS):
            self.zoom_index = idx
            self.scale = ZOOM_LEVELS[idx]
            self.zoom_label.config(text=f"  [{int(self.scale*100)}%]")
            self._render_page()

    # -------------------------------------------------------------------
    # JSON load/save
    # -------------------------------------------------------------------

    def _save_json(self):
        """Save all targets to JSON."""
        self.json_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "meta": {
                "form": self.pdf_path.stem,
                "pdf": str(self.pdf_path.name),
                "page_width": PAGE_WIDTH,
                "page_height": PAGE_HEIGHT,
                "coordinate_system": "bottom-left origin (PDF/ReportLab)",
            },
            "fields": {}
        }

        for t in sorted(self.targets, key=lambda t: (t.page, -t.pdf_y, t.pdf_x)):
            data["fields"][t.name] = {
                "page": t.page,
                "x": round(t.pdf_x, 1),
                "y": round(t.pdf_y, 1),
                "width": t.width,
                "alignment": t.alignment,
                "font_size": t.font_size,
            }

        with open(self.json_path, "w") as f:
            json.dump(data, f, indent=2)

        print(f"Saved {len(self.targets)} fields to {self.json_path}")
        self.root.title(
            f"Coordinate Tool -- {self.pdf_path.name} -- Page {self.current_page}  [SAVED]"
        )

    def _load_json(self, path: Path):
        """Load targets from a JSON mapping file."""
        with open(path) as f:
            data = json.load(f)

        self.targets.clear()
        for name, field in data.get("fields", {}).items():
            self.targets.append(FieldTarget(
                name=name,
                page=field["page"],
                pdf_x=field["x"],
                pdf_y=field["y"],
                width=field.get("width", 120.0),
                alignment=field.get("alignment", "right"),
                font_size=field.get("font_size", 10),
            ))
        print(f"Loaded {len(self.targets)} fields from {path}")

    def _import_from_python_coords(self):
        """Import existing coordinates from the Python coordinate module."""
        # Try to import from the f1120s.py coordinate file
        form_stem = self.pdf_path.stem  # e.g. "f1120s"
        try:
            # Add server dir to path for imports
            server_dir = REPO_ROOT / "server"
            if str(server_dir) not in sys.path:
                sys.path.insert(0, str(server_dir))

            mod = __import__(
                f"apps.tts_forms.coordinates.{form_stem}",
                fromlist=["FIELD_MAP", "HEADER_FIELDS"]
            )
            field_map = getattr(mod, "FIELD_MAP", {})
            header_fields = getattr(mod, "HEADER_FIELDS", {})

            # Import field map entries
            for name, coord in {**header_fields, **field_map}.items():
                self.targets.append(FieldTarget(
                    name=name,
                    page=coord.page,
                    pdf_x=coord.x,
                    pdf_y=coord.y,
                    width=coord.width,
                    alignment=coord.alignment,
                    font_size=coord.font_size,
                ))

            print(f"Imported {len(self.targets)} fields from {form_stem}.py "
                  f"({len(header_fields)} header + {len(field_map)} field)")
        except (ImportError, AttributeError) as e:
            print(f"No Python coordinates found for {form_stem}: {e}")

    # -------------------------------------------------------------------
    # Export helper
    # -------------------------------------------------------------------

    def export_python(self):
        """Print the current targets as Python FieldCoord definitions."""
        print("\n# --- Generated coordinate mappings ---")
        for t in sorted(self.targets, key=lambda t: (t.page, -t.pdf_y, t.pdf_x)):
            print(
                f'    "{t.name}": FieldCoord('
                f'page={t.page}, x={t.pdf_x}, y={t.pdf_y}, '
                f'width={t.width}, alignment="{t.alignment}", '
                f'font_size={t.font_size}),'
            )

    # -------------------------------------------------------------------
    # Run
    # -------------------------------------------------------------------

    def run(self):
        """Start the application."""
        self.root.mainloop()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="IRS Form Coordinate Mapping Tool")
    parser.add_argument("--pdf", default=str(DEFAULT_PDF),
                        help="Path to IRS PDF template")
    parser.add_argument("--page", type=int, default=0,
                        help="Page number (0-indexed)")
    parser.add_argument("--json", default=None,
                        help="Path to JSON mapping file (load/save)")
    parser.add_argument("--export-python", action="store_true",
                        help="Print coordinates as Python and exit")
    args = parser.parse_args()

    app = CoordTool(
        pdf_path=args.pdf,
        page=args.page,
        json_path=args.json,
    )

    if args.export_python:
        app.export_python()
    else:
        app.run()


if __name__ == "__main__":
    main()

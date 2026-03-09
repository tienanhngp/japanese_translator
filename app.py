"""
Manga Translate App – Real-time screen snipping + OCR + Translation
- Press the Snip button (or Ctrl+Shift+X) to capture a screen region
- Uses manga-ocr to extract Japanese text
- Translates to English using deep-translator
"""

import os
import ctypes
import tkinter as tk
import threading
import tempfile
import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk, ImageGrab
from manga_ocr import MangaOcr
from deep_translator import GoogleTranslator

# Make the process DPI-aware so Tkinter coordinates match actual screen pixels
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)   # Per-Monitor DPI aware
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()     # Fallback
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════════════════
#  Screen Snip Overlay  (fullscreen transparent canvas for region selection)
# ═══════════════════════════════════════════════════════════════════════════
class SnipOverlay(tk.Toplevel):
    """Fullscreen overlay that lets the user drag-select a screen region."""

    def __init__(self, master, callback):
        super().__init__(master)
        self.callback = callback  # called with PIL.Image of selected region

        # Take a screenshot BEFORE showing the overlay
        self.screenshot = ImageGrab.grab(all_screens=True)

        # Fullscreen, topmost, no decorations
        self.attributes("-fullscreen", True)
        self.attributes("-topmost", True)
        self.overrideredirect(True)
        self.configure(cursor="crosshair")

        # Display the screenshot as the overlay background
        self.tk_img = ImageTk.PhotoImage(self.screenshot)
        self.canvas = tk.Canvas(self, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.create_image(0, 0, anchor="nw", image=self.tk_img)

        # Semi-transparent dark tint
        overlay = Image.new("RGBA", self.screenshot.size, (0, 0, 0, 100))
        self.overlay_img = ImageTk.PhotoImage(overlay)
        self.canvas.create_image(0, 0, anchor="nw", image=self.overlay_img)

        # Selection rectangle
        self.start_x = self.start_y = 0
        self.rect_id = None

        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.bind("<Escape>", lambda e: self._cancel())

        # Instruction text
        self.canvas.create_text(
            self.screenshot.width // 2, 30,
            text="Drag to select region  ·  ESC to cancel",
            fill="white", font=("Segoe UI", 16, "bold"),
        )

    def _on_press(self, event):
        self.start_x, self.start_y = event.x, event.y
        if self.rect_id:
            self.canvas.delete(self.rect_id)

    def _on_drag(self, event):
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        self.rect_id = self.canvas.create_rectangle(
            self.start_x, self.start_y, event.x, event.y,
            outline="#00aaff", width=2,
        )

    def _on_release(self, event):
        x0 = min(self.start_x, event.x)
        y0 = min(self.start_y, event.y)
        x1 = max(self.start_x, event.x)
        y1 = max(self.start_y, event.y)

        if (x1 - x0) < 10 or (y1 - y0) < 10:
            self._cancel()
            return

        # Crop the region from the original screenshot
        region = self.screenshot.crop((x0, y0, x1, y1))
        self.destroy()
        self.callback(region)

    def _cancel(self):
        self.destroy()
        self.callback(None)


# ═══════════════════════════════════════════════════════════════════════════
#  Main App
# ═══════════════════════════════════════════════════════════════════════════
class MangaTranslateApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Manga Translator")
        self.geometry("1100x750")
        self.minsize(900, 600)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.mocr = None
        self.translator = GoogleTranslator(source="ja", target="en")
        self.current_image_path = None
        self.photo_image = None

        self._build_ui()
        self._load_ocr_model()

        # Global hotkey: Ctrl+Shift+X to snip
        self.bind_all("<Control-Shift-x>", lambda e: self._snip_screen())
        self.bind_all("<Control-Shift-X>", lambda e: self._snip_screen())

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        # Top bar
        top_frame = ctk.CTkFrame(self, corner_radius=0)
        top_frame.pack(fill="x", padx=10, pady=(10, 5))

        self.btn_snip = ctk.CTkButton(
            top_frame, text="✂ Snip Screen (Ctrl+Shift+X)",
            command=self._snip_screen, width=220,
            fg_color="#e84393", hover_color="#d63384",
        )
        self.btn_snip.pack(side="left", padx=5, pady=5)

        self.btn_open = ctk.CTkButton(
            top_frame, text="📂 Open Image", command=self._open_image, width=130
        )
        self.btn_open.pack(side="left", padx=5, pady=5)

        self.btn_paste = ctk.CTkButton(
            top_frame, text="📋 Paste", command=self._paste_image, width=100
        )
        self.btn_paste.pack(side="left", padx=5, pady=5)

        self.btn_translate = ctk.CTkButton(
            top_frame,
            text="🔍 Extract & Translate",
            command=self._extract_and_translate,
            width=180,
            state="disabled",
        )
        self.btn_translate.pack(side="left", padx=5, pady=5)

        self.btn_clear = ctk.CTkButton(
            top_frame, text="🗑 Clear", command=self._clear, width=80
        )
        self.btn_clear.pack(side="left", padx=5, pady=5)

        self.status_label = ctk.CTkLabel(
            top_frame, text="Loading OCR model…", text_color="orange"
        )
        self.status_label.pack(side="right", padx=10, pady=5)

        # Main content
        content_frame = ctk.CTkFrame(self)
        content_frame.pack(fill="both", expand=True, padx=10, pady=5)
        content_frame.columnconfigure(0, weight=3)
        content_frame.columnconfigure(1, weight=2)
        content_frame.rowconfigure(0, weight=1)

        # Image panel
        img_frame = ctk.CTkFrame(content_frame)
        img_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))

        self.image_label = ctk.CTkLabel(
            img_frame,
            text="No image loaded\n\nClick  ✂ Snip Screen  to capture a region\nor open / paste an image",
        )
        self.image_label.pack(fill="both", expand=True, padx=5, pady=5)

        # Text panel
        text_frame = ctk.CTkFrame(content_frame)
        text_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

        ctk.CTkLabel(text_frame, text="Extracted Japanese Text", font=("", 14, "bold")).pack(
            pady=(8, 2)
        )
        self.ocr_textbox = ctk.CTkTextbox(text_frame, wrap="word", font=("", 16))
        self.ocr_textbox.pack(fill="both", expand=True, padx=8, pady=(0, 5))

        ctk.CTkLabel(text_frame, text="English Translation", font=("", 14, "bold")).pack(
            pady=(8, 2)
        )
        self.translation_textbox = ctk.CTkTextbox(text_frame, wrap="word", font=("", 16))
        self.translation_textbox.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # Bottom bar – manual input
        bottom_frame = ctk.CTkFrame(self, corner_radius=0)
        bottom_frame.pack(fill="x", padx=10, pady=(5, 10))

        ctk.CTkLabel(bottom_frame, text="Manual input:").pack(side="left", padx=(5, 2), pady=5)
        self.manual_entry = ctk.CTkEntry(
            bottom_frame, placeholder_text="Type Japanese text here…", width=400
        )
        self.manual_entry.pack(side="left", padx=5, pady=5, fill="x", expand=True)
        self.manual_entry.bind("<Return>", lambda e: self._translate_manual())

        self.btn_manual = ctk.CTkButton(
            bottom_frame, text="Translate", command=self._translate_manual, width=100
        )
        self.btn_manual.pack(side="left", padx=5, pady=5)

    # --------------------------------------------------------- OCR loading
    def _load_ocr_model(self):
        """Load manga-ocr model in a background thread."""

        def _load():
            try:
                self.mocr = MangaOcr()
                self.after(0, self._on_model_loaded)
            except Exception as e:
                err_msg = str(e)
                self.after(0, lambda: self._on_model_error(err_msg))

        threading.Thread(target=_load, daemon=True).start()

    def _on_model_loaded(self):
        self.status_label.configure(text="✅ OCR model ready", text_color="green")
        if self.current_image_path:
            self.btn_translate.configure(state="normal")

    def _on_model_error(self, err):
        self.status_label.configure(text="❌ Model error", text_color="red")
        messagebox.showerror("OCR Model Error", f"Failed to load manga-ocr:\n{err}")

    # --------------------------------------------------- Screen Snip
    def _snip_screen(self):
        """Hide app, show snip overlay, capture region, OCR + translate."""
        if self.mocr is None:
            messagebox.showinfo("Not Ready", "OCR model is still loading, please wait.")
            return

        # Minimize main window so it's not in the screenshot
        self.withdraw()
        self.update()

        # Small delay to let the window fully disappear
        self.after(200, self._show_snip_overlay)

    def _show_snip_overlay(self):
        SnipOverlay(self, self._on_snip_done)

    def _on_snip_done(self, region_img):
        """Called when the user finishes or cancels the snip."""
        # Restore main window
        self.deiconify()
        self.lift()

        if region_img is None:
            return  # cancelled

        # Save to temp file (manga-ocr works with file paths)
        tmp = os.path.join(tempfile.gettempdir(), "_manga_snip.png")
        region_img.save(tmp)
        self._load_image_from_pil(region_img, tmp)

        # Auto-trigger OCR + translate
        self._extract_and_translate()

    # -------------------------------------------------------- Image loading
    def _open_image(self):
        path = filedialog.askopenfilename(
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.bmp *.webp *.tiff"),
                ("All files", "*.*"),
            ]
        )
        if path:
            self._load_image_from_path(path)

    def _paste_image(self):
        try:
            img = ImageGrab.grabclipboard()
            if img is None:
                messagebox.showinfo("Paste", "No image found in clipboard.")
                return
            tmp = os.path.join(tempfile.gettempdir(), "_manga_paste.png")
            img.save(tmp)
            self._load_image_from_pil(img, tmp)
        except Exception as e:
            messagebox.showerror("Paste Error", str(e))

    def _load_image_from_path(self, path: str):
        try:
            img = Image.open(path)
            self._load_image_from_pil(img, path)
        except Exception as e:
            messagebox.showerror("Image Error", f"Cannot open image:\n{e}")

    def _load_image_from_pil(self, img: Image.Image, path: str):
        """Display a PIL image and store the path for OCR."""
        self.current_image_path = path

        display_img = self._fit_image(img, max_w=620, max_h=600)
        self.photo_image = ctk.CTkImage(
            light_image=display_img,
            dark_image=display_img,
            size=display_img.size,
        )
        self.image_label.configure(image=self.photo_image, text="")

        if self.mocr is not None:
            self.btn_translate.configure(state="normal")
        self.status_label.configure(
            text=f"📷 {os.path.basename(path)}", text_color="white"
        )

    @staticmethod
    def _fit_image(img: Image.Image, max_w: int, max_h: int) -> Image.Image:
        w, h = img.size
        ratio = min(max_w / w, max_h / h, 1.0)
        new_size = (int(w * ratio), int(h * ratio))
        return img.resize(new_size, Image.LANCZOS)

    # ------------------------------------------------ Extract & Translate
    def _extract_and_translate(self):
        if not self.current_image_path or self.mocr is None:
            return

        self.btn_translate.configure(state="disabled")
        self.status_label.configure(text="⏳ Extracting text…", text_color="yellow")

        path = self.current_image_path

        def _work():
            try:
                text = self.mocr(path)
                self.after(0, lambda: self._show_ocr_result(text))
            except Exception as e:
                err_msg = str(e)
                self.after(0, lambda: self._ocr_error(err_msg))

        threading.Thread(target=_work, daemon=True).start()

    def _show_ocr_result(self, japanese_text: str):
        self.ocr_textbox.delete("1.0", "end")
        self.ocr_textbox.insert("1.0", japanese_text)

        self.status_label.configure(text="⏳ Translating…", text_color="yellow")

        def _translate():
            try:
                result = self.translator.translate(japanese_text)
                self.after(0, lambda: self._show_translation(result))
            except Exception as e:
                err_msg = str(e)
                self.after(0, lambda: self._translation_error(err_msg))

        threading.Thread(target=_translate, daemon=True).start()

    def _show_translation(self, english_text: str):
        self.translation_textbox.delete("1.0", "end")
        self.translation_textbox.insert("1.0", english_text)
        self.btn_translate.configure(state="normal")
        self.status_label.configure(text="✅ Done", text_color="green")

    def _ocr_error(self, err: str):
        self.btn_translate.configure(state="normal")
        self.status_label.configure(text="❌ OCR failed", text_color="red")
        messagebox.showerror("OCR Error", err)

    def _translation_error(self, err: str):
        self.btn_translate.configure(state="normal")
        self.status_label.configure(text="❌ Translation failed", text_color="red")
        messagebox.showerror("Translation Error", err)

    # -------------------------------------------------------- Manual input
    def _translate_manual(self):
        text = self.manual_entry.get().strip()
        if not text:
            return

        self.ocr_textbox.delete("1.0", "end")
        self.ocr_textbox.insert("1.0", text)
        self.status_label.configure(text="⏳ Translating…", text_color="yellow")

        def _work():
            try:
                result = self.translator.translate(text)
                self.after(0, lambda: self._show_translation(result))
            except Exception as e:
                err_msg = str(e)
                self.after(0, lambda: self._translation_error(err_msg))

        threading.Thread(target=_work, daemon=True).start()

    # -------------------------------------------------------------- Clear
    def _clear(self):
        self.current_image_path = None
        self.photo_image = None
        self.image_label.configure(
            image="",
            text="No image loaded\n\nClick  ✂ Snip Screen  to capture a region\nor open / paste an image",
        )
        self.ocr_textbox.delete("1.0", "end")
        self.translation_textbox.delete("1.0", "end")
        self.manual_entry.delete(0, "end")
        self.btn_translate.configure(state="disabled")
        self.status_label.configure(
            text="✅ OCR model ready" if self.mocr else "Loading OCR model…",
            text_color="green" if self.mocr else "orange",
        )


if __name__ == "__main__":
    app = MangaTranslateApp()
    app.mainloop()

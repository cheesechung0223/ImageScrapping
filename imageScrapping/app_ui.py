"""
Image Scraper UI – enter website URL or import URLs from txt, then download all images.
Run in PyCharm: set run configuration to app_ui.py or run: python app_ui.py
"""
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from threading import Thread
from queue import Queue

from image_scraper import scrape_images_from_url, scrape_images_from_urls, url_to_folder_name


def ui_log(log_widget: scrolledtext.ScrolledText, msg: str):
    """Thread-safe log append."""
    log_widget.after(0, lambda: _append_log(log_widget, msg))


def _append_log(log_widget: scrolledtext.ScrolledText, msg: str):
    log_widget.insert(tk.END, msg + "\n")
    log_widget.see(tk.END)


def run_scraper(
    urls: list[str],
    output_folder: str,
    log_widget: scrolledtext.ScrolledText,
    progress_var: tk.StringVar,
    done_callback,
    folder_name: str | None = None,
):
    """Run scraper in background and report progress. folder_name: optional subfolder for single URL."""
    def task():
        try:
            if len(urls) == 1:
                def progress(current, total, message):
                    log_widget.after(0, lambda: ui_log(log_widget, message))
                    log_widget.after(0, lambda: progress_var.set(message))

                downloaded, failed, errors = scrape_images_from_url(
                    urls[0], output_folder, progress_callback=progress, subfolder_name=folder_name
                )
                display_path = os.path.join(output_folder, folder_name or url_to_folder_name(urls[0]))
            else:
                def progress(idx, total, message):
                    log_widget.after(0, lambda: ui_log(log_widget, message))
                    log_widget.after(0, lambda: progress_var.set(message))

                downloaded, failed, errors = scrape_images_from_urls(
                    urls, output_folder, progress_callback=progress
                )
                display_path = output_folder

            for e in errors:
                log_widget.after(0, lambda m=e: ui_log(log_widget, f"  Error: {m}"))
            summary = f"Done. Downloaded: {downloaded}, Failed: {failed}. Output: {display_path}"
            log_widget.after(0, lambda: ui_log(log_widget, summary))
            log_widget.after(0, lambda: progress_var.set(summary))
        except Exception as e:
            log_widget.after(0, lambda: ui_log(log_widget, f"Error: {e}"))
            log_widget.after(0, lambda: progress_var.set("Error"))
        finally:
            log_widget.after(0, done_callback)

    t = Thread(target=task, daemon=True)
    t.start()


def main():
    root = tk.Tk()
    root.title("Image Scraper – Scam Prevention Dataset")
    root.geometry("720x520")
    root.minsize(500, 400)

    # URLs to scrape (single or from file)
    urls_list: list[str] = []

    # --- Single URL ---
    f_url = ttk.LabelFrame(root, text="Website URL", padding=8)
    f_url.pack(fill=tk.X, padx=8, pady=6)
    url_var = tk.StringVar()
    ttk.Entry(f_url, textvariable=url_var, width=70).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
    ttk.Button(f_url, text="Add URL", command=lambda: _add_url(url_var, urls_list, log, url_var)).pack(side=tk.RIGHT)

    # --- Import TXT ---
    f_import = ttk.LabelFrame(root, text="Import URLs from file (one URL per line)", padding=8)
    f_import.pack(fill=tk.X, padx=8, pady=6)
    ttk.Button(f_import, text="Import TXT...", command=lambda: _import_txt(urls_list, log)).pack(side=tk.LEFT, padx=(0, 8))
    ttk.Button(f_import, text="Clear list", command=lambda: _clear_list(urls_list, log)).pack(side=tk.LEFT)

    # --- Output folder ---
    f_out = ttk.Frame(root, padding=0)
    f_out.pack(fill=tk.X, padx=8, pady=6)
    out_var = tk.StringVar(value=os.path.abspath(os.path.join(os.path.dirname(__file__), "downloaded_images")))
    ttk.Label(f_out, text="Output folder:").pack(side=tk.LEFT, padx=(0, 8))
    ttk.Entry(f_out, textvariable=out_var, width=55).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
    ttk.Button(f_out, text="Browse...", command=lambda: _browse_out(out_var)).pack(side=tk.RIGHT)

    # --- Folder name (optional, for single URL - each site gets its own subfolder) ---
    f_name = ttk.LabelFrame(root, text="Folder name for this URL (optional; leave empty = auto from URL)", padding=6)
    f_name.pack(fill=tk.X, padx=8, pady=4)
    folder_name_var = tk.StringVar()
    ttk.Entry(f_name, textvariable=folder_name_var, width=50).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
    ttk.Button(f_name, text="Preview", command=lambda: _preview_folder_name(url_var, folder_name_var, log)).pack(side=tk.RIGHT)

    # --- Run ---
    progress_var = tk.StringVar(value="Idle")
    run_btn = ttk.Button(root, text="Start scraping", command=lambda: _start(urls_list, out_var, folder_name_var, log, progress_var, run_btn))
    run_btn.pack(pady=8)

    ttk.Label(root, textvariable=progress_var, foreground="gray").pack()

    # --- Log ---
    log_frame = ttk.LabelFrame(root, text="Log", padding=6)
    log_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
    log = scrolledtext.ScrolledText(log_frame, height=14, wrap=tk.WORD, state=tk.NORMAL)
    log.pack(fill=tk.BOTH, expand=True)

    def _add_url(sv, lst, lw, url_sv):
        u = (sv.get() or "").strip()
        if not u:
            messagebox.showinfo("Add URL", "Please enter a URL first.")
            return
        if not u.startswith("http://") and not u.startswith("https://"):
            u = "https://" + u
        lst.append(u)
        lw.insert(tk.END, f"Added: {u}\n")
        lw.see(tk.END)
        url_sv.set("")

    def _import_txt(lst, lw):
        path = filedialog.askopenfilename(
            title="Select TXT file (one URL per line)",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                lines = [line.strip() for line in f if line.strip()]
            added = 0
            for line in lines:
                u = line.strip()
                if not u or u.startswith("#"):
                    continue
                if not u.startswith("http://") and not u.startswith("https://"):
                    u = "https://" + u
                lst.append(u)
                added += 1
            lw.insert(tk.END, f"Imported {added} URL(s) from {os.path.basename(path)}\n")
            lw.see(tk.END)
            messagebox.showinfo("Import", f"Imported {added} URL(s).")
        except Exception as e:
            messagebox.showerror("Import error", str(e))

    def _clear_list(lst, lw):
        lst.clear()
        lw.insert(tk.END, "URL list cleared.\n")
        lw.see(tk.END)

    def _browse_out(sv):
        d = filedialog.askdirectory(title="Select output folder", initialdir=sv.get())
        if d:
            sv.set(d)

    def _preview_folder_name(url_sv, folder_sv, lw):
        u = (url_sv.get() or "").strip()
        if not u:
            messagebox.showinfo("Preview", "Enter a URL first to see auto folder name.")
            return
        if not u.startswith("http://") and not u.startswith("https://"):
            u = "https://" + u
        name = folder_sv.get() and folder_sv.get().strip() or url_to_folder_name(u)
        lw.insert(tk.END, f"Folder name will be: {name}\n")
        lw.see(tk.END)

    def _start(lst, out_sv, folder_name_sv, lw, prog_sv, btn):
        out_folder = (out_sv.get() or "").strip()
        if not out_folder:
            messagebox.showwarning("Output", "Please set output folder.")
            return
        # Use single URL from entry if list is empty
        if not lst:
            u = (url_var.get() or "").strip()
            if not u:
                messagebox.showwarning("URL", "Enter a URL or import a TXT file with URLs.")
                return
            if not u.startswith("http://") and not u.startswith("https://"):
                u = "https://" + u
            to_run = [u]
            folder_name = (folder_name_sv.get() or "").strip() or None
        else:
            to_run = list(lst)
            folder_name = None
        lw.insert(tk.END, f"Starting scrape for {len(to_run)} URL(s) -> {out_folder}\n")
        lw.see(tk.END)
        btn.config(state=tk.DISABLED)
        run_scraper(
            to_run,
            out_folder,
            lw,
            prog_sv,
            done_callback=lambda: btn.config(state=tk.NORMAL),
            folder_name=folder_name,
        )

    root.mainloop()


if __name__ == "__main__":
    main()

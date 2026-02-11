import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import os
import shutil
import json
import fitz  # PyMuPDF
from PIL import Image, ImageTk

# ===============================
# CONFIG & CONSTANTS
# ===============================
CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    "excel_path": "excel/diagram_list.xlsx",
    "pdf_dir": "pdf",
    "language": "Japanese"
}

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return DEFAULT_CONFIG.copy()
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4, ensure_ascii=False)

config = load_config()
EXCEL_PATH = config["excel_path"]
PDF_DIR = config["pdf_dir"]
DEFAULT_LANG = config.get("language", "Japanese")
os.makedirs(PDF_DIR, exist_ok=True)

COLUMNS = ["Search No","Reference model","Contents","Before correction","After correction","Type 1","Type 2","Type 3","Type 4","Type 5"]
JAPANESE_COLUMNS = ["検索No.","参考機種","内容","訂正前","訂正後","分類1","分類2","分類3","分類4","分類5"]

# ===============================
# LANGUAGE TEXT
# ===============================
with open("lang.json", "r", encoding="utf-8") as f:
    LANG_TEXT = json.load(f)


# ===============================
# EXCEL HANDLING
# ===============================
def load_excel():
    if not os.path.exists(EXCEL_PATH):
        return pd.DataFrame(columns=COLUMNS)
    df = pd.read_excel(EXCEL_PATH, dtype=str).fillna("")
    clean_df = pd.DataFrame({col: df[col] if col in df.columns else "" for col in COLUMNS})
    return clean_df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

def save_excel(df):
    os.makedirs(os.path.dirname(EXCEL_PATH), exist_ok=True)
    df[COLUMNS].to_excel(EXCEL_PATH, index=False)

def export_excel(df, lang):
    headers = JAPANESE_COLUMNS if lang=="Japanese" else COLUMNS
    file = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel","*.xlsx")])
    if file:
        df_out = df.copy()
        df_out.columns = headers
        df_out.to_excel(file, index=False)
        messagebox.showinfo(LANG_TEXT[lang]["export_done"],
                            LANG_TEXT[lang]["export_msg"].format(file=file))

# ===============================
# PDF HANDLING
# ===============================
def find_pdf(search_no):
    search_no_norm = str(search_no).zfill(3)
    for f in os.listdir(PDF_DIR):
        if f.lower().endswith(".pdf") and f"検索no.{search_no_norm}" in f.lower():
            return os.path.join(PDF_DIR, f)
    return None

def generate_pdf_thumbnail(pdf_path, width=700):
    if not pdf_path or not os.path.exists(pdf_path):
        return None
    doc = fitz.open(pdf_path)
    page = doc.load_page(0)
    pix = page.get_pixmap(matrix=fitz.Matrix(2,2))
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    ratio = width / img.width
    img = img.resize((int(img.width*ratio), int(img.height*ratio)))
    doc.close()
    return ImageTk.PhotoImage(img)

# ===============================
# MULTI-SELECT DROPDOWN
# ===============================
class MultiSelectDropdown(tk.Frame):
    def __init__(self, parent, values, label="", width=20, callback=None):
        super().__init__(parent)
        self.values = values
        self.selected = []
        self.callback = callback
        self.button = tk.Button(self, text=label, width=width, command=self.toggle_menu)
        self.button.pack()

    def toggle_menu(self):
        menu = tk.Toplevel(self)
        menu.wm_overrideredirect(True)
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height()
        menu.geometry(f"+{x}+{y}")

        self.vars = {}
        for v in self.values:
            var = tk.BooleanVar(value=v in self.selected)
            chk = tk.Checkbutton(menu, text=v, variable=var,
                                 command=self.update_selection, anchor="w")
            chk.pack(fill="x")
            self.vars[v] = var

        menu.bind("<FocusOut>", lambda e: menu.destroy())
        menu.focus_set()

    def update_selection(self):
        self.selected = [v for v, var in self.vars.items() if var.get()]
        self.button.config(text=f"{len(self.selected)} selected" if self.selected else "")
        if self.callback:
            self.callback()

    def get_selected(self):
        return self.selected

# ===============================
# MAIN APP
# ===============================
class DiagramApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.lang = DEFAULT_LANG
        self.text = LANG_TEXT[self.lang]
        self.df = load_excel()
        self.title(self.text["app_title"])
        self.geometry("1800x900")
        self.create_styles()
        self.create_ui()
        self.update_headers()
        self.refresh_table(self.df)

    def t(self, key):
        return LANG_TEXT[self.lang][key]

    # ---------- Styles ----------
    def create_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Treeview", rowheight=28)

    def stripe_rows(self):
        for i, item in enumerate(self.tree.get_children()):
            current_tags = list(self.tree.item(item, "tags"))
            if i % 2 == 0:
                if "even" not in current_tags:
                    current_tags.append("even")
            else:
                if "odd" not in current_tags:
                    current_tags.append("odd")
            self.tree.item(item, tags=tuple(current_tags))

        self.tree.tag_configure("even", background="light blue")
        self.tree.tag_configure("odd", background="#ffffff")

    # ---------- UI ----------
    def create_ui(self):
        header = tk.Frame(self, bg="#2b2f3a", height=55)
        header.pack(fill="x")

        self.title_lbl = tk.Label(header, fg="white", bg="#2b2f3a",
                                font=("Segoe UI",16,"bold"))
        self.title_lbl.pack(side="left", padx=20)

        self.add_btn = tk.Button(header, command=self.open_add_window)
        self.settings_btn = tk.Button(header, command=self.open_settings)
        self.export_btn = tk.Button(header,
            command=lambda: export_excel(self.filtered_df, self.lang))

        self.export_btn.pack(side="right", padx=10)
        self.settings_btn.pack(side="right")
        self.add_btn.pack(side="right", padx=10)

        self.filter_frame = tk.LabelFrame(self)
        self.filter_frame.pack(fill="x", padx=15, pady=10)
        self.create_filters()

        frame = tk.Frame(self)
        frame.pack(fill="both", expand=True, padx=15, pady=10)

        self.tree = ttk.Treeview(frame, columns=COLUMNS+["PDF"], show="headings")
        vsb = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        self.tree.tag_configure("exists", foreground="green")
        self.tree.tag_configure("missing", foreground="red")
        self.tree.bind("<Double-1>", self.open_pdf_preview)

        # Right-click menu with Delete
        self.menu = tk.Menu(self, tearoff=0)
        self.menu.add_command(label="Edit", command=self.edit_selected_row)
        self.menu.add_command(label="Delete", command=self.delete_selected_row)
        self.tree.bind("<Button-3>", self.show_context_menu)

        for col in COLUMNS:
            self.tree.heading(col, text=col, anchor="center")
            self.tree.column(col, anchor="center")
        self.tree.heading("PDF", text="PDF", anchor="center")
        self.tree.column("PDF", anchor="center")

    # ---------- Filters ----------
    def create_filters(self):
        for w in self.filter_frame.winfo_children():
            w.destroy()
        labels = JAPANESE_COLUMNS if self.lang == "Japanese" else COLUMNS

        self.search_var = tk.StringVar()
        tk.Label(self.filter_frame, text=labels[0]).pack(side="left")
        tk.Entry(self.filter_frame, textvariable=self.search_var, width=10).pack(side="left", padx=5)
        self.search_var.trace_add("write", lambda *_: self.apply_filters())

        tk.Label(self.filter_frame, text=labels[1]).pack(side="left", padx=(20,0))
        models = sorted(self.df["Reference model"].dropna().unique())
        self.model_filter = MultiSelectDropdown(
            self.filter_frame,
            models,
            width=15,
            callback=self.apply_filters
        )
        self.model_filter.pack(side="left", padx=5)

        self.type_filters = {}
        for i in range(1, 6):
            tk.Label(self.filter_frame, text=labels[i+4]).pack(side="left", padx=(20 if i > 1 else 0, 0))
            types = sorted(self.df[f"Type {i}"].dropna().unique())
            msd = MultiSelectDropdown(self.filter_frame, types, width=15, callback=self.apply_filters)
            msd.pack(side="left", padx=5)
            self.type_filters[i] = msd

    def apply_filters(self):
        df = self.df.copy()
        search = self.search_var.get().strip()
        if search:
            df = df[df["Search No"].astype(str).str.contains(search, na=False)]
        selected_models = self.model_filter.get_selected() if self.model_filter else []
        if selected_models:
            df = df[df["Reference model"].isin(selected_models)]
        for i in range(1,6):
            selected_types = self.type_filters[i].get_selected() if i in self.type_filters else []
            if selected_types:
                df = df[df[f"Type {i}"].isin(selected_types)]
        self.refresh_table(df)

    def update_headers(self):
        self.text = LANG_TEXT[self.lang]
        self.title(self.text["app_title"])
        self.title_lbl.config(text=self.text["app_title"])
        self.add_btn.config(text=self.text["add_entry"])
        self.settings_btn.config(text=self.text["settings"])
        self.export_btn.config(text=self.text["export_excel"])
        self.filter_frame.config(text=self.text["filters"])

        headers = JAPANESE_COLUMNS if self.lang=="Japanese" else COLUMNS
        for i, col in enumerate(COLUMNS):
            self.tree.heading(col, text=headers[i])
            self.tree.column(col, width=140, anchor="center")
        self.tree.heading("PDF", text="PDF")

    def refresh_table(self, df):
        self.tree.delete(*self.tree.get_children())
        self.filtered_df = df.copy()
        for _, row in df.iterrows():
            pdf = find_pdf(row["Search No"])
            status = self.t("pdf_exists") if pdf else self.t("pdf_missing")
            tag = "exists" if pdf else "missing"
            self.tree.insert(
                "", "end",
                values=[row[c] for c in COLUMNS] + [status],
                tags=(tag,)
            )
        self.stripe_rows()

    # ---------- Right-click ----------
    def show_context_menu(self, event):
        row_id = self.tree.identify_row(event.y)
        if row_id:
            self.tree.selection_set(row_id)
            self.menu.tk_popup(event.x_root, event.y_root)

    def delete_selected_row(self):
        sel = self.tree.selection()
        if not sel:
            return
        values = self.tree.item(sel, "values")
        search_no = values[0]
        if messagebox.askyesno(self.t("delete_title"), self.t("delete_confirm")):
            idx = self.df[self.df["Search No"]==search_no].index
            self.df.drop(idx, inplace=True)
            save_excel(self.df)
            pdf_path = find_pdf(search_no)
            if pdf_path and os.path.exists(pdf_path):
                os.remove(pdf_path)
            self.refresh_table(self.df)

   # For Edit entry
    def edit_selected_row(self):
        sel = self.tree.selection()
        if not sel:
            return

        values = self.tree.item(sel, "values")
        original_search_no = values[0]

        win = tk.Toplevel(self)
        win.title("Edit Entry")
        win.geometry("550x820")

        labels = JAPANESE_COLUMNS if self.lang == "Japanese" else COLUMNS

        fields = {}
        for i, col in enumerate(COLUMNS):
            tk.Label(win, text=labels[i]).pack(anchor="w", padx=10)
            var = tk.StringVar(value=values[i])
            ent = tk.Entry(win, textvariable=var)
            ent.pack(fill="x", padx=10)
            fields[col] = var

            # Optional: lock Search No
            if col == "Search No":
                ent.config(state="disabled")

        pdf_var = tk.StringVar()
        existing_pdf = find_pdf(original_search_no)

        pdf_label = tk.Label(win,
                            text=os.path.basename(existing_pdf) if existing_pdf else self.t("no_pdf"),
                            fg="green" if existing_pdf else "red")
        pdf_label.pack(pady=10)

        preview_label = tk.Label(win)
        preview_label.pack(pady=5)

        if existing_pdf:
            thumb = generate_pdf_thumbnail(existing_pdf, width=80)
            if thumb:
                preview_label.config(image=thumb)
                preview_label.image = thumb

        def select_new_pdf():
            p = filedialog.askopenfilename(filetypes=[("PDF", "*.pdf")])
            if p:
                pdf_var.set(p)
                pdf_label.config(text=os.path.basename(p), fg="green")
                thumb = generate_pdf_thumbnail(p, width=80)
                if thumb:
                    preview_label.config(image=thumb)
                    preview_label.image = thumb

        ttk.Button(win, text="Replace PDF", command=select_new_pdf).pack()
        ttk.Button(
            win,
            text="Save Changes",
            command=lambda: self.save_edited_entry(
                win, fields, pdf_var, original_search_no
            )
        ).pack(pady=15)

    def save_edited_entry(self, win, fields, pdf_var, original_search_no):
        idx = self.df[self.df["Search No"] == original_search_no].index
        if idx.empty:
            return

        for col in COLUMNS:
            self.df.loc[idx, col] = fields[col].get()

        # Replace PDF if user selected a new one
        if pdf_var.get():
            if not os.path.exists(PDF_DIR):
                os.makedirs(PDF_DIR)

            old_pdf = find_pdf(original_search_no)
            if old_pdf and os.path.exists(old_pdf):
                os.remove(old_pdf)

            shutil.copy(pdf_var.get(), PDF_DIR)

        save_excel(self.df)
        self.refresh_table(self.df)
        win.destroy()


    # ---------- PDF Preview ----------
    def open_pdf_preview(self, event):
        sel = self.tree.selection()
        if not sel: return
        values = self.tree.item(sel,"values")
        pdf = find_pdf(values[0])
        if not pdf:
            messagebox.showerror(self.t("error"), self.t("pdf_not_found"))
            return

        win = tk.Toplevel(self)
        win.title(self.t("pdf_preview"))
        win.geometry("620x500")
        canvas = tk.Canvas(win)
        scrollbar = tk.Scrollbar(win, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        frame = tk.Frame(canvas)
        canvas.create_window((0,0), window=frame, anchor="nw")

        thumb = generate_pdf_thumbnail(pdf, width=700)
        if thumb:
            lbl = tk.Label(frame, image=thumb)
            lbl.image = thumb
            lbl.pack(padx=10, pady=10)

        btn_frame = tk.Frame(frame)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text=self.t("open_pdf"), command=lambda: os.startfile(pdf)).pack(side="left", padx=5)
        tk.Button(btn_frame, text=self.t("close"), command=win.destroy).pack(side="left", padx=5)

        frame.update_idletasks()
        canvas.config(scrollregion=canvas.bbox("all"))

    # ---------- Settings ----------
    def open_settings(self):
        win = tk.Toplevel(self)
        win.title(self.t("settings_title"))
        win.geometry("500x300")

        excel_var = tk.StringVar(value=EXCEL_PATH)
        pdf_var = tk.StringVar(value=PDF_DIR)
        lang_var = tk.StringVar(value=self.lang)

        tk.Label(win, text=self.t("excel_file")).pack(anchor="w", padx=10)
        tk.Entry(win, textvariable=excel_var).pack(fill="x", padx=10)

        tk.Label(win, text=self.t("pdf_folder")).pack(anchor="w", padx=10, pady=(10,0))
        tk.Entry(win, textvariable=pdf_var).pack(fill="x", padx=10)

        tk.Label(win, text=self.t("default_language")).pack(anchor="w", padx=10, pady=(10,0))
        ttk.Combobox(win, textvariable=lang_var,
                     values=["Japanese","English"]).pack(anchor="w", padx=10)

        ttk.Button(win, text=self.t("save_settings"),
                   command=lambda:self.save_settings(win, excel_var, pdf_var, lang_var)).pack(pady=20)

    def save_settings(self, win, excel_var, pdf_var, lang_var):
        global EXCEL_PATH, PDF_DIR
        EXCEL_PATH = excel_var.get()
        PDF_DIR = pdf_var.get()
        self.lang = lang_var.get()
        save_config({"excel_path":EXCEL_PATH,"pdf_dir":PDF_DIR,"language":self.lang})
        self.df = load_excel()
        self.update_headers()
        self.refresh_table(self.df)
        self.create_filters()
        win.destroy()

    # ---------- Add Entry ----------
    def open_add_window(self):
        win = tk.Toplevel(self)
        win.title(self.t("add_title"))
        win.geometry("550x820")

        # Choose labels dynamically
        labels = JAPANESE_COLUMNS if self.lang == "Japanese" else COLUMNS

        fields = {}
        for i, col in enumerate(COLUMNS):  # keep COLUMNS as keys for saving
            tk.Label(win, text=labels[i]).pack(anchor="w", padx=10)
            var = tk.StringVar()
            tk.Entry(win, textvariable=var).pack(fill="x", padx=10)
            fields[col] = var

        pdf_var = tk.StringVar()
        lbl = tk.Label(win, text=self.t("no_pdf"), fg="red")
        lbl.pack(pady=10)

        preview_label = tk.Label(win)
        preview_label.pack(pady=5)

        def select_pdf():
            p=filedialog.askopenfilename(filetypes=[("PDF","*.pdf")])
            if p:
                pdf_var.set(p)
                lbl.config(text=os.path.basename(p), fg="green")
                thumb = generate_pdf_thumbnail(p, width=80)
                if thumb:
                    preview_label.config(image=thumb)
                    preview_label.image = thumb

        ttk.Button(win,text=self.t("select_pdf"), command=select_pdf).pack()
        ttk.Button(win,text=self.t("save_entry"),
                   command=lambda:self.save_entry(win,fields,pdf_var)).pack(pady=15)

    def save_entry(self, win, fields, pdf_var):
        if not fields["Search No"].get() or not pdf_var.get():
            messagebox.showerror(self.t("error"), self.t("required_error"))
            return
        if not os.path.exists(PDF_DIR):
            os.makedirs(PDF_DIR)
        shutil.copy(pdf_var.get(), PDF_DIR)
        duplicate = self.df[(self.df["Search No"]==fields["Search No"].get()) & 
                            (self.df["Reference model"]==fields["Reference model"].get())]
        if not duplicate.empty:
            messagebox.showerror(self.t("error"), self.t("duplicate_error"))
            return
        self.df = pd.concat([self.df,
            pd.DataFrame([{c:fields[c].get() for c in COLUMNS}])])
        save_excel(self.df)
        self.refresh_table(self.df)
        win.destroy()

# ===============================
# RUN
# ===============================
if __name__ == "__main__":
    DiagramApp().mainloop()

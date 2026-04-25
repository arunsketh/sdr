"""
FAA Service Difficulty Report (SDR) Analyser
Multi-year CSV analysis tool with tkinter GUI + matplotlib charts.

Requirements (all included with standard Python or pip-installable):
    pip install pandas matplotlib

Run:
    python sdr_analyser.py
"""

import os
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from collections import defaultdict

import pandas as pd
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import matplotlib.ticker as mticker

# ── ATA / JASC chapter lookup ──────────────────────────────────────────────
JASC_MAP = {
    "21": "Air conditioning",   "22": "Auto flight",        "23": "Communications",
    "24": "Electrical power",   "25": "Equipment/furnishings","26": "Fire protection",
    "27": "Flight controls",    "28": "Fuel",               "29": "Hydraulic power",
    "30": "Ice/rain protection","31": "Instruments",        "32": "Landing gear",
    "33": "Lights",             "34": "Navigation",         "35": "Oxygen",
    "36": "Pneumatic",          "38": "Water/waste",        "49": "APU",
    "51": "Structures",         "52": "Doors",              "53": "Fuselage",
    "54": "Nacelles/pylons",    "55": "Stabilizers",        "56": "Windows",
    "57": "Wings",              "71": "Power plant",        "72": "Engine turbine",
    "73": "Engine fuel/control","74": "Ignition",           "75": "Air",
    "76": "Engine controls",    "77": "Engine indicating",  "78": "Exhaust",
    "79": "Oil",                "80": "Starting",
}
STAGE_MAP = {
    "IN": "Inspection",     "CL": "Climb",          "NR": "Normal cruise",
    "CR": "Cruise",         "TX": "Taxi",           "TO": "Takeoff",
    "LD": "Landing",        "AP": "Approach",       "MA": "Maintenance",
    "GR": "Ground run",     "PG": "Parking/storage","MN": "Maneuvering",
    "OT": "Other",          "DE": "Descent",
}
CATEGORIES = {
    "ATA chapter (system)":    "ata",
    "Part condition":          "condition",
    "Aircraft make":           "make",
    "Stage of operation":      "stage",
    "SDR type (A/G)":          "sdrtype",
    "How discovered":          "howdisc",
    "Nature of condition":     "nature",
}
HOW_DISC_MAP = {
    "V": "Visual inspection", "O": "Operational check", "C": "Functional check",
    "9": "Other",             "E": "Electronic check",  "F": "Flight crew report",
    "A": "Accidental damage", "T": "Testing",
}
NATURE_MAP = {
    "O": "Other",             "L": "Cracking",          "J": "Corrosion",
    "B": "Broken/fractured",  "N": "Deterioration",     "D": "Dent/gouge",
    "G": "Missing",           "H": "Wear",              "F": "Deformation",
    "E": "Leaking",           "C": "Burned",
}

CHART_TYPES = ["Horizontal bar", "Vertical bar", "Line (trend by year)", "Pie / donut"]
TOP_N_OPTIONS = [5, 10, 15, 20, 50, 999]

# Colour palette – works on white bg
PALETTE = [
    "#2E6FBF","#1A8C6A","#C44D2A","#A86500","#8B2525",
    "#4A3FA0","#2E6B1A","#8B2560","#5A5A55","#0A5A46",
    "#A83010","#3A2E8B","#1F5000","#602040","#3A3A38",
]


# ── helpers ────────────────────────────────────────────────────────────────

def detect_year(filename: str) -> str:
    m = re.search(r"20\d{2}", filename)
    return m.group(0) if m else os.path.splitext(os.path.basename(filename))[0]


def get_category(series: pd.Series, key: str) -> pd.Series:
    if key == "ata":
        codes = series.astype(str).str[:2]
        return codes.map(JASC_MAP).fillna("ATA " + codes)
    if key == "condition":
        return series.astype(str).str.strip().str.title().replace("Nan", "Unknown")
    if key == "make":
        return series.astype(str).str.strip().str.upper().replace("NAN", "Unknown")
    if key == "stage":
        return series.astype(str).str.strip().map(STAGE_MAP).fillna(series.astype(str).str.strip())
    if key == "sdrtype":
        return series.map({"A": "Aircraft (A)", "G": "Engine (G)"}).fillna("Unknown")
    if key == "howdisc":
        return series.astype(str).str.strip().map(HOW_DISC_MAP).fillna(series.astype(str).str.strip())
    if key == "nature":
        return series.astype(str).str.strip().map(NATURE_MAP).fillna(series.astype(str).str.strip())
    return series.astype(str)


def col_for_key(key: str) -> str:
    return {
        "ata":       "JASCCode",
        "condition": "PartCondition",
        "make":      "AircraftMake",
        "stage":     "StageOfOperationCode",
        "sdrtype":   "SDRType",
        "howdisc":   "HowDiscoveredCode",
        "nature":    "NatureOfConditionA",
    }[key]


# ── Main application ───────────────────────────────────────────────────────

class SDRApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("FAA SDR Multi-Year Analyser")
        self.geometry("1280x820")
        self.minsize(900, 600)
        self.configure(bg="#F5F5F3")

        self.data: dict[str, pd.DataFrame] = {}   # year → DataFrame
        self._build_ui()
        self._apply_style()

    # ── Style ──────────────────────────────────────────────────────────────

    def _apply_style(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        BG, FG, ACC = "#F5F5F3", "#1A1A18", "#2E6FBF"
        s.configure("TFrame",       background=BG)
        s.configure("TLabelframe",  background=BG, foreground=FG, font=("Helvetica", 10, "bold"))
        s.configure("TLabelframe.Label", background=BG, foreground=FG)
        s.configure("TLabel",       background=BG, foreground=FG, font=("Helvetica", 10))
        s.configure("TButton",      background=ACC, foreground="white",
                    font=("Helvetica", 10, "bold"), padding=6, relief="flat")
        s.map("TButton", background=[("active", "#1A5099")])
        s.configure("Accent.TButton", background="#C44D2A", foreground="white",
                    font=("Helvetica", 10, "bold"), padding=6, relief="flat")
        s.map("Accent.TButton", background=[("active", "#A83010")])
        s.configure("TCombobox",    font=("Helvetica", 10))
        s.configure("Treeview",     font=("Helvetica", 9), rowheight=22)
        s.configure("Treeview.Heading", font=("Helvetica", 9, "bold"), background="#DDDBD5", foreground=FG)
        s.configure("TScrollbar",   background="#DDDBD5")

    # ── UI layout ──────────────────────────────────────────────────────────

    def _build_ui(self):
        # Top bar
        top = ttk.Frame(self, padding=(12, 8))
        top.pack(fill="x")

        ttk.Label(top, text="SDR Multi-Year Analyser",
                  font=("Helvetica", 16, "bold")).pack(side="left")

        btn_frame = ttk.Frame(top)
        btn_frame.pack(side="right")
        ttk.Button(btn_frame, text="+ Load CSV files", command=self._load_files).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="Clear all", style="Accent.TButton",
                   command=self._clear_all).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="Export chart", command=self._export_chart).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="Export table CSV", command=self._export_table).pack(side="left", padx=4)

        # Divider
        ttk.Separator(self, orient="horizontal").pack(fill="x")

        # Main pane: left sidebar + right chart area
        main = ttk.Frame(self)
        main.pack(fill="both", expand=True)

        self._build_sidebar(main)
        self._build_chart_area(main)

    def _build_sidebar(self, parent):
        sidebar = ttk.Frame(parent, width=270, padding=(10, 10))
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        # ── Loaded files ──
        lf1 = ttk.LabelFrame(sidebar, text=" Loaded files ", padding=8)
        lf1.pack(fill="x", pady=(0, 10))

        self._file_listbox = tk.Listbox(lf1, height=6, font=("Helvetica", 9),
                                         bg="#EEECEA", selectmode="extended",
                                         relief="flat", bd=0, highlightthickness=0)
        self._file_listbox.pack(fill="both")
        ttk.Button(lf1, text="Remove selected", command=self._remove_selected,
                   style="Accent.TButton").pack(fill="x", pady=(6, 0))

        # ── Controls ──
        lf2 = ttk.LabelFrame(sidebar, text=" Analysis options ", padding=8)
        lf2.pack(fill="x", pady=(0, 10))

        def row(label, widget_fn):
            ttk.Label(lf2, text=label, font=("Helvetica", 9)).pack(anchor="w")
            w = widget_fn(lf2)
            w.pack(fill="x", pady=(2, 8))
            return w

        self._cat_var = tk.StringVar(value="ATA chapter (system)")
        self._cat_cb  = row("Category", lambda p: ttk.Combobox(
            p, textvariable=self._cat_var, values=list(CATEGORIES.keys()),
            state="readonly", font=("Helvetica", 9)))

        self._chart_var = tk.StringVar(value="Horizontal bar")
        self._chart_cb  = row("Chart type", lambda p: ttk.Combobox(
            p, textvariable=self._chart_var, values=CHART_TYPES,
            state="readonly", font=("Helvetica", 9)))

        self._topn_var = tk.IntVar(value=10)
        self._topn_cb  = row("Show top N", lambda p: ttk.Combobox(
            p, textvariable=self._topn_var,
            values=[str(n) if n != 999 else "All" for n in TOP_N_OPTIONS],
            state="readonly", font=("Helvetica", 9)))
        self._topn_cb.set("10")

        self._norm_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(lf2, text="Normalise to % of year total",
                        variable=self._norm_var).pack(anchor="w", pady=(0, 6))

        ttk.Button(lf2, text="▶  Run analysis", command=self._run).pack(fill="x")

        # ── Summary metrics ──
        lf3 = ttk.LabelFrame(sidebar, text=" Summary ", padding=8)
        lf3.pack(fill="x", pady=(0, 10))
        self._summary_text = tk.Text(lf3, height=7, font=("Courier", 9),
                                      bg="#EEECEA", relief="flat", bd=0,
                                      state="disabled", wrap="word")
        self._summary_text.pack(fill="both")

        # ── Filter ──
        lf4 = ttk.LabelFrame(sidebar, text=" Filter category (contains) ", padding=8)
        lf4.pack(fill="x")
        self._filter_var = tk.StringVar()
        ttk.Entry(lf4, textvariable=self._filter_var, font=("Helvetica", 9)).pack(fill="x")
        ttk.Button(lf4, text="Apply filter", command=self._run).pack(fill="x", pady=(4, 0))

    def _build_chart_area(self, parent):
        right = ttk.Frame(parent, padding=(6, 6, 10, 10))
        right.pack(side="left", fill="both", expand=True)

        # Notebook: chart + table
        self._nb = ttk.Notebook(right)
        self._nb.pack(fill="both", expand=True)

        # Chart tab
        chart_frame = ttk.Frame(self._nb)
        self._nb.add(chart_frame, text="  Chart  ")

        self._fig = Figure(figsize=(9, 6), dpi=100, facecolor="#F5F5F3")
        self._ax  = self._fig.add_subplot(111)
        self._canvas = FigureCanvasTkAgg(self._fig, master=chart_frame)
        self._canvas.get_tk_widget().pack(fill="both", expand=True)
        toolbar = NavigationToolbar2Tk(self._canvas, chart_frame)
        toolbar.update()

        # Table tab
        table_frame = ttk.Frame(self._nb)
        self._nb.add(table_frame, text="  Data table  ")
        self._build_table(table_frame)

        # Status bar
        self._status = tk.StringVar(value="Load CSV files to begin.")
        ttk.Label(right, textvariable=self._status, font=("Helvetica", 9),
                  foreground="#777").pack(anchor="w", pady=(4, 0))

    def _build_table(self, parent):
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True)

        self._tree = ttk.Treeview(frame, show="headings", selectmode="extended")
        vsb = ttk.Scrollbar(frame, orient="vertical",   command=self._tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

    # ── File management ────────────────────────────────────────────────────

    def _load_files(self):
        paths = filedialog.askopenfilenames(
            title="Select SDR CSV files",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if not paths:
            return
        for path in paths:
            year = detect_year(os.path.basename(path))
            if year in self.data:
                if not messagebox.askyesno("Overwrite?",
                        f"Year {year} is already loaded. Overwrite?"):
                    continue
            try:
                df = pd.read_csv(path, low_memory=False)
                self.data[year] = df
            except Exception as e:
                messagebox.showerror("Load error", f"{os.path.basename(path)}\n{e}")
                continue
        self._refresh_filelist()
        if self.data:
            self._run()

    def _refresh_filelist(self):
        self._file_listbox.delete(0, "end")
        for year in sorted(self.data):
            rows = len(self.data[year])
            self._file_listbox.insert("end", f"{year}  —  {rows:,} rows")

    def _remove_selected(self):
        sel = self._file_listbox.curselection()
        years = sorted(self.data.keys())
        for idx in reversed(sel):
            del self.data[years[idx]]
        self._refresh_filelist()
        self._run()

    def _clear_all(self):
        self.data.clear()
        self._refresh_filelist()
        self._ax.clear()
        self._canvas.draw()
        self._clear_table()
        self._set_summary("")
        self._status.set("All data cleared.")

    # ── Analysis ───────────────────────────────────────────────────────────

    def _get_topn(self) -> int:
        val = self._topn_cb.get()
        return 999 if val == "All" else int(val)

    def _run(self):
        if not self.data:
            self._status.set("No data loaded.")
            return

        cat_label = self._cat_var.get()
        cat_key   = CATEGORIES[cat_label]
        chart_type = self._chart_var.get()
        top_n      = self._get_topn()
        normalise  = self._norm_var.get()
        filt       = self._filter_var.get().strip().lower()

        years = sorted(self.data.keys())
        col   = col_for_key(cat_key)

        # Aggregate counts per (year, category)
        year_counts: dict[str, dict[str, int]] = {}
        total_counts: dict[str, int] = defaultdict(int)

        for year in years:
            df = self.data[year]
            if col not in df.columns:
                year_counts[year] = {}
                continue
            cats = get_category(df[col], cat_key)
            vc = cats.value_counts()
            year_counts[year] = vc.to_dict()
            for k, v in vc.items():
                total_counts[k] += v

        # Filter
        if filt:
            total_counts = {k: v for k, v in total_counts.items()
                            if filt in k.lower()}

        # Sort & slice
        sorted_cats = sorted(total_counts, key=lambda k: total_counts[k], reverse=True)
        if top_n != 999:
            sorted_cats = sorted_cats[:top_n]

        if not sorted_cats:
            self._status.set("No data matches the current filter.")
            return

        self._draw_chart(years, year_counts, sorted_cats, cat_label, chart_type, normalise, total_counts)
        self._populate_table(years, year_counts, sorted_cats, normalise)
        self._update_summary(years, total_counts, sorted_cats)
        self._status.set(
            f"Showing {len(sorted_cats)} categories · {len(years)} year(s) · "
            f"{sum(len(self.data[y]) for y in years):,} total reports")

    # ── Chart drawing ──────────────────────────────────────────────────────

    def _draw_chart(self, years, year_counts, categories, cat_label,
                    chart_type, normalise, total_counts):
        self._ax.clear()
        fig = self._fig
        ax  = self._ax
        fig.set_facecolor("#F5F5F3")
        ax.set_facecolor("#FAFAF8")

        # ── Normalise helper ──
        def get_values(year, cats):
            raw = [year_counts.get(year, {}).get(c, 0) for c in cats]
            if normalise:
                total = sum(year_counts.get(year, {}).values()) or 1
                return [v / total * 100 for v in raw]
            return raw

        if chart_type == "Pie / donut":
            # Combine across all years
            values = [total_counts.get(c, 0) for c in categories]
            colours = PALETTE[:len(categories)]
            wedges, texts, autotexts = ax.pie(
                values, labels=None, colors=colours,
                autopct="%1.1f%%", startangle=140,
                wedgeprops=dict(width=0.55, edgecolor="#F5F5F3", linewidth=1.5),
                pctdistance=0.75)
            for at in autotexts:
                at.set_fontsize(8)
                at.set_color("#1A1A18")
            ax.legend(categories, loc="lower center", fontsize=8,
                      bbox_to_anchor=(0.5, -0.12), ncol=3,
                      framealpha=0.4, edgecolor="#DDDBD5")
            ax.set_title(cat_label, fontsize=12, fontweight="bold", pad=14)

        elif chart_type == "Line (trend by year)":
            if len(years) < 2:
                messagebox.showinfo("Need more years",
                    "Line chart requires at least 2 years of data.")
                return
            x = list(range(len(years)))
            for i, cat in enumerate(categories):
                vals = [year_counts.get(y, {}).get(cat, 0) for y in years]
                if normalise:
                    vals = [v / (sum(year_counts.get(y, {}).values()) or 1) * 100 for v in vals]
                ax.plot(x, vals, marker="o", linewidth=2,
                        color=PALETTE[i % len(PALETTE)], label=cat, alpha=0.85)
            ax.set_xticks(x)
            ax.set_xticklabels(years, fontsize=9)
            ax.yaxis.set_major_formatter(
                mticker.PercentFormatter() if normalise else mticker.FuncFormatter(
                    lambda v, _: f"{int(v):,}"))
            ax.set_ylabel("% of year total" if normalise else "Report count", fontsize=9)
            ax.set_title(f"{cat_label} — trend over years", fontsize=12, fontweight="bold")
            ax.legend(fontsize=8, loc="upper left", framealpha=0.4, edgecolor="#DDDBD5")
            ax.grid(axis="y", color="#DDDBD5", linewidth=0.6)

        elif chart_type in ("Horizontal bar", "Vertical bar"):
            n_cats  = len(categories)
            n_years = len(years)
            bar_w   = 0.7 / n_years if n_years > 1 else 0.6
            positions = list(range(n_cats))

            for i, year in enumerate(years):
                vals = get_values(year, categories)
                offsets = [p + (i - n_years / 2 + 0.5) * bar_w for p in positions]

                if chart_type == "Horizontal bar":
                    ax.barh(offsets, vals, height=bar_w * 0.9,
                            color=PALETTE[i % len(PALETTE)], label=year, alpha=0.88)
                else:
                    ax.bar(offsets, vals, width=bar_w * 0.9,
                           color=PALETTE[i % len(PALETTE)], label=year, alpha=0.88)

            tick_labels = [c if len(c) <= 26 else c[:24] + "…" for c in categories]

            if chart_type == "Horizontal bar":
                ax.set_yticks(positions)
                ax.set_yticklabels(tick_labels, fontsize=8)
                ax.xaxis.set_major_formatter(
                    mticker.PercentFormatter() if normalise else mticker.FuncFormatter(
                        lambda v, _: f"{int(v):,}"))
                ax.set_xlabel("% of year total" if normalise else "Report count", fontsize=9)
                ax.invert_yaxis()
                ax.grid(axis="x", color="#DDDBD5", linewidth=0.6)
            else:
                ax.set_xticks(positions)
                ax.set_xticklabels(tick_labels, rotation=35, ha="right", fontsize=8)
                ax.yaxis.set_major_formatter(
                    mticker.PercentFormatter() if normalise else mticker.FuncFormatter(
                        lambda v, _: f"{int(v):,}"))
                ax.set_ylabel("% of year total" if normalise else "Report count", fontsize=9)
                ax.grid(axis="y", color="#DDDBD5", linewidth=0.6)

            ax.set_title(cat_label, fontsize=12, fontweight="bold")
            if n_years > 1:
                ax.legend(fontsize=9, framealpha=0.4, edgecolor="#DDDBD5")

        ax.spines[["top", "right"]].set_visible(False)
        ax.spines[["left", "bottom"]].set_color("#BBBAB5")
        ax.tick_params(colors="#555")
        fig.tight_layout(pad=1.8)
        self._canvas.draw()
        self._nb.select(0)

    # ── Table ──────────────────────────────────────────────────────────────

    def _clear_table(self):
        self._tree.delete(*self._tree.get_children())
        self._tree["columns"] = []

    def _populate_table(self, years, year_counts, categories, normalise):
        self._clear_table()
        cols = ["Category"] + years + ["Total"]
        self._tree["columns"] = cols
        for c in cols:
            self._tree.heading(c, text=c, anchor="w")
            w = 90 if c != "Category" else 220
            self._tree.column(c, width=w, anchor="e" if c != "Category" else "w")

        for cat in categories:
            year_vals = []
            for year in years:
                raw = year_counts.get(year, {}).get(cat, 0)
                if normalise:
                    total = sum(year_counts.get(year, {}).values()) or 1
                    year_vals.append(f"{raw/total*100:.1f}%")
                else:
                    year_vals.append(f"{raw:,}")
            total_raw = sum(year_counts.get(y, {}).get(cat, 0) for y in years)
            total_str = f"{total_raw:,}" if not normalise else "—"
            self._tree.insert("", "end", values=[cat] + year_vals + [total_str])

    # ── Summary ────────────────────────────────────────────────────────────

    def _update_summary(self, years, total_counts, categories):
        total_reports = sum(len(self.data[y]) for y in years)
        top3 = categories[:3]
        lines = [
            f"Years loaded : {len(years)}  ({', '.join(sorted(years))})",
            f"Total reports: {total_reports:,}",
            "",
            "Top categories (all years):",
        ]
        for i, cat in enumerate(top3, 1):
            n = total_counts.get(cat, 0)
            pct = n / total_reports * 100 if total_reports else 0
            lines.append(f"  {i}. {cat[:28]:<28} {n:>7,}  ({pct:.1f}%)")

        # YoY change on top category
        if len(years) >= 2 and top3:
            top = top3[0]
            y1  = sorted(years)[-2]
            y2  = sorted(years)[-1]
            # look up raw year counts
            c1 = sum(
                1 for _, row in self.data[y1].iterrows()
                if str(row.get(col_for_key(CATEGORIES[self._cat_var.get()]), "")).strip()
                   in [k for k in self.data[y1].get(col_for_key(CATEGORIES[self._cat_var.get()]), pd.Series(dtype=str)).astype(str).unique()]
            )
            # simpler: just use year_counts from data we've already computed
            lines.append("")
            lines.append(f"Latest year: {y2}")
        self._set_summary("\n".join(lines))

    def _set_summary(self, text: str):
        self._summary_text.config(state="normal")
        self._summary_text.delete("1.0", "end")
        self._summary_text.insert("end", text)
        self._summary_text.config(state="disabled")

    # ── Export ─────────────────────────────────────────────────────────────

    def _export_chart(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG image", "*.png"), ("PDF", "*.pdf"), ("SVG", "*.svg")])
        if path:
            self._fig.savefig(path, dpi=150, bbox_inches="tight")
            messagebox.showinfo("Saved", f"Chart saved to:\n{path}")

    def _export_table(self):
        if not self._tree.get_children():
            messagebox.showwarning("Nothing to export", "Run an analysis first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV", "*.csv")])
        if not path:
            return
        cols = self._tree["columns"]
        rows = [self._tree.item(i)["values"] for i in self._tree.get_children()]
        pd.DataFrame(rows, columns=cols).to_csv(path, index=False)
        messagebox.showinfo("Saved", f"Table saved to:\n{path}")


# ── Entry point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = SDRApp()
    app.mainloop()

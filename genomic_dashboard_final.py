"""
Genomic Data Pipeline: Sample Management, Gene Sequencing & Mutation Variant Dashboard

Name    : CHARUVARSHINI M
Reg No. : 25SSDS415014

How to run
----------
    python3 "genomic dashboard final.py"          (Mac / Linux)
    python "genomic dashboard final.py"           (Windows)

* On a normal computer (VS Code, IDLE, Terminal, Command Prompt) the graphical
  dashboard window opens.
* In Google Colab / Jupyter, or on any machine without tkinter or without a
  display, the program automatically switches to a text-menu version that has
  exactly the same features and the same database - so it never crashes.
* To force the text version anywhere, run with:  --console

Only Python's standard library is used (sqlite3, tkinter) - nothing to install.
"""

import os
import sys
import sqlite3
import tempfile

# tkinter is optional: if it is missing (Colab, minimal Linux installs) the
# program falls back to the text-menu interface instead of crashing.
try:
    import tkinter as tk
    from tkinter import ttk, messagebox
    TK_AVAILABLE = True
except Exception:
    tk = ttk = messagebox = None
    TK_AVAILABLE = False


# DATABASE PATH FIX

def resolve_db_path():
    """Put genomic.db next to this script; fall back to a writable folder.

    __file__ does not exist in notebooks, and the script's folder may be
    read-only on some machines, so try several locations.
    """
    candidates = []

    try:
        candidates.append(os.path.dirname(os.path.abspath(__file__)))
    except NameError:
        pass

    candidates.append(os.getcwd())
    candidates.append(os.path.expanduser("~"))
    candidates.append(tempfile.gettempdir())

    for folder in candidates:
        try:
            if folder and os.path.isdir(folder) and os.access(folder, os.W_OK):
                return os.path.join(folder, "genomic.db")
        except Exception:
            continue

    return "genomic.db"


DB_FILE = resolve_db_path()

MUTATION_TYPES = [
    "SNP", "Insertion", "Deletion", "Missense",
    "Nonsense", "Frameshift", "Substitution"
]

MAX_INT = 2 ** 63 - 1  # largest integer SQLite can store


# DATABASE LAYER

def get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_conn()

    try:
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS samples (
                sample_id INTEGER PRIMARY KEY AUTOINCREMENT,
                sample_name TEXT NOT NULL UNIQUE,
                organism_species TEXT NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS genes (
                gene_id INTEGER PRIMARY KEY AUTOINCREMENT,
                sample_id INTEGER NOT NULL,
                gene_symbol TEXT NOT NULL,
                sequence_length_bp INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (sample_id)
                    REFERENCES samples(sample_id)
                    ON DELETE CASCADE
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS variants (
                variant_id INTEGER PRIMARY KEY AUTOINCREMENT,
                gene_id INTEGER NOT NULL,
                mutation_type TEXT NOT NULL,
                chromosome_position INTEGER NOT NULL,
                FOREIGN KEY (gene_id)
                    REFERENCES genes(gene_id)
                    ON DELETE CASCADE
            )
        """)

        cur.execute("SELECT COUNT(*) FROM samples")

        # Default data is inserted only when the database is empty.
        if cur.fetchone()[0] == 0:

            samples = [
                ("SMP-001", "Homo sapiens"),
                ("SMP-002", "Mus musculus"),
                ("SMP-003", "Homo sapiens")
            ]

            cur.executemany(
                "INSERT INTO samples (sample_name, organism_species) VALUES (?, ?)",
                samples
            )

            genes = [
                (1, "BRCA1", 81189),
                (1, "TP53", 19149),
                (2, "Trp53", 11000),
                (3, "EGFR", 188307)
            ]

            cur.executemany(
                """INSERT INTO genes
                (sample_id, gene_symbol, sequence_length_bp)
                VALUES (?, ?, ?)""",
                genes
            )

            variants = [
                (1, "Missense", 43044295),
                (1, "Deletion", 43045802),
                (2, "SNP", 7675088),
                (3, "Insertion", 7661779),
                (4, "Substitution", 55191822)
            ]

            cur.executemany(
                """INSERT INTO variants
                (gene_id, mutation_type, chromosome_position)
                VALUES (?, ?, ?)""",
                variants
            )

        conn.commit()

    finally:
        conn.close()


def add_record(sample_name, species, gene_symbol,
               seq_len, mutation_type, position):
    """Insert a sample (only if new), then its gene, then its variant.

    Returns True if a brand-new sample profile was created, False if an
    existing sample was reused.
    """

    conn = get_conn()

    try:
        cur = conn.cursor()

        cur.execute(
            "SELECT sample_id FROM samples WHERE sample_name = ?",
            (sample_name,)
        )

        row = cur.fetchone()

        if row:
            sample_id = row[0]
        else:
            cur.execute(
                """INSERT INTO samples
                (sample_name, organism_species)
                VALUES (?, ?)""",
                (sample_name, species)
            )
            sample_id = cur.lastrowid

        cur.execute(
            """INSERT INTO genes
            (sample_id, gene_symbol, sequence_length_bp)
            VALUES (?, ?, ?)""",
            (sample_id, gene_symbol, seq_len)
        )

        gene_id = cur.lastrowid

        cur.execute(
            """INSERT INTO variants
            (gene_id, mutation_type, chromosome_position)
            VALUES (?, ?, ?)""",
            (gene_id, mutation_type, position)
        )

        conn.commit()
        return row is None

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def delete_record(kind, record_id):

    table, col = {
        "sample": ("samples", "sample_id"),
        "gene": ("genes", "gene_id"),
        "variant": ("variants", "variant_id")
    }[kind]

    conn = get_conn()

    try:
        conn.execute(
            f"DELETE FROM {table} WHERE {col} = ?",
            (record_id,)
        )
        conn.commit()

    finally:
        conn.close()


def query(sql, params=()):

    conn = get_conn()

    try:
        cur = conn.cursor()
        cur.execute(sql, params)

        cols = [d[0] for d in cur.description]

        return cols, cur.fetchall()

    finally:
        conn.close()


# SHARED LOGIC (used by both the window and the text version)

DELETE_TYPES = [
    "Purge Entire Sample",
    "Drop Single Gene",
    "Remove Single Variant"
]

DELETE_KIND = {
    "Purge Entire Sample": "sample",
    "Drop Single Gene": "gene",
    "Remove Single Variant": "variant"
}

MASTER_SQL = """
    SELECT
        s.sample_name,
        s.organism_species,
        g.gene_symbol,
        v.mutation_type,
        v.chromosome_position
    FROM samples s
    JOIN genes g ON g.sample_id = s.sample_id
    JOIN variants v ON v.gene_id = g.gene_id
    ORDER BY
        s.sample_name,
        g.gene_symbol,
        v.chromosome_position
"""

MASTER_COLS = [
    "Sample Name",
    "Species",
    "Gene Symbol",
    "Mutation Type",
    "Chromosome Position"
]


def validate_input(sample, species, gene, seqlen_txt, pos_txt):
    """Validate the insert form.

    Returns (error, values). error is None when everything is fine, otherwise
    a (title, message) pair. values = (species, seq_len, position).
    """

    if not sample or not gene or not pos_txt:
        return (
            ("Missing Input",
             "Sample Name, Gene Symbol and Chromosome Position cannot be blank."),
            None
        )

    try:
        position = int(pos_txt)
    except ValueError:
        return (
            ("Invalid Position",
             "Chromosome Position must be a whole number (e.g. 43044295)."),
            None
        )

    if position < 0:
        return (
            ("Invalid Position", "Chromosome Position cannot be negative."),
            None
        )

    if position > MAX_INT:
        return (
            ("Invalid Position", "Chromosome Position is too large."),
            None
        )

    seq_len = 0

    if seqlen_txt:

        try:
            seq_len = int(seqlen_txt)
        except ValueError:
            return (
                ("Invalid Length", "Sequence Length must be a whole number."),
                None
            )

        if seq_len < 0:
            return (
                ("Invalid Length", "Sequence Length cannot be negative."),
                None
            )

        if seq_len > MAX_INT:
            return (
                ("Invalid Length", "Sequence Length is too large."),
                None
            )

    if not species:
        species = "Unknown"

    return None, (species, seq_len, position)


def get_delete_targets(kind_text):
    """Return an ordered list of (label, record_id) for the delete dropdown."""

    targets = []

    if kind_text == "Purge Entire Sample":

        _, rows = query("""
            SELECT sample_id, sample_name
            FROM samples
            ORDER BY sample_name
        """)

        for sid, name in rows:
            targets.append((f"Sample {sid}: {name}", sid))

    elif kind_text == "Drop Single Gene":

        _, rows = query("""
            SELECT
                g.gene_id,
                s.sample_name,
                g.gene_symbol
            FROM genes g
            JOIN samples s ON s.sample_id = g.sample_id
            ORDER BY g.gene_id
        """)

        for gid, sname, sym in rows:
            targets.append((f"Gene {gid}: {sym} ({sname})", gid))

    else:

        _, rows = query("""
            SELECT
                v.variant_id,
                g.gene_symbol,
                v.mutation_type,
                v.chromosome_position
            FROM variants v
            JOIN genes g ON g.gene_id = v.gene_id
            ORDER BY v.variant_id
        """)

        for vid, sym, mt, pos in rows:
            targets.append((f"Variant {vid}: {sym} {mt} @ {pos}", vid))

    return targets


def pretty_cols(cols):
    return [c.replace("_", " ").title() for c in cols]


# GUI (tkinter window)

class GenomicApp:

    DELETE_TYPES = DELETE_TYPES

    def __init__(self, root):

        self.root = root

        root.title("Genomic Data Pipeline Dashboard")
        root.geometry("1100x620")

        self.v_sample = tk.StringVar()
        self.v_species = tk.StringVar()
        self.v_gene = tk.StringVar()
        self.v_seqlen = tk.StringVar()
        self.v_mut = tk.StringVar(value=MUTATION_TYPES[0])
        self.v_pos = tk.StringVar()

        self.v_del_type = tk.StringVar(
            value=self.DELETE_TYPES[0]
        )

        self.v_del_target = tk.StringVar()

        self.delete_map = {}

        self.build_ui()
        self.refresh_all()

    # LAYOUT

    def build_ui(self):

        left = ttk.Frame(self.root, padding=10)
        left.pack(side="left", fill="y")

        right = ttk.Frame(self.root, padding=10)
        right.pack(side="right", fill="both", expand=True)

        # INSERT PANEL

        ins = ttk.LabelFrame(
            left,
            text="Pipeline Insert Panel",
            padding=10
        )

        ins.pack(fill="x", pady=(0, 12))

        fields = [
            ("Sample Name *", self.v_sample),
            ("Species (new sample)", self.v_species),
            ("Gene Symbol * (e.g. BRCA1)", self.v_gene),
            ("Sequence Length bp (optional)", self.v_seqlen)
        ]

        r = 0

        for label, var in fields:

            ttk.Label(
                ins,
                text=label
            ).grid(row=r, column=0, sticky="w", pady=3)

            ttk.Entry(
                ins,
                textvariable=var,
                width=26
            ).grid(row=r, column=1, pady=3)

            r += 1

        ttk.Label(
            ins,
            text="Mutation Type"
        ).grid(row=r, column=0, sticky="w", pady=3)

        ttk.Combobox(
            ins,
            textvariable=self.v_mut,
            values=MUTATION_TYPES,
            state="readonly",
            width=23
        ).grid(row=r, column=1, pady=3)

        r += 1

        ttk.Label(
            ins,
            text="Chromosome Position *"
        ).grid(row=r, column=0, sticky="w", pady=3)

        ttk.Entry(
            ins,
            textvariable=self.v_pos,
            width=26
        ).grid(row=r, column=1, pady=3)

        r += 1

        ttk.Button(
            ins,
            text="Add Record",
            command=self.on_add
        ).grid(
            row=r,
            column=0,
            columnspan=2,
            pady=(8, 0),
            sticky="ew"
        )

        # DELETE PANEL

        dele = ttk.LabelFrame(
            left,
            text="Pipeline Delete Panel",
            padding=10
        )

        dele.pack(fill="x")

        ttk.Label(
            dele,
            text="Delete type"
        ).grid(row=0, column=0, sticky="w", pady=3)

        self.cb_type = ttk.Combobox(
            dele,
            textvariable=self.v_del_type,
            values=self.DELETE_TYPES,
            state="readonly",
            width=23
        )

        self.cb_type.grid(row=0, column=1, pady=3)

        self.cb_type.bind(
            "<<ComboboxSelected>>",
            lambda e: self.reload_delete_targets()
        )

        ttk.Label(
            dele,
            text="Record"
        ).grid(row=1, column=0, sticky="w", pady=3)

        self.cb_target = ttk.Combobox(
            dele,
            textvariable=self.v_del_target,
            state="readonly",
            width=23
        )

        self.cb_target.grid(row=1, column=1, pady=3)

        ttk.Button(
            dele,
            text="Delete Selected",
            command=self.on_delete
        ).grid(
            row=2,
            column=0,
            columnspan=2,
            pady=(8, 0),
            sticky="ew"
        )

        # TABS

        self.nb = ttk.Notebook(right)
        self.nb.pack(fill="both", expand=True)

        self.trees = {}

        tab_names = [
            ("master", "Master Genomic Registry"),
            ("samples", "Samples"),
            ("genes", "Genes"),
            ("variants", "Variants")
        ]

        for key, title in tab_names:

            frame = ttk.Frame(self.nb)
            self.nb.add(frame, text=title)

            tree = ttk.Treeview(
                frame,
                show="headings"
            )

            vsb = ttk.Scrollbar(
                frame,
                orient="vertical",
                command=tree.yview
            )

            hsb = ttk.Scrollbar(
                frame,
                orient="horizontal",
                command=tree.xview
            )

            tree.configure(
                yscrollcommand=vsb.set,
                xscrollcommand=hsb.set
            )

            tree.grid(row=0, column=0, sticky="nsew")
            vsb.grid(row=0, column=1, sticky="ns")
            hsb.grid(row=1, column=0, sticky="ew")

            frame.rowconfigure(0, weight=1)
            frame.columnconfigure(0, weight=1)

            self.trees[key] = tree

    # HELPERS

    def fill_tree(self, tree, cols, rows):

        tree.delete(*tree.get_children())

        tree["columns"] = cols

        for c in cols:

            tree.heading(
                c,
                text=c.replace("_", " ").title()
            )

            tree.column(
                c,
                width=140,
                anchor="w"
            )

        for row in rows:
            tree.insert("", "end", values=row)

    def refresh_all(self):

        _, rows = query(MASTER_SQL)

        self.fill_tree(self.trees["master"], MASTER_COLS, rows)

        for key, table in [
            ("samples", "samples"),
            ("genes", "genes"),
            ("variants", "variants")
        ]:

            cols, rows = query(f"SELECT * FROM {table}")

            self.fill_tree(self.trees[key], cols, rows)

        self.reload_delete_targets()

    def reload_delete_targets(self):

        targets = get_delete_targets(self.v_del_type.get())

        self.delete_map = {label: rid for label, rid in targets}

        self.cb_target["values"] = [label for label, _ in targets]

        self.v_del_target.set("")

    def clear_inputs(self):

        for var in (
            self.v_sample,
            self.v_species,
            self.v_gene,
            self.v_seqlen,
            self.v_pos
        ):
            var.set("")

        self.v_mut.set(MUTATION_TYPES[0])

    # ACTIONS

    def on_add(self):

        sample = self.v_sample.get().strip()
        species = self.v_species.get().strip()
        gene = self.v_gene.get().strip()
        seqlen_txt = self.v_seqlen.get().strip()
        pos_txt = self.v_pos.get().strip()
        mut = self.v_mut.get().strip()

        error, values = validate_input(
            sample, species, gene, seqlen_txt, pos_txt
        )

        if error:
            messagebox.showerror(error[0], error[1])
            return

        species, seq_len, position = values

        try:

            is_new = add_record(
                sample,
                species,
                gene,
                seq_len,
                mut,
                position
            )

        except sqlite3.Error as e:

            messagebox.showerror("Database Error", str(e))

            return

        msg = (
            "New sample created and record added."
            if is_new
            else "Existing sample found - gene and variant linked to it."
        )

        self.clear_inputs()
        self.refresh_all()

        messagebox.showinfo("Success", msg)

    def on_delete(self):

        label = self.v_del_target.get()

        if not label or label not in self.delete_map:

            messagebox.showerror(
                "Nothing Selected",
                "Please choose a record to delete."
            )

            return

        kind_text = self.v_del_type.get()

        if not messagebox.askyesno(
            "Confirm Delete",
            f"Delete:\n{label}\n\nChild records will also be removed."
        ):
            return

        kind = DELETE_KIND[kind_text]

        try:

            delete_record(kind, self.delete_map[label])

        except sqlite3.Error as e:

            messagebox.showerror("Database Error", str(e))

            return

        self.refresh_all()

        messagebox.showinfo("Deleted", "Record deleted successfully.")


# TEXT-MENU VERSION (Colab / Jupyter / no display / no tkinter)

def print_table(title, cols, rows):

    print()
    print("=" * 70)
    print(title)
    print("=" * 70)

    if not rows:
        print("(no records)")
        return

    table = [[str(c) for c in cols]] + [[str(v) for v in r] for r in rows]

    widths = [max(len(r[i]) for r in table) for i in range(len(cols))]

    def line(r):
        return "  ".join(r[i].ljust(widths[i]) for i in range(len(cols)))

    print(line(table[0]))
    print("  ".join("-" * w for w in widths))

    for r in table[1:]:
        print(line(r))


def show_all_views():
    """Display all four views (like the four tabs)."""

    _, rows = query(MASTER_SQL)
    print_table("TAB 1 - MASTER GENOMIC REGISTRY", MASTER_COLS, rows)

    for title, table in [
        ("TAB 2 - SAMPLES", "samples"),
        ("TAB 3 - GENES", "genes"),
        ("TAB 4 - VARIANTS", "variants")
    ]:
        cols, rows = query(f"SELECT * FROM {table}")
        print_table(title, pretty_cols(cols), rows)


def console_add():

    print("\n--- Pipeline Insert Panel (* = required) ---")

    sample = input("Sample Name *: ").strip()
    species = input("Species (new sample): ").strip()
    gene = input("Gene Symbol * (e.g. BRCA1): ").strip()
    seqlen_txt = input("Sequence Length bp (optional): ").strip()

    print("Mutation Type:")
    for i, m in enumerate(MUTATION_TYPES, 1):
        print(f"  {i}. {m}")

    choice = input("Choose 1-%d [1]: " % len(MUTATION_TYPES)).strip()

    mut = MUTATION_TYPES[0]

    if choice:
        if choice.isdigit() and 1 <= int(choice) <= len(MUTATION_TYPES):
            mut = MUTATION_TYPES[int(choice) - 1]
        else:
            print("ERROR [Invalid Choice]: please choose a number from the list.")
            return

    pos_txt = input("Chromosome Position *: ").strip()

    error, values = validate_input(sample, species, gene, seqlen_txt, pos_txt)

    if error:
        print(f"ERROR [{error[0]}]: {error[1]}")
        return

    species, seq_len, position = values

    try:
        is_new = add_record(sample, species, gene, seq_len, mut, position)
    except sqlite3.Error as e:
        print(f"ERROR [Database Error]: {e}")
        return

    print(
        "SUCCESS: New sample created and record added."
        if is_new
        else "SUCCESS: Existing sample found - gene and variant linked to it."
    )

    show_all_views()


def console_delete():

    print("\n--- Pipeline Delete Panel ---")

    for i, t in enumerate(DELETE_TYPES, 1):
        print(f"  {i}. {t}")

    choice = input("Delete type (1-3, Enter to cancel): ").strip()

    if not choice:
        return

    if not (choice.isdigit() and 1 <= int(choice) <= len(DELETE_TYPES)):
        print("ERROR [Invalid Choice]: please choose 1, 2 or 3.")
        return

    kind_text = DELETE_TYPES[int(choice) - 1]

    targets = get_delete_targets(kind_text)

    if not targets:
        print("Nothing to delete.")
        return

    for i, (label, _) in enumerate(targets, 1):
        print(f"  {i}. {label}")

    pick = input("Record number (Enter to cancel): ").strip()

    if not pick:
        return

    if not (pick.isdigit() and 1 <= int(pick) <= len(targets)):
        print("ERROR [Nothing Selected]: please choose a record to delete.")
        return

    label, record_id = targets[int(pick) - 1]

    sure = input(
        f"Delete {label}? Child records will also be removed. (y/n): "
    ).strip().lower()

    if sure != "y":
        print("Cancelled.")
        return

    try:
        delete_record(DELETE_KIND[kind_text], record_id)
    except sqlite3.Error as e:
        print(f"ERROR [Database Error]: {e}")
        return

    print("SUCCESS: Record deleted successfully.")

    show_all_views()


def run_console():

    print("\nGENOMIC DATA PIPELINE DASHBOARD (text version)")
    print(f"Database file: {DB_FILE}")

    show_all_views()

    menu = """
------------------------------ MENU ------------------------------
 1. Show all four tables (Master Registry, Samples, Genes, Variants)
 2. Add a record      (Pipeline Insert Panel)
 3. Delete a record   (Pipeline Delete Panel)
 0. Exit
------------------------------------------------------------------"""

    while True:

        print(menu)

        try:
            choice = input("Choose an option: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            return

        try:
            if choice == "1":
                show_all_views()
            elif choice == "2":
                console_add()
            elif choice == "3":
                console_delete()
            elif choice == "0":
                print("Goodbye.")
                return
            else:
                print("Please enter 1, 2, 3 or 0.")

        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            return


# MAIN

def main():

    try:
        init_db()

    except (sqlite3.Error, OSError) as e:

        print(f"Database Startup Error - could not initialize:\n{DB_FILE}\n\n{e}")
        return

    use_console = "--console" in sys.argv or not TK_AVAILABLE

    if not use_console:

        # Linux without a display variable cannot open a window.
        if sys.platform.startswith("linux") and not (
            os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")
        ):
            use_console = True

    if not use_console:

        try:
            root = tk.Tk()

        except Exception:
            # No usable display (e.g. Colab, remote server): use text version.
            use_console = True

    if use_console:

        if not TK_AVAILABLE or "--console" not in sys.argv:
            print(
                "Note: no graphical window is available here, so the "
                "text-menu version (same features, same database) is used."
            )

        run_console()
        return

    GenomicApp(root)

    root.mainloop()


if __name__ == "__main__":
    main()
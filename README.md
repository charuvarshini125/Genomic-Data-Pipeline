# Genomic Data Pipeline: Sample Management, Gene Sequencing & Mutation Variant Dashboard

## Project Overview

This project is a Python-based Genomic Data Pipeline Dashboard developed using Python, SQLite and Tkinter.

It provides a simple interface to manage genomic sample information, gene sequencing records and mutation variants.

## Features

- Add new genomic sample records.
- Store organism species information.
- Manage gene symbols and sequence lengths.
- Record mutation types and chromosome positions.
- Delete individual samples, genes and variants.
- View the Master Genomic Registry.
- View separate Samples, Genes and Variants tables.
- Automatically create and initialize the SQLite database.
- Supports a text-based interface when a graphical interface is unavailable.

## Technologies Used

- Python
- SQLite3
- Tkinter
- SQL

## Project Files

| File | Description |
|---|---|
| `genomic_dashboard_final.py` | Main Python application |
| `genomic.db` | SQLite database |
| `README.md` | Project documentation |
| `screenshots/` | Application screenshots |

## How to Run

### Requirements
- Python 3 installed.
- Tkinter available for graphical interface.

### Steps

1. Download or clone this repository.
2. Keep `genomic_dashboard_final.py` and `genomic.db` in the same folder.
3. Open the project folder in VS Code or Terminal.
4. Run:

```bash
python3 genomic_dashboard_final.py
```

On Windows, use:

```bash
python genomic_dashboard_final.py
```

### Console Mode

To run the text-based version:

```bash
python3 genomic_dashboard_final.py --console
```

## Database Structure

The project uses three relational tables:

1. **Samples** – Stores sample names and organism species.
2. **Genes** – Stores gene symbols and sequence lengths.
3. **Variants** – Stores mutation types and chromosome positions.

The tables are connected using primary keys and foreign keys.

## Author

Developed as an academic project in Data Science and Analytics.

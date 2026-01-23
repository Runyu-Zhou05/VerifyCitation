from editdistance import eval as edit_distance

def find_duplicates(bib_entries: list, threshold: int=5):
    '''
    Find duplicate entries in a list of bibliographic entries based on title similarity.
    Two titles with an edit distance less than or equal to the threshold are considered duplicates.
    '''
    n = len(bib_entries)
    duplicates = []
    for i in range(n):
        title_i = bib_entries[i].get('title', '').lower()
        for j in range(i + 1, n):
            title_j = bib_entries[j].get('title', '').lower()
            dist = edit_distance(title_i, title_j)
            if dist <= threshold:
                duplicates.append((i, j, dist))
    return duplicates

import shutil

from rich.table import Table
from rich.console import Console
from rich import box
from io import StringIO

def rich_to_string(renderable, width=100):
    buffer = StringIO()
    console = Console(
        file=buffer,
        force_terminal=True,   # ensures layout/rendering
        width=width,
        color_system=None,     # disables ANSI colors
    )
    console.print(renderable)
    return buffer.getvalue()

def log_duplicates(
    duplicates: list,
    bib_entries: list,
    logger=print,
    min_col_width: int = 10,
    max_col_width: int = None,
    padding: int = 1,
):
    """
    Log duplicates using rich.table.Table.
    """

    try:
        term_width = shutil.get_terminal_size().columns
    except (AttributeError, OSError):
        term_width = 100

    rule_width = min(term_width, 100)

    logger("\n" + "=" * rule_width)
    logger("DUPLICATE DETECTION REPORT")
    logger("=" * rule_width)
    logger(f"Found {len(duplicates)} duplicate pair(s):\n")

    if max_col_width is None:
        max_col_width = int(term_width * 0.4)

    field_width = 10

    available_for_entries = term_width - field_width - (padding * 4) - 4
    entry_col_width = max(
        min_col_width,
        min(max_col_width, available_for_entries // 2),
    )

    for i, (idx1, idx2, dist) in enumerate(duplicates, start=1):
        entry1 = bib_entries[idx1]
        entry2 = bib_entries[idx2]

        table = Table(
            title=f"Duplicate Pair #{i} (Title Edit Distance: {dist})",
            box=box.SQUARE,
            expand=False,
            padding=(0, padding),
            show_lines=True
        )

        table.add_column(
            "Field",
            justify="right",
            width=field_width,
            no_wrap=True,
        )
        table.add_column(
            "Entry 1",
            justify="left",
            width=entry_col_width,
            overflow="fold",
        )
        table.add_column(
            "Entry 2",
            justify="left",
            width=entry_col_width,
            overflow="fold",
        )

        table.add_row(
            "ID",
            r"\cite{" + entry1.get("ID", "[NO_ID]") + "}",
            r"\cite{" + entry2.get("ID", "[NO_ID]") + "}",
        )
        table.add_row(
            "Title",
            entry1.get("title", "N/A"),
            entry2.get("title", "N/A"),
        )
        table.add_row(
            "Authors",
            entry1.get("author", "N/A"),
            entry2.get("author", "N/A"),
        )
        table.add_row(
            "Year",
            entry1.get("year", "N/A"),
            entry2.get("year", "N/A"),
        )
        table.add_row(
            "URL",
            entry1.get("url", "N/A"),
            entry2.get("url", "N/A"),
        )
        
        def get_journal(entry):
            fields = ['journal', 'booktitle', 'series', 'conference', 'publisher']
            for field in fields:
                if field in entry:
                    return field, entry[field]
            return '', ''
        
        f1, j1 = get_journal(entry1)
        f2, j2 = get_journal(entry2)
        if f1 or f2:
            table.add_row(
                "Journal",
                f"{f1}={{{j1}}}" if f1 else "N/A",
                f"{f2}={{{j2}}}" if f2 else "N/A",
            )

        logger(rich_to_string(table, width=term_width))
        logger()

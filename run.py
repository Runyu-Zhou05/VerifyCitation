import argparse

def print_verification_result_table(l: list, logger=print, include_errlv_header=False,
    header="CITATION VERIFICATION REPORT"):
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
    
    try:
        import shutil
        term_width = shutil.get_terminal_size().columns
    except (AttributeError, OSError):
        term_width = 100

    headers = ['ID']
    if include_errlv_header:
        headers.append('Error Level')
    headers.append('Message')

    table = []
    for item in l:
        row = [item[0]]
        if include_errlv_header:
            row.append(item[1])
        row.append(item[2])
        table.append(row)

    max_col_widths = [30]
    if include_errlv_header:
        max_col_widths.append(15)
    max_col_widths.append(max(10, term_width - sum(max_col_widths) - (len(max_col_widths) + 2) * 3))

    tb = Table(
        title=header,
        box=box.SQUARE,
        expand=False,
        padding=(0, 1),
        show_lines=True
    )
    for i, h in enumerate(headers):
        tb.add_column(
            h,
            max_width=max_col_widths[i],
            overflow='fold'
        )
    for row in table:
        tb.add_row(*[cell.strip() for cell in row])

    logger(rich_to_string(tb, width=term_width))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Citation Verifier")
    parser.add_argument(
        "bibfile",
        type=str,
        default='',
        nargs='?',
        help="Path to the .bib file to be verified",
    )
    parser.add_argument('-p', '--hide-progress-bar', action='store_true',
                        help="Hide progress bar during verification")
    parser.add_argument('-g', '--group-by-error-level', action='store_true',
                        help="Group verification results by error level")
    args = parser.parse_args()

    from bibparser import parse_bibfile, parse_bibcontent

    logger = print
    try:
        if args.bibfile:
            entries = parse_bibfile(args.bibfile, logger=logger)
        else:
            import sys

            bibstr = sys.stdin.read()
            entries = parse_bibcontent(bibstr, logger=logger)
    except Exception as e:
        logger(f"Error parsing bib: {e}")
        exit(1)
    entries = entries[:]

    from deduplicator import find_duplicates, log_duplicates

    duplicates = find_duplicates(entries, threshold=5)

    if duplicates:
        try:
            log_duplicates(duplicates, entries, logger=logger)
            flag = input(f'Do you want to proceed? (y/n): ').strip().lower()
            if flag != 'y':
                logger('Quitting...')
                exit(0)
        except KeyboardInterrupt:
            logger("Process interrupted by user.")
            exit(1)
    else:
        logger("Congratulations! No duplicates found in your bib.")

    logger(f'\nStarting citation verification for {len(entries)} entries...\n')

    from verifier import verify_entry

    vresults = []
    import tqdm
    for entry in tqdm.tqdm(entries, disable=args.hide_progress_bar):
        if 'ID' not in entry:
            vresults.append((
                '[NO_ID]', 'error', 'Entry must have an ID field.'
            ))
        else:
            try:
                status, message = verify_entry(entry)
                vresults.append((entry['ID'], status, message))
            except Exception as e:
                vresults.append((
                    entry['ID'], 'attention',
                    f'The verifier encountered an exception:\n{e}'
                ))

    group_by_level = args.group_by_error_level
    groupdict = dict()
    from matching import ERROR_LEVELS
    for lv_id, level in ERROR_LEVELS:
        filtered = [v for v in vresults if v[1] == level]
        groupdict[level] = filtered
        if filtered and group_by_level:
            print_verification_result_table(
                filtered, logger=logger,
                include_errlv_header=False,
                header=f"{level.upper()}"
            )
            logger('\n')
    if not group_by_level:
        print_verification_result_table(
            vresults, logger=logger, include_errlv_header=True
        )
    
    summarystr = '[*] Summary: '
    for level, items in groupdict.items():
        summarystr += f'{level}={len(items)} '
    logger(summarystr.strip())
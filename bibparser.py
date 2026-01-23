import bibtexparser as bibp

def parse_bibfile(bibfile_path, logger=print):
    try:
        with open(bibfile_path, 'r') as bibfile:
            bib_database = bibp.load(bibfile)
    except Exception as e:
        logger(f"Error reading .bib file: {e}")
        return None
    entries = bib_database.entries
    logger(f"Parsed {len(entries)} entries from {bibfile_path}.")
    return entries

def parse_bibcontent(bibstr, logger=print):
    try:
        bib_database = bibp.loads(bibstr)
    except Exception as e:
        logger(f"Error reading .bib file: {e}")
        return None
    entries = bib_database.entries
    logger(f"Parsed {len(entries)} {'entry' if len(entries) == 1 else 'entries'} from stdin.")
    return entries

if __name__ == "__main__":
    parse_bibfile('./test.bib')
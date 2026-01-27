import requests

from typing import Tuple, Union, Any
from bibparser import parse_bibcontent
from bibtexparser.customization import splitname

from matching import ERROR_LEVEL_STR2INT, verify_authors
from getdoi import retry, get_doi
from googlesearch import verify_entry_via_google

@retry
def get_bib_from_doi(doi: str) -> str:
    url = f"https://doi.org/{doi}"
    headers = {"Accept": "application/x-bibtex"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        text = response.text
        entries = parse_bibcontent(text, logger=lambda x: None)
        if len(entries) == 0:
            raise ValueError(f"No BibTeX entries found for DOI {doi}")
        entry, = entries
        return entry
    else:
        raise ValueError(f"Failed to retrieve BibTeX for DOI {doi}: HTTP {response.status_code}")

def parse_authors(author_str: str) -> list:
    authors = [a.strip() for a in author_str.replace('\n', ' ').split(' and ')]
    parsed = [splitname(a) for a in authors]
    return parsed

def get_journal(entry: dict) -> str:
    journal_fields = ['journal', 'booktitle', 'series', 'conference', 'publisher']
    for field in journal_fields:
        if field in entry:
            return entry[field].strip().lower(), entry[field]
    return ''

def abbreviate(name: str) -> str:
    parts = name.strip().split()
    abbr = ''.join(p[0] for p in parts if p)
    return abbr

def remove_functional_words(name: str) -> str:
    functional_words = {'the', 'of', 'and', 'in', 'on', 'for', 'to', 'a', 'an', 'by', 'with'}
    parts = name.strip().lower().split()
    filtered_parts = [p for p in parts if p not in functional_words]
    return ' '.join(filtered_parts)

def compare_journals(entry: dict, doibib: dict) -> Tuple[str, str]:
    entry_journal, entry_journal_original = get_journal(entry)
    doi_journal, doi_journal_original = get_journal(doibib)
    if entry_journal and doi_journal:
        if entry_journal == doi_journal:
            return 'info', ''
        elif 'arxiv' in entry_journal and 'arxiv' in doi_journal:
            return 'info', ''
        elif 'arxiv' in doi_journal and 'arxiv' not in entry_journal:
            return 'info', f'Bib journal/conference is "{entry_journal_original}", ' + \
                f'but DOI publisher is "{doi_journal_original}"; it\'s not sure if this ' + \
                f'mismatch is a problem.'
        else:
            # try abbreviation matching
            entry_journal_nofunc = remove_functional_words(entry_journal)
            doi_journal_nofunc = remove_functional_words(doi_journal)
            entry_abbr = abbreviate(entry_journal_nofunc)
            doi_abbr = abbreviate(doi_journal_nofunc)
            entry_abbr_after_on = abbreviate(entry_journal_nofunc.partition(' on ')[-1])
            doi_abbr_after_on = abbreviate(doi_journal_nofunc.partition(' on ')[-1])
            if entry_abbr == doi_journal or entry_journal == doi_abbr:
                return 'info', ''
            elif entry_abbr_after_on == doi_journal or entry_journal == doi_abbr_after_on:
                return 'info', ''
            else:
                return 'error', f'Journal/conference mismatch: ' + \
                    f'bib "{entry_journal_original}" vs. DOI "{doi_journal_original}".'
    else:
        if doi_journal and not entry_journal:
            return 'info', 'No journal/conference info found in the entry.'
        if entry_journal and not doi_journal:
            return 'info', 'Cannot retrieve journal/conference info from DOI.'
        else:
            return 'info', ''

def compare_entries(entry: dict, doibib: dict) -> Tuple[str, str]:
    title = entry.get('title', '')
    if not title:
        return 'error', f'No title found in ' + \
            f'{"the entry" if "ID" not in entry else "entry " + entry["ID"]}.'

    errlv = 'info'
    msg = ''
    title_mismatch = False

    # first, compare titles
    if 'title' in doibib:
        from editdistance import eval as edit_distance
        threshold = 5
        title_doi = doibib['title']
        title_entry = title
        dist = edit_distance(title_doi.strip().lower(), title_entry.strip().lower())
        if dist > threshold:
            title_mismatch = True
            msg += f'Title mismatch (edit distance {dist} > {threshold=}):\n' + \
                f'Bib title: "{title_entry}";\nDOI title: "{title_doi}".\n'
            if ERROR_LEVEL_STR2INT[errlv] < ERROR_LEVEL_STR2INT['error']:
                errlv = 'error'

    if title_mismatch: # We suspect the entry's title doesn't exist; so stop further checks
        return errlv, msg
    
    # second, compare links
    url = entry.get('url', '').strip().rstrip('/')
    if url and 'url' in doibib:
        link = doibib['url'].strip().rstrip('/')
        if url != link:
            msg += f'URL mismatch:\nBibtex\'s URL:\t"{url}"\nDOI\'s link:\t"{link}"\n'
            if ERROR_LEVEL_STR2INT[errlv] < ERROR_LEVEL_STR2INT['warning']:
                errlv = 'warning'

    # third, compare authors
    entry_authors = entry.get('author', '').strip()
    doi_authors = doibib.get('author', '').strip()
    if doi_authors:
        ok, author_msg = verify_authors(entry_authors, doi_authors)
        if not ok:
            msg += f'Author verification failed:\n{author_msg}\n'
            if ERROR_LEVEL_STR2INT[errlv] < ERROR_LEVEL_STR2INT['error']:
                errlv = 'error'

    # fourth, compare year
    entry_year = entry.get('year', '').strip()
    doi_year = doibib.get('year', '').strip()
    if entry_year and doi_year and entry_year != doi_year:
        msg += f'Year mismatch: bib year "{entry_year}" vs. DOI year "{doi_year}".\n'
        if abs(int(entry_year) - int(doi_year)) != 1 and \
            ERROR_LEVEL_STR2INT[errlv] < ERROR_LEVEL_STR2INT['warning']:
            errlv = 'warning'

    # fifth, compare journal/conference
    journal_errlv, journal_msg = compare_journals(entry, doibib)
    if ERROR_LEVEL_STR2INT[journal_errlv] > ERROR_LEVEL_STR2INT[errlv]:
        errlv = journal_errlv
    if journal_msg:
        msg += journal_msg + '\n'

    if errlv == 'info' and not msg:
        msg = 'OK'

    return errlv, msg

def verify_entry(entry: dict) -> Tuple[str, str]:
    assert 'ID' in entry, 'Entry must have an ID field.'
    ok, doi = get_doi(entry)
    if ok:
        doibib = get_bib_from_doi(doi)
        if doibib is None:
            return 'attention', f'Failed to retrieve BibTeX from DOI {doi}.'
        return compare_entries(entry, doibib)
    else:
        return verify_entry_via_google(entry)

if __name__ == "__main__":
    from pprint import pprint
    sample_doi = '10.48550/arXiv.2505.23941'
    bib = get_bib_from_doi(sample_doi)
    pprint(bib)
    pprint(parse_authors(bib['author']))

    sample_bib = '''@article{liu2025rpt,
  title={RPT: Reinforced Pre-Training of Large Language Models},
  author={Liu, Xiaodong and others},
  journal={arXiv:2505.07185},
  year={2025},
  url={https://arxiv.org/abs/2505.07185}
}'''
    entry, = parse_bibcontent(sample_bib)
    status, message = verify_entry(entry)
    print(f"Verification result for entry ID {entry['ID']}:")
    print(f"Status: {status}")
    print(f"Message: {message}")
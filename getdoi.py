from typing import Tuple, Union, Any

def retry(func, max_retries=3, delay=0.2):
    import time
    from functools import wraps

    @wraps(func)
    def wrapper(*args, **kwargs) -> Union[Any, None]:
        attempts = 0
        while attempts < max_retries:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                attempts += 1
                if attempts == max_retries:
                    raise
                time.sleep(delay)
        return None

    return wrapper

def get_arxiv_doi(entry: dict) -> Union[None, str]:
    arxiv_colon = 'arXiv:'
    if arxiv_colon in entry.get('journal', ''):
        arxiv_id = entry['journal'].rpartition(arxiv_colon)[-1].strip()
        return f'10.48550/arXiv.{arxiv_id}'
    elif 'arxiv.org' in entry.get('url', ''):
        url = entry['url']
        arxiv_id = url.rstrip('/').rpartition('/')[-1]
        return f'10.48550/arXiv.{arxiv_id}'

def get_acl_doi(entry: dict) -> Union[None, str]:
    if 'aclanthology.org' in entry.get('url', ''):
        url = entry['url']
        filename = url.rstrip('/').rpartition('/')[-1]
        acl_id = '.'.join(filename.split('.')[:3])
        doi = f'10.18653/v1/{acl_id}'
        return doi

def get_doi(entry: dict) -> Tuple[bool, str]:
    doi = entry.get('doi', '').strip()
    if doi: return True, doi
    arxiv_doi = get_arxiv_doi(entry)
    if arxiv_doi: return True, arxiv_doi
    acl_doi = get_acl_doi(entry)
    if acl_doi: return True, acl_doi
    return False, 'All methods to get DOI failed.'

if __name__ == "__main__":
    bib = './test.bib'
    from bibparser import parse_bibfile
    entries = parse_bibfile(bib)
    num_ok = 0
    for entry in entries:
        ok, doi = get_doi(entry)
        if ok:
            print(f"Entry ID: {entry.get('ID', '[NO_ID]')}, DOI: {doi}")
            num_ok += 1
    print(f"Total entries with DOIs found: {num_ok} out of {len(entries)}.")
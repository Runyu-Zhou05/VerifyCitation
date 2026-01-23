from typing import Union, Tuple, Any
from matching import ERROR_LEVEL_STR2INT, verify_authors_google

def google_search(param) -> Tuple[bool, Any]:
    import time, urllib3
    from serpapi import GoogleSearch
    attempts = 0
    max_attempts = 5
    while attempts < max_attempts:
        try:
            return True, GoogleSearch(param)
        except (urllib3.exceptions.ProtocolError, ConnectionResetError) as e:
            attempts += 1
            time.sleep(10)
        except Exception as e:
            attempts += 1
            time.sleep(5)
    return False, f'Google search failed after {max_attempts} attempts.'

def get_year_from_summary(summary: str) -> str:
    # summary is like: 'Y You, T Chen, Y Sui, T Chen... - 
    # Advances in neural ..., 2020 - proceedings.neurips.cc'
    sep = ' - '
    if sep not in summary:
        return ''
    left = summary.rpartition(sep)[0]
    comma = ', '
    if comma not in left:
        return ''
    year = left.rpartition(comma)[-1].strip()
    if len(year) == 4 and year.isdigit():
        return year
    return ''

serp_api_key = ''

def search_info_via_google(title: str) -> Tuple[bool, Union[dict, str]]:
    global serp_api_key
    if serp_api_key == '':
        serp_api_key = input("Please enter your SerpAPI key: ").strip()
    params = {
        "engine": "google_scholar",
        "q": title,
        "api_key": serp_api_key
    }
    try:
        flag, search = google_search(params)
    except Exception as e:
        return False, f'Exception during Google search: {e}'
    if not flag:
        return False, search
    orgres_field = 'organic_results'
    results = search.get_dict()
    if orgres_field not in results:
        return False, f'Search result has no {orgres_field} field.'
    info = results[orgres_field]
    if len(info) == 0:
        return False, 'No results found.'
    info = info[0]
    pubinfo_field = 'publication_info'
    pub = info.get(pubinfo_field, None)
    if pub is None:
        return False, f'No {pubinfo_field} found in the top result.'
    summary = pub.get('summary', '')
    year = get_year_from_summary(summary)
    authors_names = [x['name'] for x in pub.get('authors', [])]
    final = {
        'title': info.get('title', ''),
        'authors': authors_names,
        'link': info.get('link', ''),
    }
    if year:
        final['year'] = year
    return True, final

def verify_entry_via_google(entry: dict) -> Tuple[str, str]:
    title = entry.get('title', '')
    if not title:
        return 'error', f'No title found in the entry {entry["ID"]}.'
    flag, info = search_info_via_google(title)
    if not flag:
        return 'attention', f'Google search failed: {info}'
    
    errlv = 'info'
    msg = ''
    title_mismatch = False

    # first, compare titles
    if 'title' in info:
        from editdistance import eval as edit_distance
        threshold = 5
        title_google = info['title']
        title_entry = title
        dist = edit_distance(title_google.strip().lower(), title_entry.strip().lower())
        if dist > threshold:
            title_mismatch = True
            msg += f'Title mismatch (edit distance {dist} > {threshold=}):\n' + \
                f'Bib title:\t"{title_entry}";\nGoogle title:\t"{title_google}".\n'
            if ERROR_LEVEL_STR2INT[errlv] < ERROR_LEVEL_STR2INT['warning']:
                errlv = 'warning'

    if title_mismatch: # We suspect the entry's title doesn't exist; so stop further checks
        return errlv, msg

    # second, compare links
    url = entry.get('url', '').strip().rstrip('/')
    if url and 'link' in info:
        link = info['link'].strip().rstrip('/')
        if url != link:
            msg += f'URL mismatch:\nBibtex\'s URL:\t"{url}"\nGoogle\'s link:\t"{link}"\n'
            if ERROR_LEVEL_STR2INT[errlv] < ERROR_LEVEL_STR2INT['warning']:
                errlv = 'warning'

    # third, compare authors
    entry_authors = entry.get('author', '').strip()
    google_authors = info.get('authors', [])
    if google_authors:
        ok, author_msg = verify_authors_google(entry_authors, google_authors)
        if not ok:
            msg += f'Author verification failed:\n{author_msg}\n'
            if ERROR_LEVEL_STR2INT[errlv] < ERROR_LEVEL_STR2INT['error']:
                errlv = 'error'
    else:
        msg += 'No authors found in Google search result.\n'

    # fourth, compare year
    entry_year = entry.get('year', '').strip()
    google_year = info.get('year', '').strip()
    if entry_year and google_year and entry_year != google_year:
        msg += f'Year mismatch: bib year "{entry_year}" vs. Google year "{google_year}".\n'
        if abs(int(entry_year) - int(google_year)) != 1 and \
            ERROR_LEVEL_STR2INT[errlv] < ERROR_LEVEL_STR2INT['warning']:
            errlv = 'warning'

    if errlv == 'info' and not msg:
        msg = 'OK'

    return errlv, msg

if __name__ == "__main__":
    from bibparser import parse_bibcontent
    bib = '''@inproceedings{you2020graphcl,
  title={Graph Contrastive Learning with Augmentations},
  author={You, Yonglong and Chen, Tianlong and Sui, Zhangyang and Wang, Yang},
  booktitle={NeurIPS},
  year={2020},
  url={https://proceedings.neurips.cc/paper/2020/file/3fe230348e9a12c13120749e3f9fa4cd-Paper.pdf}
}'''
    entries = parse_bibcontent(bib)
    entry = entries[0]
    errlv, msg = verify_entry_via_google(entry)
    print(f'Verification level: {errlv}\nMessage:\n{msg}')
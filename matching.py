from typing import Tuple, Union

ERROR_LEVELS = [
    (4, 'error'),
    (3, 'warning'),
    (2, 'attention'),
    (1, 'info'),
]

ERROR_LEVEL_STR2INT = {level_str: level_int for level_int, level_str in ERROR_LEVELS}
ERROR_LEVEL_INT2STR = {level_int: level_str for level_int, level_str in ERROR_LEVELS}

def split_authors(s: str) -> list:
    from bibtexparser.customization import splitname
    authors = [a.strip() for a in s.split(' and ')]
    parsed = []
    for a in authors:
        if a != 'others':
            a = a.strip(',')
            splitted = splitname(a)
            if len(splitted['first']) == 0 and len(splitted['von']) == 0 and len(splitted['jr']) == 0 and \
                len(splitted['last']) == 1:
                splitted['last'][0] = splitted['last'][0].strip('{}')
            parsed.append(splitted)
    return parsed

def join_author(author: dict) -> str:
    parts = []
    if 'first' in author and author['first']:
        parts.extend(author['first'])
    if 'last' in author and author['last']:
        parts.extend(author['last'])
    return ' '.join(parts)

import unicodedata

def accent_to_latex(char):
    # Map of Unicode combining marks to LaTeX accent commands
    accent_map = {
        '\u0301': "\\'",  # Acute (иж)
        '\u0300': "\\`",  # Grave (ии)
        '\u0302': "\\^",  # Circumflex (и║)
        '\u0308': '\\"',  # Umlaut/Diaeresis (?)
        '\u0303': "\\~",  # Tilde (?)
        '\u0304': "\\=",  # Macron (иб)
        '\u0307': "\\.",  # Dot (?)
        '\u0327': "\\c",  # Cedilla (?)
    }

    # Normalize character to "Decomposed" form (NFD)
    # e.g., 'иж' becomes ['e', 'combining acute']
    normalized = unicodedata.normalize('NFD', char)
    
    base_char = normalized[0]
    
    # Check if there is a combining mark attached
    if len(normalized) > 1:
        accent_mark = normalized[1]
        latex_accent = accent_map.get(accent_mark)
        
        if latex_accent:
            # Result format: {\'e}
            return f"{{{latex_accent}{base_char}}}"
            
    return char

def normalize_name(name: str) -> str:
    return ''.join(accent_to_latex(c) for c in name)

def normalize_entries(alist: list) -> list:
    r = []
    for a in alist:
        r.append({
            k: [normalize_name(s) for s in v] if isinstance(v, list)
            else normalize_name(v)
            for k, v in a.items()
        })
    return r

def compare_name_list(n1: list, n2: list) -> bool:
    # first, check if one of them is composed of only initials
    init1 = ''.join(x[0] for x in n1 if x).upper()
    init2 = ''.join(x[0] for x in n2 if x).upper()
    if (len(n2) == 1 and init1 == n2[0].upper()) or \
        (len(n1) == 1 and init2 == n1[0].upper()):
        return True

    # second, compare each part
    minlen = min(len(n1), len(n2))
    for i in range(minlen):
        if n1[i] != n2[i]:
            # try: like "J." vs "John"
            s1 = n1[i].strip().rstrip('.')
            s2 = n2[i].strip().rstrip('.')
            if len(s1) == 1 and s2.startswith(s1):
                continue
            if len(s2) == 1 and s1.startswith(s2):
                continue
            # try: like "Li-Jia" vs "LJ"
            s1_upper = ''.join(c for c in s1 if c.isupper())
            s2_upper = ''.join(c for c in s2 if c.isupper())
            if s1_upper == s2.upper() or s2_upper == s1.upper():
                continue
            return False
    return True

def report_mismatch(index, position, component1, component2) -> str:
    c1 = ' '.join(component1).strip()
    c2 = ' '.join(component2).strip()
    s = (
        f"Author No. {index}: {position} mismatch: "
        f"'{c1}' vs '{c2}'.\n"
    )
    return s

def verify_authors(authors1: Union[str, list], authors2: Union[str, list]) -> Tuple[bool, str]:
    '''
    Verify a1 with a2 as the golden standard.
    '''
    if isinstance(authors1, str):
        a1 = split_authors(authors1)
    else:
        a1 = authors1
    if isinstance(authors2, str):
        a2 = split_authors(authors2)
    else:
        a2 = authors2

    a1 = normalize_entries(a1)
    a2 = normalize_entries(a2)

    ok = True
    msg = ''

    if len(a1) == 0:
        ok = False
        msg += 'No authors provided!\n'

    min_len = min(len(a1), len(a2))
    for i in range(min_len):
        name1 = a1[i]
        name2 = a2[i]
        if join_author(name1) == join_author(name2):
            continue # exact match
        if not compare_name_list(name1.get('last', []), name2.get('last', [])):
            ok = False
            msg += report_mismatch(i + 1, 'last name', name1['last'], name2['last'])
        if 'first' in name1 and 'first' in name2:
            if not compare_name_list(name1['first'], name2['first']):
                ok = False
                msg += report_mismatch(i + 1, 'first name', name1['first'], name2['first'])

    return ok, msg.strip()

def verify_authors_google(entry_authors: Union[str, list], google_authors: list) -> Tuple[bool, str]:
    '''
    Verify authors from the entry with those from Google as the golden standard.
    It seems that Google authors are always in 'X Lastname' format.
    '''
    g = []
    for a in google_authors:
        parts = a.strip().split()
        first = parts[:-1]
        last = parts[-1:]
        g.append({
            'first': first,
            'last': last,
            'von': [],
            'jr': [],
        })
    
    return verify_authors(entry_authors, g)
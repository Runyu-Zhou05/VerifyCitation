<!-- # Citation Verifier

Verify the validity of each citation given a `.bib` file.

## Installation

```sh
conda create -n citevrf python=3.11 -y
source .../conda/bin/activate citevrf # activate the conda environment
pip install bibtexparser==1.4.3 requests==2.32.5 editdistance==0.8.1 google-search-results==2.4.2 rich==14.2.0
```

## Usage

First, make sure that the currect working directory is `VerifyCitation`.

```sh
cd VerifyCitation
```

`test.bib` provides an example of a `.bib` file to be checked.

To run the verifier:

```sh
python run.py test.bib
```

Replace test.bib with your bib file. Or, if you want to directly paste the bib content, you can run

```sh
python run.py
```

Paste your bib content, and press Ctrl + D to quit the input mode.

The verifier first tries to detect duplicate bib entries by determining if the edit distant between
any pair of titles is less than or equal to a specific threshold (default to 5 in `deduplicator.py`,
you can adjust it by tweaking `find_duplicates`'s `threshold` argument), and then search over DOI and 
Google Scholar by the titles and see if other info is correct.

Please note that, in case when Google Scholar is needed, you are asked to type the SerpAPI.
You may also directly set `serp_api_key` in `googlesearch.py`.

The result is reported as a table or multiple tables.
When called with argument `-g`, the reports are grouped by error levels (errors, warnings, etc.);
otherwise, the validity of each entry is reported.

There are four error levels: `error`, `warning`, `attention` and `info`.
An entry with an `error` tag indicates that you may need to search for this entry again.

In an empirical aspect of view, if it reports that the conference in the provided bib is not arXiv, 
but DOI returns arXiv as the publisher, then you may ignore this error message. -->

# Citation Verifier

A tool to validate and verify citation entries from `.bib` files by checking against DOI databases and Google Scholar.

## Installation

1. Create and activate a Conda environment:
   ```sh
   conda create -n citevrf python=3.11 -y
   conda activate citevrf
   ```

2. Install required packages:
   ```sh
   pip install bibtexparser==1.4.3 requests==2.32.5 editdistance==0.8.1 google-search-results==2.4.2 rich==14.2.0 tqdm
   ```

## Usage

Navigate to the project directory:
```sh
cd VerifyCitation
```

### Basic Verification

To verify a `.bib` file:
```sh
python run.py input.bib
```
Replace `input.bib` with your BibTeX file.

### Direct Input Mode

You can also paste BibTeX content directly:
```sh
python run.py
```
Paste your BibTeX entries, then press `Ctrl + D` (or `Cmd + D` on macOS) to finish.

### Output Grouping

By default, results are shown per entry. To group by error level:
```sh
python run.py input.bib -g
```

## How It Works

1. **Duplicate Detection**  
   The tool identifies potential duplicates by computing edit distances between titles.  
   Default threshold: 5 (adjustable in `deduplicator.py` via the `threshold` parameter in `find_duplicates`).

2. **Citation Validation**  
   Each entry is verified by searching:
   - Retrieving ground-truth bibtex from `doi.org`
   - Searching on `Google Scholar` if unable to get DOI

3. **API Configuration**  
   When Google Scholar verification is required, you will be prompted for a SerpAPI key.  
   Alternatively, set it directly in `googlesearch.py` as `serp_api_key`.

## Error Levels

Results are categorized into four levels:

| Level | Description |
|-------|-------------|
| **error** | Critical issues; consider re-searching the entry |
| **warning** | Significant discrepancies that may require inspection |
| **attention** | Minor inconsistencies to review; or the script failed to retrieve certain information |
| **info** | Informational notes for reference |

## Notes

- **arXiv entries**: If a DOI search returns arXiv as the publisher but your `.bib` entry specifies a conference, this may be flagged as an error. In practice, such cases can often be ignored, as arXiv versions of conference papers are common.

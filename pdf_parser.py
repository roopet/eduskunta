# pdf_parser.py
import fitz # PyMuPDF
import pymupdf # PyMuPDF
import requests
import os
import re
from config import PDF_FOLDER, DESC_START_HEADING # EFFECTIVE_DATE_PHRASE and DATE_REGEX likely removed/replaced

def get_pdf_text_from_url(pdf_url, max_pages=None):
    """Lataa PDF URL-osoitteesta ja poimii tekstin määritellyiltä sivuilta."""
    if not pdf_url or not pdf_url.startswith('http'):
        print(f"Virheellinen tai puuttuva PDF URL: {pdf_url}")
        return None # Palauta None virheen merkiksi

    print(f"DEBUG PDF: Ladataan ja yritetään lukea PDF URL: {pdf_url[:80]}...")
    try:
        # Lataa PDF-sisältö muistiin requests-kirjastolla
        response = requests.get(pdf_url, timeout=60) # Lisää timeout
        response.raise_for_status() # Tarkista HTTP-virheet (4xx, 5xx)
        pdf_bytes = response.content # PDF-data byteinä

        # Avaa PDF suoraan byteistä PyMuPDF:llä
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        full_text = ""
        # Määritä luettavien sivujen määrä
        pages_to_read = len(doc)
        if max_pages is not None and max_pages > 0:
            pages_to_read = min(len(doc), max_pages)

        # Lue teksti sivuilta
        for page_num in range(pages_to_read):
            page = doc[page_num]
            full_text += page.get_text("text") + "\n--- PAGE BREAK ---\n"
        doc.close()

        print(f"DEBUG PDF: Tekstin poiminta URL:sta onnistui ({len(full_text)} merkkiä).")
        return full_text if full_text else "" # Palauta tyhjä, jos PDF oli tyhjä

    except requests.exceptions.RequestException as e:
        print(f"Virhe ladattaessa PDF URL:sta {pdf_url}: {e}")
        return None
    except fitz.fitz.FileDataError as e: # PyMuPDF:n virhe, jos data ei ole validi PDF
         print(f"Virhe avattaessa PDF-dataa URL:sta {pdf_url} (ei validi PDF?): {e}")
         return None
    except Exception as e:
        # Muu odottamaton virhe PyMuPDF:ssä tai muualla
        print(f"Virhe käsiteltäessä PDF URL:sta {pdf_url}: {e}")
        import traceback
        traceback.print_exc() # Tulosta koko traceback terminaaliin
        return None

# --- download_pdf function remains the same ---
def download_pdf(pdf_url, he_tunnus):
    if not pdf_url:
        print(f"No PDF URL for {he_tunnus}")
        return None
    safe_filename = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in he_tunnus) + ".pdf"
    filepath = os.path.join(PDF_FOLDER, safe_filename)
    if os.path.exists(filepath):
        # print(f"PDF already exists locally: {filepath}") # Optional: reduce verbosity
        return filepath
    try:
        response = requests.get(pdf_url, stream=True, timeout=60)
        response.raise_for_status()
        os.makedirs(PDF_FOLDER, exist_ok=True)
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        # print(f"Downloaded PDF to: {filepath}") # Optional: reduce verbosity
        return filepath
    except requests.exceptions.RequestException as e:
        print(f"Error downloading {pdf_url} for {he_tunnus}: {e}")
        return None
    except OSError as e:
        print(f"Error saving PDF {filepath}: {e}")
        return None


# Renamed and modified to read first few pages
def extract_text_first_pages(pdf_path, num_pages=5):
    """Extracts text from the first few pages of a PDF."""
    if not pdf_path or not os.path.exists(pdf_path):
        print(f"PDF path not valid: {pdf_path}")
        return ""
    full_text = ""
    try:
        doc = fitz.open(pdf_path)
        doc = pymupdf.open(pdf_path)
        # Read text from specified number of pages, or fewer if doc is shorter
        pages_to_read = min(len(doc), num_pages)
        for page_num in range(pages_to_read):
            page = doc[page_num]
            full_text += page.get_text("text") + "\n--- PAGE BREAK ---\n" # Add separator
        doc.close()
        return full_text
    except Exception as e:
        print(f"Error reading PDF {pdf_path}: {e}")
        return ""

# Modified description finder
def find_short_description(text):
    """Finds text after DESC_START_HEADING and tries to determine its end."""
    if not text:
        return None

    start_match = re.search(DESC_START_HEADING, text, re.IGNORECASE)
    if not start_match:
        # print("Could not find description start heading.")
        return None

    start_index = start_match.end()
    text_after_heading = text[start_index:]

    # Define potential end markers (regex patterns)
    end_markers = [
        r"^\s*1\.\s+Laki",                       # Start of law section "1. Laki"
        r"^\s*Laki\s*\n",                       # "Laki" on its own line
        r"^\s*1\s+[Ll]uku",                     # Start of chapter "1 Luku" / "1 luku"
        r"^\s*1\s*§",                           # Start of section "1 §"
        r"Ehdotetut? l[ae]i[dt]? ovat tarkoitus tulla voimaan", # Effective date phrase (start)
        r"Tämän lain voimaantulosta\s*säädetään", # New effective date phrase
        r"Laki tulee voimaan"                    # Another effective date phrase start
        # Add more specific markers if needed
    ]

    earliest_end_index = len(text_after_heading) # Default to end of text

    for pattern in end_markers:
        end_match = re.search(pattern, text_after_heading, re.IGNORECASE | re.MULTILINE)
        if end_match and end_match.start() < earliest_end_index:
            earliest_end_index = end_match.start()

    # Extract text up to the earliest end marker
    description = text_after_heading[:earliest_end_index].strip()

    # Clean up whitespace and limit length
    description = re.sub(r'\s+', ' ', description).strip()
    # Limit length reasonably, e.g., 1500 chars, adjust as needed
    max_len = 1500
    if len(description) > max_len:
         # Try to cut at a sentence end near the limit
         last_period = description.rfind('.', 0, max_len)
         if last_period != -1:
              description = description[:last_period + 1]
         else:
              description = description[:max_len] + "..." # Indicate truncation

    # print(f"Extracted description length: {len(description)}")
    return description if description else None

# Modified effective date finder
def find_effective_date_text(text):
    """Finds different patterns indicating effective date information."""
    if not text:
        return None

    # List of patterns to search for, ordered roughly by specificity
    # Capturing groups help extract the relevant part.
    patterns = [
        # Pattern capturing a specific date (adjust DATE_REGEX if needed)
        r"((?:Ehdotetut? l[ae]i[dt]? ovat tarkoitus tulla voimaan|Laki on tarkoitettu tulemaan voimaan)\s*.*?(\d{1,2}\.\s*\d{1,2}\.\s*\d{4}).*)",
        # Pattern for the new example
        r"(Tämän lain voimaantulosta\s*säädetään\s*(?:valtioneuvoston)?\s*asetuksella)",
        # Pattern for "säädettävänä ajankohtana"
        r"((?:Laki|Tämä laki) tulee voimaan(?:\s*myöhemmin)?\s*säädettävänä\s*ajankohtana)",
         # Generic "Laki tulee voimaan" followed by something (like a date word month year?) - less reliable
        r"((?:Laki|Tämä laki) tulee voimaan\s+\d{1,2}\.\s*päivänä\s*\w+kuuta\s*\d{4})"
        # Add more patterns here if other common phrasings are found
    ]

    # Search within the latter part of the text, assuming date is usually after description
    search_area = text # Or maybe text[len(text)//2:] to speed up if needed

    for pattern in patterns:
        match = re.search(pattern, search_area, re.IGNORECASE | re.MULTILINE)
        if match:
            # Return the most relevant captured group (usually the first one covering the phrase)
            # Clean whitespace from the result
            result_text = match.group(1).strip()
            result_text = re.sub(r'\s+', ' ', result_text)
            # print(f"Found effective date text: {result_text}")
            return result_text # Return the first successful match

    # print("Could not find effective date information.")
    return None
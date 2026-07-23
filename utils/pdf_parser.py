import io
from PyPDF2 import PdfReader

def extract_text_from_pdf(pdf_file) -> str:
    """
    Extracts all text from a PDF file.
    pdf_file can be a file path (str), bytes, or a file-like object.
    """
    if isinstance(pdf_file, bytes):
        reader = PdfReader(io.BytesIO(pdf_file))
    else:
        # File path string or file-like object (e.g. Streamlit UploadedFile)
        reader = PdfReader(pdf_file)
        
    text = ""
    for page in reader.pages:
        extracted = page.extract_text()
        if extracted:
            text += extracted + "\n"
    return text

def parse_pdf_sections(text: str) -> dict:
    """
    Parses LinkedIn PDF profile text into sections.
    Standard sections: Summary, Experience, Education, Skills, Honors.
    """
    sections = {
        "Summary": "",
        "Experience": "",
        "Education": "",
        "Skills": "",
        "Honors": ""
    }
    
    # Define mapping of sections to potential heading keywords in the PDF.
    headers_map = [
        ("Summary", ["Summary", "About", "Profile"]),
        ("Experience", ["Experience", "Work Experience", "Professional Experience"]),
        ("Education", ["Education", "Academic Background"]),
        ("Skills", ["Skills", "Skills & Endorsements", "Languages"]),
        ("Honors", ["Honors & Awards", "Honors", "Awards", "Patents", "Certifications"])
    ]
    
    lines = text.splitlines()
    matches = []
    
    for i, line in enumerate(lines):
        clean_line = line.strip()
        # Header is usually short and matches one of the keywords
        if not clean_line or len(clean_line) > 30:
            continue
            
        for sec_key, keywords in headers_map:
            matched = False
            for kw in keywords:
                if clean_line.lower() == kw.lower():
                    matched = True
                    break
            if matched:
                matches.append((i, sec_key, clean_line))
                break
                
    # Sort matches by line index
    matches.sort(key=lambda x: x[0])
    
    # If no matches are found, return the whole text under "Summary"
    if not matches:
        sections["Summary"] = text.strip()
        return sections
        
    # Slice the lines according to matched sections
    for idx, (line_idx, sec_key, _) in enumerate(matches):
        start_line = line_idx + 1
        end_line = matches[idx+1][0] if idx + 1 < len(matches) else len(lines)
        section_text = "\n".join(lines[start_line:end_line]).strip()
        
        if sections[sec_key]:
            sections[sec_key] += "\n\n" + section_text
        else:
            sections[sec_key] = section_text
            
    # Assign text before first heading to Summary
    first_match_idx = matches[0][0]
    if first_match_idx > 0:
        prefix_text = "\n".join(lines[:first_match_idx]).strip()
        if prefix_text:
            if sections["Summary"]:
                sections["Summary"] = prefix_text + "\n\n" + sections["Summary"]
            else:
                sections["Summary"] = prefix_text

    return sections

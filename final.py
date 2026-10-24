import json
import time
import urllib.request
import urllib.error
from fpdf import FPDF

def clean_text(text):
    """
    Replaces common unsupported Unicode characters (like smart quotes and en-dashes)
    with their standard ASCII equivalents to prevent fpdf encoding crashes.
    """
    if text is None:
        return ""
        
    text = str(text)
    replacements = {
        '\u2013': '-',   # en-dash
        '\u2014': '--',  # em-dash
        '\u2018': "'",   # smart single quote left
        '\u2019': "'",   # smart single quote right
        '\u201c': '"',   # smart double quote left
        '\u201d': '"',   # smart double quote right
        '\u2022': '-',   # bullet point
        '\u2026': '...', # ellipsis
        '\u00a0': ' ',   # non-breaking space
        '\u200b': ''     # zero-width space
    }
    
    for search, replace in replacements.items():
        text = text.replace(search, replace)
        
    # Finally, safely force it into latin-1. Any other completely weird emojis 
    # or symbols will be silently ignored rather than crashing the script.
    return text.encode('latin-1', 'ignore').decode('latin-1')


def create_resume_pdf(data, output_filename):
    """Generates a formatted PDF resume from a parsed JSON dictionary using fpdf2."""
    
    details = data.get("details", {})
    iith_degrees = data.get("degreesAtIITH", [])
    cv_sections = data.get("cv", [])
    
    # Extract CGPA and Year safely
    iith_cgpa = clean_text(iith_degrees[0].get("CGPA", "N/A") if iith_degrees else "N/A")
    iith_grad_year = clean_text(iith_degrees[0].get("Passing_Year", "N/A") if iith_degrees else "N/A")
    
    # Format Phone Number safely
    phone = clean_text(details.get("contact") or "")
    if phone and phone.startswith("91") and len(phone) > 10:
        phone = f"+91 {phone[2:]}"
        
    # Format Links safely (handle None/null values)
    linkedin = clean_text(details.get("linkedin") or "")
    linkedin_url = linkedin if linkedin.startswith("http") else (f"https://{linkedin}" if linkedin else "")
    
    github = clean_text(details.get("github") or "")
    github_url = github if github.startswith("http") else (f"https://{github}" if github else "")

    # Initialize PDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    
    # --- HEADER SECTION ---
    student_name = clean_text(details.get('student_name') or 'Unknown Candidate')
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(0, 10, student_name, align="C", new_x="LMARGIN", new_y="NEXT")
    
    # Dynamic Contact Details
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(100, 100, 100)
    
    contact_parts = []
    email = clean_text(details.get('email'))
    email_other = clean_text(details.get('email_other'))
    
    if email:
        contact_parts.append(f'<a href="mailto:{email}">{email}</a>')
    if email_other:
        contact_parts.append(f'<a href="mailto:{email_other}">{email_other}</a>')
    if phone:
        contact_parts.append(phone)
    if linkedin_url:
        contact_parts.append(f'<a href="{linkedin_url}">LinkedIn</a>')
    if github_url:
        contact_parts.append(f'<a href="{github_url}">GitHub</a>')
        
    contact_html = f"""
    <div align="center">
        {" | ".join(contact_parts)}
    </div>
    """
    pdf.write_html(contact_html)
    pdf.ln(5)

    # --- EDUCATION SECTION ---
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(0, 8, "EDUCATION", border="B", align="L", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    
    # Safely handle missing education data
    sch_xii = clean_text(details.get('School_XII') or 'N/A')
    brd_xii = clean_text(details.get('Board_XII') or 'N/A')
    yr_xii = clean_text(details.get('Passing_Year_XII') or 'N/A')
    mk_xii = clean_text(details.get('Marks_XII') or 'N/A')
    
    sch_x = clean_text(details.get('School_X') or 'N/A')
    brd_x = clean_text(details.get('Board_X') or 'N/A')
    yr_x = clean_text(details.get('Passing_Year_X') or 'N/A')
    mk_x = clean_text(details.get('Marks_X') or 'N/A')

    # Use HTML tables for neat education alignment
    education_html = f"""
    <table width="100%" border="0">
        <thead>
            <tr>
                <th width="45%" align="left"><b>Institution</b></th>
                <th width="25%" align="left"><b>Degree / Board</b></th>
                <th width="15%" align="left"><b>Passing Year</b></th>
                <th width="15%" align="left"><b>Score / CGPA</b></th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>Indian Institute of Technology Hyderabad</td>
                <td>B.Tech</td>
                <td>{iith_grad_year}</td>
                <td>{iith_cgpa}</td>
            </tr>
            <tr>
                <td>{sch_xii}</td>
                <td>Class XII ({brd_xii})</td>
                <td>{yr_xii}</td>
                <td>{mk_xii}%</td>
            </tr>
            <tr>
                <td>{sch_x}</td>
                <td>Class X ({brd_x})</td>
                <td>{yr_x}</td>
                <td>{mk_x}%</td>
            </tr>
        </tbody>
    </table>
    """
    pdf.write_html(education_html)
    pdf.ln(5)

    # --- DYNAMIC SECTIONS (Skills, Projects, Courses, etc.) ---
    for section in cv_sections:
        section_title = clean_text(section.get('info', 'Section').upper())
        
        # Section Header
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(44, 62, 80)
        pdf.cell(0, 8, section_title, border="B", align="L", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)
        
        # Section Body
        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(51, 51, 51)
        
        for field in section.get('fields', []):
            field_content = field.get('info', '')
            
            if field_content:
                # 1. Strip the JSON's empty paragraph tags
                field_content = field_content.replace("<p><br></p>", "")
                # 2. Sanitize the string to prevent FPDF crashes
                field_content = clean_text(field_content)
                
                # 3. Write HTML to PDF
                pdf.write_html(field_content)
                pdf.ln(2)

    # Output the PDF
    pdf.output(output_filename)


def run_resume_downloader(start_id, end_id):
    api_url_template = "https://ocs.iith.ac.in/portal/api/api/student/publiccv/{id_number}"
    # Session identifier string extracted from active browser storage
    session_cookie = "s%3AEcr2rZztdfLNXU4u3ZW91NkSXQeZ4C1I.BUqUc703JX7WkuEJCK7Sk2TuPyG%2FGDD4qs%2FjT08OyOM"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Cookie': session_cookie,
        'Accept': 'application/json, */*'
    }

    print(f"Beginning PDF Generation sequence for IDs {start_id} through {end_id}...")

    for i in range(start_id, end_id + 1):
        target_url = api_url_template.format(id_number=i)
        print(f"\nFetching Profile Data for ID {i}: {target_url}")
        
        try:
            req = urllib.request.Request(target_url, headers=headers)
            with urllib.request.urlopen(req) as response:
                content_type = response.info().get_content_type()
                
                if "application/json" in content_type:
                    raw_data = response.read().decode('utf-8')
                    json_data = json.loads(raw_data)
                    
                    if json_data.get("success") and "details" in json_data:
                        details = json_data["details"]
                        student_name = clean_text(details.get("student_name") or f"Student_{i}")
                        
                        # Generate clean local filename
                        clean_name = "".join([c for c in student_name if c.isalnum() or c in (' ', '_')]).replace(' ', '_')
                        pdf_filename = f"Resume_{i}_{clean_name}.pdf"
                        
                        # Pass the entire parsed JSON dictionary to the PDF generator
                        create_resume_pdf(json_data, pdf_filename)
                        print(f"-> SUCCESS: Formatted and generated structured PDF: '{pdf_filename}'")
                    else:
                        print(f"-> SKIPPED: ID {i} API response did not contain successful student profile records.")
                else:
                    print(f"-> SKIPPED: ID {i} Received unexpected file configuration format '{content_type}'.")
                        
        except urllib.error.HTTPError as e:
            print(f"-> SKIPPED: API Error {e.code}: Target index row {i} returned an error status.")
        except urllib.error.URLError as e:
            print(f"-> SKIPPED: Network error encountered on ID {i}: {e.reason}")
        except Exception as e:
            # THIS IS THE CATCH-ALL FOR ANY OTHER CRASHES (JSON, PDF Generation, Unicode, etc.)
            print(f"-> SKIPPED: Unexpected error processing ID {i}. Reason: {e}")
            
        # 2 second pause to be polite to the server, regardless of success or failure
        time.sleep(2.0)

# Run for your desired range
if __name__ == "__main__":
    run_resume_downloader(start_id=2401, end_id=3000) 
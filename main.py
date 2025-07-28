import sys
import re
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from ebooklib import epub
import smtplib
import os
from email.message import EmailMessage
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

# Try to import playwright for better transcript fetching
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

# Try to import pytube for fetching video title
try:
    from pytube import YouTube
except ImportError:
    YouTube = None

def extract_video_id(url):
    """Extract the video ID from a YouTube URL."""
    regex = r"(?:v=|youtu\.be/|embed/|v/|shorts/)([\w-]{11})"
    match = re.search(regex, url)
    if match:
        return match.group(1)
    else:
        return None

def fetch_video_title(url):
    title = input("Enter a title for the book: ").strip()
    if not title:
        title = "YouTube Transcript"
    return title

def sanitize_filename(name):
    # Remove or replace characters not allowed in filenames
    return re.sub(r'[\\/*?\:"<>|]', '', name)

def fetch_transcript_with_playwright(video_id):
    """Fetch transcript using Playwright to bypass IP blocks."""
    if not PLAYWRIGHT_AVAILABLE:
        raise Exception("Playwright not available. Please install it with: pip install playwright")
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Navigate to YouTube video
            url = f"https://www.youtube.com/watch?v={video_id}"
            page.goto(url)
            
            # Wait for page to load
            page.wait_for_load_state("networkidle")
            
            # Try to find and click the "Show transcript" button
            try:
                # Look for transcript button
                transcript_button = page.locator('button[aria-label*="transcript"], button[aria-label*="Transcript"]')
                if transcript_button.count() > 0:
                    transcript_button.first.click()
                    page.wait_for_timeout(2000)  # Wait for transcript to load
                
                # Extract transcript text
                transcript_elements = page.locator('[data-testid="transcript-segment"]')
                if transcript_elements.count() == 0:
                    # Try alternative selectors
                    transcript_elements = page.locator('.ytd-transcript-segment-renderer')
                
                if transcript_elements.count() == 0:
                    raise Exception("No transcript found on page")
                
                transcript = []
                for i in range(transcript_elements.count()):
                    element = transcript_elements.nth(i)
                    text = element.text_content()
                    if text:
                        # Parse timestamp and text
                        parts = text.split('\n')
                        if len(parts) >= 2:
                            timestamp = parts[0]
                            content = ' '.join(parts[1:])
                            # Convert timestamp to seconds
                            time_parts = timestamp.split(':')
                            if len(time_parts) == 2:
                                seconds = int(time_parts[0]) * 60 + int(time_parts[1])
                            elif len(time_parts) == 3:
                                seconds = int(time_parts[0]) * 3600 + int(time_parts[1]) * 60 + int(time_parts[2])
                            else:
                                seconds = 0
                            
                            transcript.append({
                                'start': seconds,
                                'text': content
                            })
                
                browser.close()
                return transcript
            except Exception as e:
                browser.close()
                raise Exception(f"Failed to extract transcript: {e}")
                
    except Exception as e:
        raise Exception(f"Playwright error: {e}")

def fetch_transcript(video_id):
    """Try API first, then fallback to Playwright if needed."""
    try:
        # Try the regular API first
        transcript = YouTubeTranscriptApi().fetch(video_id)
        return transcript
    except Exception as api_error:
        # If API fails, try Playwright as fallback
        if PLAYWRIGHT_AVAILABLE:
            try:
                return fetch_transcript_with_playwright(video_id)
            except Exception as playwright_error:
                # If both fail, raise the original API error
                raise Exception(f"API failed: {api_error}. Playwright failed: {playwright_error}")
        else:
            # If Playwright not available, just raise the API error
            if "Transcripts are disabled" in str(api_error):
                raise Exception("Transcripts are disabled for this video.")
            elif "No transcript found" in str(api_error):
                raise Exception("No transcript found for this video.")
            else:
                raise Exception(f"Error fetching transcript: {api_error}")

def format_timestamp(seconds):
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{mins:02d}:{secs:02d}"

def group_transcript_by_interval(transcript, interval_seconds=1200):
    """Group transcript entries into sections of interval_seconds (default 20 min)."""
    sections = []
    current_section = []
    current_start = 0
    for entry in transcript:
        if entry.start >= current_start + interval_seconds and current_section:
            sections.append((current_start, current_start + interval_seconds, current_section))
            current_start += interval_seconds
            current_section = []
        current_section.append(entry)
    if current_section:
        # Add the last section
        sections.append((current_start, current_start + interval_seconds, current_section))
    return sections

def create_title_page(title, video_id):
    html = f"""
    <html><head></head><body>
    <h1 style='text-align:center;margin-top:2em;font-size:2.5em;'>{title}</h1>
    <h3 style='text-align:center;margin-top:1em;'>YouTube Transcript</h3>
    <p style='text-align:center;margin-top:2em;'>Video ID: {video_id}</p>
    </body></html>
    """
    title_page = epub.EpubHtml(title='Title Page', file_name='title.xhtml', lang='en')
    title_page.content = html
    return title_page

def transcript_sections_to_epub_chapters(sections):
    chapters = []
    for idx, (start, end, entries) in enumerate(sections, 1):
        section_title = f"Section {idx}: {format_timestamp(start)}–{format_timestamp(end)}"
        html = f"<h2>{section_title}</h2>\n"
        # Group transcript into paragraphs of ~5 lines for readability
        paragraph = []
        for i, entry in enumerate(entries):
            paragraph.append(entry.text.replace('\n', ' '))
            if len(paragraph) >= 5 or i == len(entries) - 1:
                html += f"<p class='block'>{' '.join(paragraph)}</p>\n"
                paragraph = []
        chapter = epub.EpubHtml(title=section_title, file_name=f'section_{idx:02d}.xhtml', lang='en')
        chapter.content = html
        chapters.append((section_title, chapter))
    return chapters

def create_custom_css():
    css = '''
    body { font-family: serif; font-size: 1.2em; line-height: 1.7; margin: 2em; }
    h1, h2 { text-align: center; }
    p.block { margin-bottom: 1.2em; }
    '''
    style = epub.EpubItem(uid="style_nav", file_name="style/nav.css", media_type="text/css", content=css)
    return style

def save_epub(title, video_id, chapters, output_filename):
    book = epub.EpubBook()
    book.set_identifier(title)
    book.set_title(title)
    book.set_language('en')
    book.add_author('YouTube Transcript Script')

    # Add custom CSS
    style = create_custom_css()
    book.add_item(style)

    # Add title page
    title_page = create_title_page(title, video_id)
    book.add_item(title_page)

    # Add chapters and build TOC
    toc = [epub.Link('title.xhtml', 'Title Page', 'title_page')]
    spine = ['nav', title_page]
    for section_title, chapter in chapters:
        chapter.add_item(style)
        book.add_item(chapter)
        toc.append(epub.Link(chapter.file_name, section_title, section_title.replace(' ', '_')))
        spine.append(chapter)
    book.toc = tuple(toc)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = spine
    epub.write_epub(output_filename, book)
    print(f"Saved transcript as {output_filename}")

def generate_pdf(title, sections, output_filename):
    """Generate a PDF file from transcript sections."""
    doc = SimpleDocTemplate(output_filename, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=1  # Center alignment
    )
    story.append(Paragraph(title, title_style))
    story.append(Spacer(1, 20))
    
    # Add subtitle
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=12,
        spaceAfter=20,
        alignment=1
    )
    story.append(Paragraph("YouTube Transcript", subtitle_style))
    story.append(Spacer(1, 30))
    
    # Content
    for idx, (start, end, entries) in enumerate(sections, 1):
        # Section header
        section_title = f"Section {idx}: {format_timestamp(start)}–{format_timestamp(end)}"
        story.append(Paragraph(section_title, styles['Heading2']))
        story.append(Spacer(1, 12))
        
        # Combine all text in the section
        section_text = ""
        for entry in entries:
            section_text += entry.text.replace('\n', ' ') + " "
        
        # Add text as paragraph
        story.append(Paragraph(section_text, styles['Normal']))
        story.append(Spacer(1, 20))
    
    doc.build(story)
    print(f"Saved PDF as {output_filename}")

def send_file_via_email(file_path, user_email, book_title, sender_email, sender_app_password):
    """Send the generated file to user's email."""
    if not (user_email and sender_email and sender_app_password):
        print("Missing email credentials for file delivery.")
        return False
    
    msg = EmailMessage()
    msg['Subject'] = f"Your YouTube Transcript: {book_title}"
    msg['From'] = sender_email
    msg['To'] = user_email
    msg.set_content(f'''
    Hi there!
    
    Here's your YouTube transcript as requested: "{book_title}"
    
    The file is attached to this email.
    
    Enjoy reading!
    ''')
    
    # Determine file type and MIME type
    file_extension = os.path.splitext(file_path)[1].lower()
    if file_extension == '.epub':
        maintype = 'application'
        subtype = 'epub+zip'
    elif file_extension == '.pdf':
        maintype = 'application'
        subtype = 'pdf'
    else:
        maintype = 'application'
        subtype = 'octet-stream'
    
    try:
        with open(file_path, 'rb') as f:
            file_data = f.read()
            file_name = os.path.basename(file_path)
        msg.add_attachment(file_data, maintype=maintype, subtype=subtype, filename=file_name)
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(sender_email, sender_app_password)
            smtp.send_message(msg)
        print(f"Sent {file_name} to {user_email}")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

def send_to_kindle(epub_path, book_title, kindle_email=None, sender_email=None, sender_app_password=None):
    # Use provided parameters or fall back to environment variables
    kindle_email = kindle_email or os.environ.get('KINDLE_EMAIL')
    sender_email = sender_email or os.environ.get('SENDER_EMAIL')
    sender_app_password = sender_app_password or os.environ.get('SENDER_APP_PASSWORD')
    
    if not (kindle_email and sender_email and sender_app_password):
        print("Missing email credentials for Kindle sending.")
        return False
    
    msg = EmailMessage()
    msg['Subject'] = book_title
    msg['From'] = sender_email
    msg['To'] = kindle_email
    msg.set_content('Convert')  # 'Convert' in the body will convert to Kindle format if possible
    
    with open(epub_path, 'rb') as f:
        file_data = f.read()
        file_name = os.path.basename(epub_path)
    msg.add_attachment(file_data, maintype='application', subtype='epub+zip', filename=file_name)
    
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(sender_email, sender_app_password)
            smtp.send_message(msg)
        print(f"Sent {file_name} to Kindle email: {kindle_email}")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

def main():
    if len(sys.argv) != 2:
        print("Usage: python main.py <YouTube URL>")
        sys.exit(1)
    url = sys.argv[1]
    video_id = extract_video_id(url)
    if not video_id:
        print("Invalid YouTube URL.")
        sys.exit(1)
    video_title = fetch_video_title(url)
    safe_title = sanitize_filename(video_title)
    transcript = fetch_transcript(video_id)
    sections = group_transcript_by_interval(transcript, interval_seconds=1200)  # 20 min
    chapters = transcript_sections_to_epub_chapters(sections)
    output_filename = f"{safe_title}.epub"
    save_epub(video_title, video_id, chapters, output_filename)
    send_to_kindle(output_filename, video_title)

if __name__ == "__main__":
    try:
        main()
    except ImportError as e:
        print("Missing dependencies. Please install them with:")
        print("  pip install youtube-transcript-api ebooklib pytube")
        sys.exit(1)

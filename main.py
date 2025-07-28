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
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

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
                # Look for transcript button with multiple selectors
                transcript_button_selectors = [
                    'button[aria-label*="transcript"]',
                    'button[aria-label*="Transcript"]',
                    'button[aria-label*="字幕"]',
                    'button[aria-label*="字幕"]',
                    '[data-testid="transcript-button"]',
                    'button:has-text("Show transcript")',
                    'button:has-text("字幕")'
                ]
                
                transcript_button = None
                for selector in transcript_button_selectors:
                    try:
                        button = page.locator(selector)
                        if button.count() > 0:
                            transcript_button = button.first
                            break
                    except:
                        continue
                
                if transcript_button:
                    transcript_button.click()
                    page.wait_for_timeout(3000)  # Wait for transcript to load
                
                # Extract transcript text with multiple selectors
                transcript_selectors = [
                    '[data-testid="transcript-segment"]',
                    '.ytd-transcript-segment-renderer',
                    '.ytd-transcript-segment',
                    '[data-testid="transcript-text"]'
                ]
                
                transcript_elements = None
                for selector in transcript_selectors:
                    try:
                        elements = page.locator(selector)
                        if elements.count() > 0:
                            transcript_elements = elements
                            break
                    except:
                        continue
                
                if not transcript_elements or transcript_elements.count() == 0:
                    # Try to find any text that looks like a transcript
                    page_text = page.text_content('body')
                    if 'transcript' in page_text.lower() or '字幕' in page_text:
                        raise Exception("Transcript button found but transcript content not accessible")
                    else:
                        raise Exception("No transcript found on page")
                
                transcript = []
                for i in range(transcript_elements.count()):
                    element = transcript_elements.nth(i)
                    text = element.text_content()
                    if text and text.strip():
                        # Parse timestamp and text
                        parts = text.split('\n')
                        if len(parts) >= 2:
                            timestamp = parts[0].strip()
                            content = ' '.join(parts[1:]).strip()
                            
                            # Skip if no content
                            if not content:
                                continue
                                
                            # Convert timestamp to seconds
                            try:
                                time_parts = timestamp.split(':')
                                if len(time_parts) == 2:
                                    seconds = int(time_parts[0]) * 60 + int(time_parts[1])
                                elif len(time_parts) == 3:
                                    seconds = int(time_parts[0]) * 3600 + int(time_parts[1]) * 60 + int(time_parts[2])
                                else:
                                    seconds = 0
                            except:
                                seconds = 0
                            
                            transcript.append({
                                'start': seconds,
                                'text': content
                            })
                
                browser.close()
                if not transcript:
                    raise Exception("No transcript content could be extracted")
                return transcript
            except Exception as e:
                browser.close()
                raise Exception(f"Failed to extract transcript: {e}")
                
    except Exception as e:
        raise Exception(f"Playwright error: {e}")

def fetch_transcript(video_id):
    """Try API first, then fallback to Playwright if needed. Preserves original language."""
    try:
        # Try the regular API first with multiple language attempts
        try:
            transcript = YouTubeTranscriptApi().fetch(video_id)
            return transcript
        except Exception as lang_error:
            # Try with different languages if English fails
            try:
                transcript = YouTubeTranscriptApi().fetch(video_id, languages=['zh-TW', 'zh-CN', 'ja', 'ko'])
                return transcript
            except:
                # If language-specific fails, try auto-detection
                try:
                    transcript = YouTubeTranscriptApi().fetch(video_id, languages=['auto'])
                    return transcript
                except:
                    raise lang_error
    except Exception as api_error:
        # If API fails, try Playwright as fallback
        if PLAYWRIGHT_AVAILABLE:
            try:
                transcript = fetch_transcript_with_playwright(video_id)
                return transcript
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

def group_transcript_by_interval(transcript, interval_seconds=2400):
    """Group transcript entries into sections of interval_seconds (default 40 min - double the size)."""
    sections = []
    current_section = []
    current_start = 0
    for entry in transcript:
        if entry.start >= current_start + interval_seconds and current_section:
            # Try to end at a complete sentence
            current_section = end_section_at_sentence(current_section)
            sections.append((current_start, current_start + interval_seconds, current_section))
            current_start += interval_seconds
            current_section = []
        current_section.append(entry)
    if current_section:
        # Add the last section
        current_section = end_section_at_sentence(current_section)
        sections.append((current_start, current_start + interval_seconds, current_section))
    return sections

def end_section_at_sentence(entries):
    """Try to end the section at a complete sentence."""
    if not entries:
        return entries
    
    # Look for sentence endings in the last few entries
    for i in range(len(entries) - 1, max(0, len(entries) - 5), -1):
        text = entries[i].text.strip()
        if text.endswith('.') or text.endswith('!') or text.endswith('?'):
            return entries[:i+1]
    
    # If no sentence ending found, return all entries
    return entries

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
    """Generate a PDF file from transcript sections with Chinese font support."""
    doc = SimpleDocTemplate(output_filename, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Use UnicodeCIDFont which supports Chinese characters
    try:
        # Register Unicode font that supports Chinese
        pdfmetrics.registerFont(UnicodeCIDFont('STSong-Light'))
        chinese_font = 'STSong-Light'
    except:
        try:
            # Try alternative Chinese fonts
            pdfmetrics.registerFont(UnicodeCIDFont('HeiseiMin-W3'))
            chinese_font = 'HeiseiMin-W3'
        except:
            try:
                # Try system fonts as fallback
                pdfmetrics.registerFont(TTFont('ArialUnicode', '/System/Library/Fonts/Arial Unicode MS.ttf'))
                chinese_font = 'ArialUnicode'
            except:
                try:
                    pdfmetrics.registerFont(TTFont('PingFang', '/System/Library/Fonts/PingFang.ttc'))
                    chinese_font = 'PingFang'
                except:
                    chinese_font = 'Helvetica'
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=25,
        spaceBefore=20,
        alignment=1,  # Center alignment
        fontName=chinese_font
    )
    story.append(Paragraph(title, title_style))
    story.append(Spacer(1, 15))
    
    # Add subtitle
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=13,
        spaceAfter=30,
        alignment=1,
        fontName=chinese_font
    )
    story.append(Paragraph("YouTube Transcript", subtitle_style))
    story.append(Spacer(1, 35))
    
    # Content
    for idx, (start, end, entries) in enumerate(sections, 1):
        # Section header
        section_title = f"Section {idx}: {format_timestamp(start)}–{format_timestamp(end)}"
        header_style = ParagraphStyle(
            'SectionHeader',
            parent=styles['Heading2'],
            fontName=chinese_font,
            fontSize=16,
            spaceAfter=20,
            spaceBefore=30
        )
        story.append(Paragraph(section_title, header_style))
        
        # Group transcript into paragraphs of ~5 lines for shorter paragraphs
        paragraph = []
        for i, entry in enumerate(entries):
            paragraph.append(entry.text.replace('\n', ' '))
            if len(paragraph) >= 5 or i == len(entries) - 1:
                # Create paragraph text
                paragraph_text = " ".join(paragraph)
                
                # Add paragraph with better formatting
                text_style = ParagraphStyle(
                    'NormalText',
                    parent=styles['Normal'],
                    fontName=chinese_font,
                    fontSize=13,
                    leading=18,
                    spaceAfter=12,
                    firstLineIndent=0,  # No indent first line
                    leftIndent=0,
                    rightIndent=0
                )
                story.append(Paragraph(paragraph_text, text_style))
                story.append(Spacer(1, 8))  # Space between paragraphs
                paragraph = []
        
        story.append(Spacer(1, 25))  # Extra space after each section
    
    doc.build(story)
    print(f"Saved PDF as {output_filename} using font: {chinese_font}")

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

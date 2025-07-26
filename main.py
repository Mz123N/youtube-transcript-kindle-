import sys
import re
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound
from ebooklib import epub
import smtplib
import os
from email.message import EmailMessage

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

def fetch_transcript(video_id):
    try:
        transcript = YouTubeTranscriptApi().fetch(video_id)
        return transcript
    except TranscriptsDisabled:
        print("Transcripts are disabled for this video.")
        sys.exit(1)
    except NoTranscriptFound:
        print("No transcript found for this video.")
        sys.exit(1)
    except Exception as e:
        print(f"Error fetching transcript: {e}")
        sys.exit(1)

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

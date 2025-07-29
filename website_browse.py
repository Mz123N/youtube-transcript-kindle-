import os
import streamlit as st
from dotenv import load_dotenv
import subprocess
import sys
import json
import random

# Load environment variables from .env file
load_dotenv()

# Install Playwright browsers if not already installed
@st.cache_resource
def install_playwright_browsers():
    try:
        # First check if playwright is available
        result = subprocess.run(['playwright', '--version'], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            return False
            
        # Install chromium browser
        result = subprocess.run(['playwright', 'install', 'chromium'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            return True
        else:
            return False
    except Exception as e:
        return False

# Install browsers on app startup
playwright_available = install_playwright_browsers()
from main import (
    extract_video_id,
    sanitize_filename,
    fetch_transcript,
    group_transcript_by_interval,
    transcript_sections_to_epub_chapters,
    save_epub,
    send_to_kindle,
    generate_pdf,
    send_file_via_email
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        color: #1f77b4;
        margin-bottom: 1rem;
        padding: 1rem;
        background: linear-gradient(90deg, #f0f8ff 0%, #e6f3ff 100%);
        border-radius: 10px;
        border-left: 5px solid #1f77b4;
    }
    .feature-box {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #28a745;
        margin: 0.5rem 0;
    }
    .input-section {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 1rem 0;
    }
    .success-box {
        background: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
    .info-box {
        background: #d1ecf1;
        border: 1px solid #bee5eb;
        border-radius: 8px;
        padding: 1rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Demo GIF section
st.markdown("""
<style>
    .demo-container {
        text-align: center;
        margin: 2rem 0;
        padding: 1rem;
        background: #f8f9fa;
        border-radius: 15px;
        border: 2px solid #e9ecef;
    }
    .demo-gif {
        max-width: 100%;
        border-radius: 10px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .demo-title {
        font-size: 1.2rem;
        font-weight: bold;
        color: #495057;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)



# Demo video section
st.markdown("""
<style>
    .demo-video-container {
        text-align: center;
        margin: 2rem 0;
        padding: 1rem;
        background: #f8f9fa;
        border-radius: 15px;
        border: 2px solid #e9ecef;
    }
    .demo-video-title {
        font-size: 1.2rem;
        font-weight: bold;
        color: #495057;
        margin-bottom: 1rem;
    }
    .demo-video {
        max-width: 100%;
        border-radius: 10px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)

# Demo video
st.markdown("""
<div class="demo-video-title">🎬 See How It Works</div>
""", unsafe_allow_html=True)

# Embed demo video
st.video("https://www.youtube.com/watch?v=afzBAW9Q64k")

# Main header with icon
st.markdown('<h1 class="main-header">📚 Turn Your Favorite Podcasts into E-Books</h1>', unsafe_allow_html=True)

# Feature highlights
col1, col2 = st.columns(2)
with col1:
    st.markdown('<div class="feature-box"><h4>⚡ Instant Conversion</h4><p>Transform YouTube videos into readable e-books in seconds</p></div>', unsafe_allow_html=True)
with col2:
    st.markdown('<div class="feature-box"><h4>📱 Read Anywhere</h4><p>Access your content on Kindle, phone, or computer</p></div>', unsafe_allow_html=True)

# Inspirational quotes section
st.markdown("""
<style>
    .quote-container {
        background: #f8f9fa;
        border: 2px solid #e9ecef;
        border-radius: 15px;
        margin: 1rem 0;
        padding: 2rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        display: flex;
        align-items: center;
        gap: 2rem;
    }
    .quote-content {
        flex: 1;
        text-align: left;
    }
    .quote-text {
        font-size: 1.3rem;
        font-style: italic;
        margin-bottom: 1rem;
        line-height: 1.6;
        color: #495057;
    }
    .quote-author {
        font-size: 1rem;
        font-weight: bold;
        color: #6c757d;
    }
    .speaker-image {
        width: 80px;
        height: 80px;
        border-radius: 50%;
        object-fit: cover;
        border: 3px solid #dee2e6;
        filter: grayscale(100%);
        opacity: 0.8;
    }
</style>
""", unsafe_allow_html=True)

# Load quotes from JSON file
@st.cache_data
def load_authors():
    try:
        with open('quotes.json', 'r') as f:
            data = json.load(f)
            return data['authors']
    except FileNotFoundError:
        # Fallback authors if JSON file is not found
        return [
            {
                "name": "Naval Ravikant",
                "image_url": "https://images.squarespace-cdn.com/content/v1/58de89eb17bffc754e3c1d33/1552963210906-LVA904K3O50RP633WOVG/Aug+2016+Headshot.jpg",
                "quotes": [
                    "The most important skill for getting rich is becoming a perpetual learner.",
                    "Read what you love until you love to read."
                ]
            }
        ]

# Load authors and select one random quote from each author
authors = load_authors()
selected_quotes = []

for author in authors:
    if author['quotes']:  # Make sure author has quotes
        random_quote = random.choice(author['quotes'])
        selected_quotes.append({
            "text": random_quote,
            "author": author['name'],
            "image_url": author['image_url']
        })

# Display a random quote from the selected quotes
if selected_quotes:
    quote = random.choice(selected_quotes)
else:
    # Fallback if no quotes are available
    quote = {
        "text": "The most important skill for getting rich is becoming a perpetual learner.",
        "author": "Naval Ravikant",
        "image_url": "https://images.squarespace-cdn.com/content/v1/58de89eb17bffc754e3c1d33/1552963210906-LVA904K3O50RP633WOVG/Aug+2016+Headshot.jpg"
    }
st.markdown(f'''
<div class="quote-container">
    <img src="{quote['image_url']}" alt="{quote['author']}" class="speaker-image">
    <div class="quote-content">
        <div class="quote-text">"{quote['text']}"</div>
        <div class="quote-author">— {quote['author']}</div>
    </div>
</div>
''', unsafe_allow_html=True)



# Input section with styling
st.markdown("### 📝 Content Details")
youtube_url = st.text_input("YouTube Link")
book_title = st.text_input("Book Title")
format_choice = st.selectbox("Choose format:", ["EPUB", "PDF"])

# Interval selection
st.markdown("### ⏱️ Section Length")
interval_choice = st.selectbox(
    "How long of the interval you want to classify this conversation?",
    ["5 min", "10 min", "20 min", "30 min"],
    index=2  # Default to 20 min
)

# Set default sender credentials (your email)
sender_email = "mengnan188@gmail.com"  # Your Gmail address
sender_app_password = os.environ.get('SENDER_APP_PASSWORD', 'your_app_password_here')  # Get from environment variable

if st.button("Generate"):
    # Store generation state
    st.session_state.generated = True
    st.session_state.youtube_url = youtube_url
    st.session_state.book_title = book_title
    st.session_state.format_choice = format_choice
    st.session_state.interval_choice = interval_choice
    
    try:
        st.info("Starting process...")

        # 1. Get and process inputs from the form
        video_id = extract_video_id(youtube_url)
        video_title = book_title  # Use the title from the form
        safe_title = sanitize_filename(video_title)
        
        # 2. Generate transcript and sections
        st.write("Step 1: Fetching transcript...")
        transcript = fetch_transcript(video_id)
        st.write(f"Transcript fetched: {len(transcript)} entries")
        
        st.write("Step 2: Grouping into sections...")
        
        # Convert interval choice to seconds
        interval_mapping = {
            "5 min": 300,
            "10 min": 600,
            "20 min": 1200,
            "30 min": 1800
        }
        interval_seconds = interval_mapping[interval_choice]
        
        sections = group_transcript_by_interval(transcript, interval_seconds=interval_seconds)
        st.write(f"Sections created: {len(sections)} with {interval_choice} intervals")
        
        # 3. Generate file based on format choice
        st.write(f"Step 3: Generating {format_choice} file...")
        if format_choice == "EPUB":
            output_filename = f"{safe_title}.epub"
            st.write("Saving EPUB file to:", output_filename)
            chapters = transcript_sections_to_epub_chapters(sections)
            save_epub(video_title, video_id, chapters, output_filename)
        else:  # PDF
            output_filename = f"{safe_title}.pdf"
            st.write("Saving PDF file to:", output_filename)
            generate_pdf(video_title, sections, output_filename)
        
        st.write(f"File generated successfully: {output_filename}")
        
        # Store file info in session state
        st.session_state.output_filename = output_filename
        st.session_state.video_title = video_title

    except Exception as e:
        st.error("An error occurred while generating or saving the book.")
        st.exception(e)

# Show download and send options if file was generated
if st.session_state.get('generated', False):
    output_filename = st.session_state.get('output_filename')
    video_title = st.session_state.get('video_title')
    
    if output_filename and video_title:
        # 4. Step 1: Direct Download
        st.markdown("### 📥 Download Your File")
        
        # Read the generated file for download
        try:
            with open(output_filename, 'rb') as f:
                file_data = f.read()
            
            # Create download button based on format
            format_choice = st.session_state.get('format_choice')
            if format_choice == "EPUB":
                st.download_button(
                    label="📥 Download EPUB",
                    data=file_data,
                    file_name=output_filename,
                    mime="application/epub+zip"
                )
            else:  # PDF
                st.download_button(
                    label="📥 Download PDF",
                    data=file_data,
                    file_name=output_filename,
                    mime="application/pdf"
                )
        except Exception as e:
            st.error(f"Error preparing download: {e}")

        # 5. Step 2: Dynamic Delivery Options
        st.markdown("### 📧 Or send directly to your email or Kindle!")
        
        # Email input
        user_email = st.text_input("Your Email (to receive the file)")
        
        # Kindle delivery option
        send_to_kindle_option = st.checkbox("Send to Kindle directly")
        
        if send_to_kindle_option:
            st.markdown('<div class="info-box">📧 **Kindle Email Address:** This is the email address linked to your Kindle device. You can find your Kindle email address at <a href="https://www.amazon.com/sendtokindle/email" target="_blank">Amazon\'s Send to Kindle page</a>.</div>', unsafe_allow_html=True)
            kindle_email = st.text_input("Kindle Email")
        else:
            kindle_email = None
        
        # Send options
        if user_email:
            if st.button("📧 Send to my email directly"):
                st.write(f"Attempting to send file to email: {user_email}")
                
                if send_file_via_email(output_filename, user_email, video_title, sender_email, sender_app_password):
                    st.success(f"✅ File sent to your email: {user_email}")
                else:
                    st.error("❌ Failed to send file to your email. Please check your email address and try again.")
        
        # Kindle sending option (only for EPUB)
        if format_choice == "EPUB" and send_to_kindle_option and kindle_email:
            if st.button("📚 Send to my Kindle directly"):
                if send_to_kindle(output_filename, video_title, kindle_email, sender_email, sender_app_password):
                    st.success(f"✅ File sent to Kindle: {kindle_email}")
                else:
                    st.error("❌ Failed to send to Kindle. Please check your Kindle email credentials.")
        elif format_choice == "PDF" and send_to_kindle_option:
            st.info("💡 Kindle sending is only available for EPUB files")
        elif send_to_kindle_option and not kindle_email:
            st.info("💡 Enter your Kindle email above to enable Kindle sending")

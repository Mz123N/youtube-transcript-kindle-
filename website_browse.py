import os
import streamlit as st
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
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

# Rotating quotes from popular podcasters
import random
import time

quotes = [
    {
        "text": "The most important skill for getting rich is becoming a perpetual learner.",
        "author": "Naval Ravikant",
        "image": "https://images.squarespace-cdn.com/content/v1/58de89eb17bffc754e3c1d33/1552963210906-LVA904K3O50RP633WOVG/Aug+2016+Headshot.jpg"
    },
    {
        "text": "Read what you love until you love to read.",
        "author": "Naval Ravikant",
        "image": "https://images.squarespace-cdn.com/content/v1/58de89eb17bffc754e3c1d33/1552963210906-LVA904K3O50RP633WOVG/Aug+2016+Headshot.jpg"
    },
    {
        "text": "The best investment you can make is in yourself.",
        "author": "Charlie Munger",
        "image": "https://image.cnbcfm.com/api/v1/image/107340287-1701209338546-Charlie_Munger_1.jpg?v=1701214769"
    },
    {
        "text": "Knowledge is the new money. Information is the new wealth.",
        "author": "Balaji Srinivasan",
        "image": "https://www.fintechfestival.sg/hs-fs/hubfs/speakers/gZ-bFq1_mE6HiiFFEWf06FQf5W-1O1PrJZzd_YeYFLY.jpg?width=225&height=225&name=gZ-bFq1_mE6HiiFFEWf06FQf5W-1O1PrJZzd_YeYFLY.jpg"
    },
    {
        "text": "The internet is the greatest library ever created.",
        "author": "Balaji Srinivasan",
        "image": "https://www.fintechfestival.sg/hs-fs/hubfs/speakers/gZ-bFq1_mE6HiiFFEWf06FQf5W-1O1PrJZzd_YeYFLY.jpg?width=225&height=225&name=gZ-bFq1_mE6HiiFFEWf06FQf5W-1O1PrJZzd_YeYFLY.jpg"
    },
    {
        "text": "Success is not about being the best. It's about being better than you were yesterday.",
        "author": "Alex Hormozi",
        "image": "https://www.acquisition.com/hubfs/ACQ_Web_Bio-AlexHormozi%202.png"
    },
    {
        "text": "The more you learn, the more you earn.",
        "author": "Alex Hormozi",
        "image": "https://www.acquisition.com/hubfs/ACQ_Web_Bio-AlexHormozi%202.png"
    }
]

# Display a random quote each time
quote = random.choice(quotes)
st.markdown(f'''
<div class="quote-container">
    <img src="{quote['image']}" alt="{quote['author']}" class="speaker-image">
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

# Delivery section
st.markdown("### 📧 Delivery Options")
user_email = st.text_input("Your Email (to receive the file)")

# Set default sender credentials (your email)
sender_email = "mengnan188@gmail.com"  # Your Gmail address
sender_app_password = os.environ.get('SENDER_APP_PASSWORD', 'your_app_password_here')  # Get from environment variable

# Kindle delivery option
send_to_kindle_option = st.checkbox("Send to Kindle directly")

if send_to_kindle_option:
    st.markdown('<div class="info-box">📧 **Kindle Email Address:** This is the email address linked to your Kindle device. You can find your Kindle email address at <a href="https://www.amazon.com/sendtokindle/email" target="_blank">Amazon\'s Send to Kindle page</a>.</div>', unsafe_allow_html=True)
    kindle_email = st.text_input("Kindle Email")
else:
    kindle_email = None

if st.button("Generate and Send"):
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

        # 4. Step 1: Direct Download
        st.markdown("### 📥 Download Your File")
        
        # Read the generated file for download
        try:
            with open(output_filename, 'rb') as f:
                file_data = f.read()
            
            # Create download button based on format
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

        # 5. Step 2: Send Options
        st.markdown("### 📧 Send Options")
        
        # Email sending option
        if user_email:
            if st.button("📧 Send to Email"):
                st.write(f"Attempting to send file to email: {user_email}")
                
                if send_file_via_email(output_filename, user_email, video_title, sender_email, sender_app_password):
                    st.success(f"✅ File sent to your email: {user_email}")
                else:
                    st.error("❌ Failed to send file to your email. Please check your email address and try again.")
        else:
            st.info("💡 Enter your email above to enable email sending")
        
        # Kindle sending option (only for EPUB)
        if format_choice == "EPUB" and send_to_kindle_option and kindle_email:
            if st.button("📚 Send to Kindle"):
                if send_to_kindle(output_filename, video_title, kindle_email, sender_email, sender_app_password):
                    st.success(f"✅ File sent to Kindle: {kindle_email}")
                else:
                    st.error("❌ Failed to send to Kindle. Please check your Kindle email credentials.")
        elif format_choice == "PDF" and send_to_kindle_option:
            st.info("💡 Kindle sending is only available for EPUB files")
        elif send_to_kindle_option and not kindle_email:
            st.info("💡 Enter your Kindle email above to enable Kindle sending")

    except Exception as e:
        st.error("An error occurred while generating or saving the book.")
        st.exception(e)

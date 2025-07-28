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
col1, col2, col3 = st.columns(3)
with col1:
    st.markdown('<div class="feature-box"><h4>⚡ Instant Conversion</h4><p>Transform YouTube videos into readable e-books in seconds</p></div>', unsafe_allow_html=True)
with col2:
    st.markdown('<div class="feature-box"><h4>📱 Read Anywhere</h4><p>Access your content on Kindle, phone, or computer</p></div>', unsafe_allow_html=True)
with col3:
    st.markdown('<div class="feature-box"><h4>🎯 Smart Formatting</h4><p>Clean, organized content with proper sections</p></div>', unsafe_allow_html=True)

# Input section with styling
st.markdown('<div class="input-section">', unsafe_allow_html=True)
st.markdown("### 📝 Content Details")
youtube_url = st.text_input("YouTube Link")
book_title = st.text_input("Book Title")
format_choice = st.selectbox("Choose format:", ["EPUB", "PDF"])
st.markdown('</div>', unsafe_allow_html=True)

# Delivery section
st.markdown('<div class="input-section">', unsafe_allow_html=True)
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
st.markdown('</div>', unsafe_allow_html=True)

if st.button("Generate and Send"):
    try:
        st.info("Starting process...")
        st.write("Current working directory:", os.getcwd())

        # 1. Get and process inputs from the form
        video_id = extract_video_id(youtube_url)
        video_title = book_title  # Use the title from the form
        safe_title = sanitize_filename(video_title)
        
        # 2. Generate transcript and sections
        st.write("Step 1: Fetching transcript...")
        transcript = fetch_transcript(video_id)
        st.write(f"Transcript fetched: {len(transcript)} entries")
        
        st.write("Step 2: Grouping into sections...")
        sections = group_transcript_by_interval(transcript, interval_seconds=1200)
        st.write(f"Sections created: {len(sections)}")
        
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

        # 4. Handle delivery based on user choice
        success_messages = []
        
        # Always send to user's email
        if user_email:
            st.write(f"Attempting to send file to email: {user_email}")
            
            if send_file_via_email(output_filename, user_email, video_title, sender_email, sender_app_password):
                success_messages.append(f"File sent to your email: {user_email}")
                st.write("Email sent successfully!")
            else:
                st.error("Failed to send file to your email. Please check your email address and try again.")
        else:
            st.write("No user email provided, skipping email delivery")
        
        # Send to Kindle if option is selected
        if send_to_kindle_option and kindle_email:
            if send_to_kindle(output_filename, video_title, kindle_email, sender_email, sender_app_password):
                success_messages.append(f"File sent to Kindle: {kindle_email}")
            else:
                st.error("Failed to send to Kindle. Please check your Kindle email credentials.")
        
        # Show success message
        if success_messages:
            st.markdown('<div class="success-box">🎉 <strong>Success!</strong> ' + " | ".join(success_messages) + '</div>', unsafe_allow_html=True)
        else:
            st.warning("File generated but no delivery method selected.")

    except Exception as e:
        st.error("An error occurred while generating or saving the book.")
        st.exception(e)

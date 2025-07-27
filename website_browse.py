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

st.title("Turn Your Favorite Podcasts into E-Books")

youtube_url = st.text_input("YouTube Link")
book_title = st.text_input("Book Title")
format_choice = st.selectbox("Choose format:", ["EPUB", "PDF"])
user_email = st.text_input("Your Email (to receive the file)")

# Set default sender credentials (your email)
sender_email = "mengnan188@gmail.com"  # Your Gmail address
sender_app_password = os.environ.get('SENDER_APP_PASSWORD', 'your_app_password_here')  # Get from environment variable

# Kindle delivery option
send_to_kindle_option = st.checkbox("Send to Kindle directly")

if send_to_kindle_option:
    kindle_email = st.text_input("Kindle Email")
else:
    kindle_email = None

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
            st.success("Success! " + " | ".join(success_messages))
        else:
            st.warning("File generated but no delivery method selected.")

    except Exception as e:
        st.error("An error occurred while generating or saving the book.")
        st.exception(e)

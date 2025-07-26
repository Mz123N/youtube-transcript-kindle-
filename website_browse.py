import os
import streamlit as st
from main import (
    extract_video_id,
    sanitize_filename,
    fetch_transcript,
    group_transcript_by_interval,
    transcript_sections_to_epub_chapters,
    save_epub,
    send_to_kindle
)

st.title("YouTube Transcript to Kindle")

youtube_url = st.text_input("YouTube Link")
book_title = st.text_input("Book Title")
kindle_email = st.text_input("Kindle Email")
sender_email = st.text_input("Sender Gmail")
sender_app_password = st.text_input("Sender App Password", type="password")

if st.button("Generate and Send to Kindle"):
    try:
        st.info("Starting process...")
        st.write("Current working directory:", os.getcwd())

        # 1. Get and process inputs from the form
        video_id = extract_video_id(youtube_url)
        video_title = book_title  # Use the title from the form
        safe_title = sanitize_filename(video_title)
        output_filename = f"{safe_title}.epub"
        st.write("Saving file to:", output_filename)

        # 2. Generate transcript, chapters, and save epub
        st.write("Step 1: Fetching transcript...")
        transcript = fetch_transcript(video_id)
        st.write(f"Transcript fetched: {len(transcript)} entries")
        
        st.write("Step 2: Grouping into sections...")
        sections = group_transcript_by_interval(transcript, interval_seconds=1200)
        st.write(f"Sections created: {len(sections)}")
        
        st.write("Step 3: Creating chapters...")
        chapters = transcript_sections_to_epub_chapters(sections)
        st.write(f"Chapters created: {len(chapters)}")
        
        st.write("Step 4: Saving EPUB file...")
        save_epub(video_title, video_id, chapters, output_filename)
        st.write("EPUB file saved successfully!")

        # 3. Send to Kindle
        if send_to_kindle(output_filename, video_title, kindle_email, sender_email, sender_app_password):
            st.success(f"Book sent to Kindle successfully! Saved as {output_filename}")
        else:
            st.error("Failed to send to Kindle. Please check your email credentials.")

    except Exception as e:
        st.error("An error occurred while generating or saving the book.")
        st.exception(e)

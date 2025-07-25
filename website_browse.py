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
        transcript = fetch_transcript(video_id)
        sections = group_transcript_by_interval(transcript, interval_seconds=1200)
        chapters = transcript_sections_to_epub_chapters(sections)
        save_epub(video_title, video_id, chapters, output_filename)

        # 3. Send to Kindle
        send_to_kindle(output_filename, video_title)

        st.success(f"Book sent to Kindle successfully! Saved as {output_filename}")

    except Exception as e:
        st.error("An error occurred while generating or saving the book.")
        st.exception(e)

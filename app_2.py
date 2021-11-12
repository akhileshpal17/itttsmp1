import streamlit as st
import os
import time
import glob
import os
from gtts import gTTS
from googletrans import Translator

try:
    os.mkdir("temp")
except:
    pass
st.title("Text to speech")

text = st.text_area("Enter text")
def text_to_speech(text):
    tts = gTTS(text,lang="en",slow=False)
    try:
        my_file_name = text[0:20]
    except:
        my_file_name = "audio"
    tts.save(f"temp/{my_file_name}.mp3")
    return my_file_name,text


display_output_text = st.checkbox("Display output text")

if st.button("convert"):
    result, output_text = text_to_speech(text)
    audio_file = open(f"temp/{result}.mp3", "rb")
    audio_bytes = audio_file.read()
    st.markdown(f"## Your audio:")
    st.audio(audio_bytes, format="audio/mp3", start_time=0)

    if display_output_text:
        st.markdown(f"## Output text:")
        st.write(f" {output_text}")

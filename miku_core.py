import os
import webbrowser
from datetime import datetime
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Initialize Gemini model
model = genai.GenerativeModel("gemini-pro")

def handle_command(text):
    text = text.lower().strip()
    
    if "youtube" in text:
        webbrowser.open("https://www.youtube.com")
        return "Opening YouTube"
    elif "time" in text:
        return f"The current time is {datetime.now().strftime('%I:%M %p')}"
    elif "search" in text:
        query = text.replace("search", "").strip()
        webbrowser.open(f"https://www.google.com/search?q={query}")
        return f"Searching for {query}"
    elif "open notepad" in text:
        os.system("notepad.exe")
        return "Opening Notepad"
    elif "open calculator" in text:
        os.system("calc.exe")
        return "Opening Calculator"
    elif "open resume" in text:
        path = "C:/Users/YourName/Documents/resume.pdf"
        if os.path.exists(path):
            os.startfile(path)
            return "Opening your resume"
        else:
            return "Resume file not found"
    else:
        try:
            response = model.generate_content(text)
            return response.text.strip()
        except Exception as e:
            return f"Sorry, something went wrong: {e}"

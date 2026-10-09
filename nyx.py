"""
NYX - Complete AI Voice + Text Assistant
Complete AI Voice + Text Assistant for Windows v5.0
Fixes: self.jstate, single voice, weather city, app opening, AI answers
"""
# ── IMPORTS ───────────────────────────────────────────────────────────────────
import os, sys, threading, time, datetime, json, re, math, unicodedata
import random, webbrowser, requests, queue, urllib.parse
import xml.etree.ElementTree as ET
import subprocess
from PIL import Image, ImageDraw
import customtkinter as ctk
import tkinter as tk
import speech_recognition as sr
import pyttsx3, pyautogui, pystray, wikipedia

# ── SOUNDDEVICE PYAUDIO WORKAROUND (for Python 3.14+) ─────────────────────────
import sounddevice as sd
class SounddeviceMicrophone(sr.AudioSource):
    def __init__(self, device_index=None, sample_rate=16000, chunk_size=1024):
        self.device_index = device_index
        self.SAMPLE_RATE = sample_rate
        self.CHUNK = chunk_size
        self.SAMPLE_WIDTH = 2  # 16-bit PCM has 2 bytes per sample
        self.format = 8  # PyAudio's paInt16 is 8
        self.stream = None
        self.sd_stream = None

    def __enter__(self):
        assert self.stream is None, "This audio source is already inside a context manager"
        self.audio_queue = queue.Queue()
        
        def callback(indata, frames, time_info, status):
            self.audio_queue.put(indata.tobytes())
            
        self.sd_stream = sd.InputStream(
            device=self.device_index,
            channels=1,
            samplerate=self.SAMPLE_RATE,
            blocksize=self.CHUNK,
            dtype='int16',
            callback=callback
        )
        self.sd_stream.start()
        
        class StreamWrapper:
            def __init__(self, audio_queue, chunk_size):
                self.audio_queue = audio_queue
                self.chunk_size = chunk_size
                self.buffer = b""

            def read(self, size):
                bytes_to_read = size * 2
                while len(self.buffer) < bytes_to_read:
                    try:
                        self.buffer += self.audio_queue.get(timeout=2.0)
                    except queue.Empty:
                        self.buffer += b"\x00" * (bytes_to_read - len(self.buffer))
                data = self.buffer[:bytes_to_read]
                self.buffer = self.buffer[bytes_to_read:]
                return data

            def close(self):
                pass
                
        self.stream = StreamWrapper(self.audio_queue, self.CHUNK)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self.sd_stream:
            try:
                self.sd_stream.stop()
                self.sd_stream.close()
            except Exception:
                pass
            self.sd_stream = None
        self.stream = None

sr.Microphone = SounddeviceMicrophone

try:
    from ddgs import DDGS          # newer package name
    DDG = True
except Exception:
    try:
        from duckduckgo_search import DDGS   # older package name
        DDG = True
    except Exception:
        DDG = False

# gTTS gives NYX a real voice for Hindi / Marathi (Devanagari) — pyttsx3's
# Windows voices can't speak Indic scripts. Needs internet.
try:
    from gtts import gTTS
    GTTS_OK = True
except Exception:
    GTTS_OK = False

try:
    import psutil
    PSUTIL = True
except Exception:
    PSUTIL = False

try:
    import screen_brightness_control as sbc
except Exception:
    sbc = None

try:
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    AUDIO = True
except Exception:
    AUDIO = False

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# ── WAKE WORDS ────────────────────────────────────────────────────────────────
WAKE = ["hey nyx", "ok nyx", "hi nyx", "nyx", "wake up nyx"]

# ── JOKES (30) ────────────────────────────────────────────────────────────────
JOKES = [
    "Why do programmers prefer dark mode? Because light attracts bugs.",
    "How many programmers does it take to change a light bulb? None, that is a hardware problem.",
    "I would tell you a joke about UDP, but you might not get it.",
    "A SQL query walks into a bar and asks two tables: can I join you?",
    "Why did the developer go broke? He used up all his cache.",
    "Real programmers count from zero.",
    "My software has no bugs. It just develops random features.",
    "To understand recursion, you must first understand recursion.",
    "There are 10 kinds of people: those who understand binary and those who do not.",
    "Why do Java developers wear glasses? Because they do not C sharp.",
    "Algorithm: a word used by programmers when they do not want to explain what they did.",
    "Hardware is what you kick when software fails.",
    "A programmer is a machine that turns coffee into code.",
    "Debugging: being the detective in a crime movie where you are also the murderer.",
    "It works on my machine. Ship my machine.",
    "Why was the JavaScript developer sad? Because he did not know how to null his feelings.",
    "A computer science student said to his girlfriend: you are the CSS to my HTML.",
    "Why did the programmer quit his job? Because he did not get arrays.",
    "I am not lazy, I am in energy saving mode.",
    "Life is short. Smile while you still have teeth.",
    "I told my wife she was drawing her eyebrows too high. She looked surprised.",
    "Why do cows wear bells? Because their horns do not work.",
    "I am reading a book about anti-gravity. It is impossible to put down.",
    "Did you hear about the mathematician who is afraid of negative numbers? He will stop at nothing to avoid them.",
    "Why do not scientists trust atoms? Because they make up everything.",
    "What do you call a fish without eyes? A fsh.",
    "I asked my dog what two minus two is. He said nothing.",
    "Why did the scarecrow win an award? He was outstanding in his field.",
    "I only know 25 letters of the alphabet. I do not know why.",
    "What do you call cheese that is not yours? Nacho cheese.",
]

# ── MOTIVATIONAL QUOTES (20) ──────────────────────────────────────────────────
QUOTES = [
    "The only way to do great work is to love what you do. - Steve Jobs",
    "Success is not final, failure is not fatal. It is the courage to continue that counts. - Churchill",
    "Believe you can and you are halfway there. - Theodore Roosevelt",
    "It always seems impossible until it is done. - Nelson Mandela",
    "The future belongs to those who believe in the beauty of their dreams. - Eleanor Roosevelt",
    "Hard work beats talent when talent does not work hard. - Tim Notke",
    "Every expert was once a beginner. Keep going Boss.",
    "Do not watch the clock. Do what it does. Keep going. - Sam Levenson",
    "The secret of getting ahead is getting started. - Mark Twain",
    "You miss 100 percent of the shots you do not take. - Wayne Gretzky",
    "Whether you think you can or you think you cannot, you are right. - Henry Ford",
    "The best time to plant a tree was 20 years ago. The second best time is now.",
    "An unexamined life is not worth living. - Socrates",
    "Spread love everywhere you go. - Mother Teresa",
    "When you reach the end of your rope, tie a knot and hang on. - Franklin Roosevelt",
    "Always remember that you are absolutely unique. Just like everyone else. - Margaret Mead",
    "Do not go where the path may lead, go instead where there is no path. - Emerson",
    "You will face many defeats in life, but never let yourself be defeated. - Maya Angelou",
    "In the end, it is not the years in your life that count. It is the life in your years. - Lincoln",
    "Never let the fear of striking out keep you from playing the game. - Babe Ruth",
]

# ── FUN FACTS (20) ────────────────────────────────────────────────────────────
FACTS = [
    "Honey never spoils. Archaeologists found 3000 year old honey in Egyptian tombs that was still edible.",
    "A day on Venus is longer than a year on Venus because it rotates so slowly.",
    "Bananas are curved because they grow towards the sun during development.",
    "Octopuses have three hearts and blue blood due to copper based hemocyanin.",
    "The shortest war in history lasted 38 minutes between Britain and Zanzibar in 1896.",
    "Water can boil and freeze at the same time known as the triple point phenomenon.",
    "A group of flamingos is called a flamboyance. How fitting for such colorful birds.",
    "Cleopatra lived closer in time to the Moon landing than to the building of the pyramids.",
    "Oxford University is older than the Aztec Empire by several centuries.",
    "The total weight of ants on Earth is roughly equal to the total weight of all humans.",
    "Lightning strikes the Earth about 100 times every single second.",
    "A snail can sleep for 3 years during hibernation in dry conditions.",
    "The human nose can detect over 1 trillion different scents according to scientists.",
    "Sharks are older than trees. Sharks have existed for 450 million years.",
    "There are more possible chess games than atoms in the observable universe.",
    "The Eiffel Tower grows about 15 cm taller in summer due to thermal expansion of iron.",
    "A group of crows is called a murder. A group of owls is called a parliament.",
    "Hot water can freeze faster than cold water under certain conditions, called the Mpemba effect.",
    "The average person walks about 100,000 miles in their lifetime, enough to circle Earth 4 times.",
    "Butterflies taste with their feet because they have taste sensors located there.",
]

# ── WEBSITES (60+) ────────────────────────────────────────────────────────────
SITES = {
    "youtube":          "https://youtube.com",
    "google":           "https://google.com",
    "gmail":            "https://mail.google.com",
    "google drive":     "https://drive.google.com",
    "google docs":      "https://docs.google.com",
    "google sheets":    "https://sheets.google.com",
    "google maps":      "https://maps.google.com",
    "maps":             "https://maps.google.com",
    "google news":      "https://news.google.com",
    "instagram":        "https://instagram.com",
    "twitter":          "https://twitter.com",
    "facebook":         "https://facebook.com",
    "whatsapp":         "https://web.whatsapp.com",
    "telegram":         "https://web.telegram.org",
    "linkedin":         "https://linkedin.com",
    "snapchat":         "https://snapchat.com",
    "pinterest":        "https://pinterest.com",
    "reddit":           "https://reddit.com",
    "tiktok":           "https://tiktok.com",
    "netflix":          "https://netflix.com",
    "amazon prime":     "https://primevideo.com",
    "hotstar":          "https://hotstar.com",
    "disney plus":      "https://disneyplus.com",
    "spotify":          "https://open.spotify.com",
    "apple music":      "https://music.apple.com",
    "soundcloud":       "https://soundcloud.com",
    "twitch":           "https://twitch.tv",
    "amazon":           "https://amazon.in",
    "flipkart":         "https://flipkart.com",
    "myntra":           "https://myntra.com",
    "meesho":           "https://meesho.com",
    "github":           "https://github.com",
    "stackoverflow":    "https://stackoverflow.com",
    "wikipedia":        "https://wikipedia.org",
    "medium":           "https://medium.com",
    "quora":            "https://quora.com",
    "chatgpt":          "https://chat.openai.com",
    "openai":           "https://openai.com",
    "claude":           "https://claude.ai",
    "gemini":           "https://gemini.google.com",
    "bard":             "https://gemini.google.com",
    "zoom":             "https://zoom.us",
    "notion":           "https://notion.so",
    "trello":           "https://trello.com",
    "canva":            "https://canva.com",
    "figma":            "https://figma.com",
    "bbc":              "https://bbc.com/news",
    "bbc news":         "https://bbc.com/news",
    "ndtv":             "https://ndtv.com",
    "zee news":         "https://zeenews.india.com",
    "times of india":   "https://timesofindia.indiatimes.com",
    "cricbuzz":         "https://cricbuzz.com",
    "espncricinfo":     "https://espncricinfo.com",
    "yahoo":            "https://yahoo.com",
    "bing":             "https://bing.com",
    "weather":          "https://weather.com",
    "imdb":             "https://imdb.com",
    "booking":          "https://booking.com",
    "airbnb":           "https://airbnb.com",
    "makemytrip":       "https://makemytrip.com",
    "uber":             "https://uber.com",
    "uber app":         "https://uber.com",
    "ola":              "https://olarides.com",
    "ola rides":        "https://olarides.com",
    "taxi":             "https://uber.com",
    "taxi booking":     "https://uber.com",
    "lyft":             "https://lyft.com",
    "meru":             "https://meruegypt.com",
}

# ── NEWS RSS SOURCES ──────────────────────────────────────────────────────────
NEWS_RSS = {
    "bbc world":    "http://feeds.bbci.co.uk/news/world/rss.xml",
    "bbc tech":     "http://feeds.bbci.co.uk/news/technology/rss.xml",
    "bbc sport":    "http://feeds.bbci.co.uk/sport/rss.xml",
    "reuters":      "https://feeds.reuters.com/reuters/topNews",
    "cnn":          "http://rss.cnn.com/rss/edition.rss",
    "al jazeera":   "https://www.aljazeera.com/xml/rss/all.xml",
    "toi":          "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
    "ndtv":         "https://feeds.feedburner.com/ndtvnews-top-stories",
}

# ── TOPIC TO NEWS SOURCE MAP ──────────────────────────────────────────────────
TOPIC_MAP = {
    "iran":         ["bbc world", "al jazeera", "reuters"],
    "israel":       ["bbc world", "al jazeera", "reuters"],
    "america":      ["reuters", "cnn", "bbc world"],
    "us":           ["reuters", "cnn", "bbc world"],
    "war":          ["bbc world", "al jazeera", "reuters"],
    "ukraine":      ["bbc world", "reuters", "cnn"],
    "russia":       ["bbc world", "reuters"],
    "china":        ["bbc world", "reuters"],
    "india":        ["toi", "ndtv", "bbc world"],
    "pakistan":     ["toi", "bbc world", "al jazeera"],
    "tech":         ["bbc tech"],
    "technology":   ["bbc tech"],
    "cricket":      ["toi", "bbc sport"],
    "ipl":          ["toi"],
    "sports":       ["bbc sport", "toi"],
    "football":     ["bbc sport"],
    "business":     ["reuters", "bbc world"],
    "economy":      ["reuters", "bbc world"],
    "climate":      ["bbc world", "reuters"],
    "world":        ["bbc world", "reuters", "al jazeera"],
    "middle east":  ["al jazeera", "reuters", "bbc world"],
    "europe":       ["bbc world", "reuters"],
    "modi":         ["toi", "ndtv"],
    "trump":        ["cnn", "reuters"],
    "election":     ["bbc world", "cnn", "reuters"],
    "gaza":         ["al jazeera", "bbc world", "reuters"],
}

# ── WINDOWS APPS (correct launch commands) ────────────────────────────────────
WINDOWS_APPS = {
    "notepad":              "notepad.exe",
    "calculator":           "calc.exe",
    "calc":                 "calc.exe",
    "camera":               "start microsoft.windows.camera:",
    "settings":             "start ms-settings:",
    "file explorer":        "explorer.exe",
    "explorer":             "explorer.exe",
    "task manager":         "taskmgr.exe",
    "paint":                "mspaint.exe",
    "word":                 "start winword",
    "microsoft word":       "start winword",
    "excel":                "start excel",
    "microsoft excel":      "start excel",
    "powerpoint":           "start powerpnt",
    "microsoft powerpoint": "start powerpnt",
    "outlook":              "start outlook",
    "microsoft outlook":    "start outlook",
    "teams":                "start msteams:",
    "microsoft teams":      "start msteams:",
    "edge":                 "start microsoft-edge:",
    "microsoft edge":       "start microsoft-edge:",
    "chrome":               "start chrome",
    "google chrome":        "start chrome",
    "firefox":              "start firefox",
    "spotify":              "start spotify:",
    "discord":              "start discord:",
    "steam":                "start steam:",
    "control panel":        "control",
    "cmd":                  "start cmd",
    "command prompt":       "start cmd",
    "powershell":           "start powershell",
    "terminal":             "start wt",
    "windows terminal":     "start wt",
    "snipping tool":        "start snippingtool",
    "media player":         "start wmplayer",
    "photos":               "start ms-photos:",
    "maps app":             "start bingmaps:",
    "clock":                "start ms-clock:",
    "alarm":                "start ms-clock:",
    "calendar":             "start outlookcal:",
    "mail":                 "start outlookmail:",
    "store":                "start ms-windows-store:",
    "microsoft store":      "start ms-windows-store:",
    "xbox":                 "start xbox:",
    "onenote":              "start onenote:",
    "skype":                "start skype:",
    "vlc":                  "start vlc",
    "vs code":              "start code",
    "visual studio code":   "start code",
    "pycharm":              "start pycharm64",
    "zoom":                 "start zoom:",
    "whatsapp":             "start whatsapp:",
    "telegram":             "start telegram:",
}

# ── 200 WORLD CITIES for weather detection ─────────────────────────────────────
WORLD_CITIES = [
    "london", "paris", "new york", "tokyo", "mumbai", "delhi", "pune",
    "bangalore", "hyderabad", "chennai", "kolkata", "dubai", "singapore",
    "sydney", "toronto", "berlin", "rome", "madrid", "amsterdam", "bangkok",
    "hong kong", "shanghai", "beijing", "moscow", "cairo", "chicago",
    "los angeles", "miami", "seattle", "boston", "houston", "las vegas",
    "washington", "san francisco", "lahore", "karachi", "dhaka", "colombo",
    "kathmandu", "kabul", "tehran", "riyadh", "istanbul", "athens",
    "budapest", "prague", "vienna", "zurich", "brussels", "stockholm",
    "oslo", "helsinki", "copenhagen", "lisbon", "dublin", "edinburgh",
    "manchester", "birmingham", "glasgow", "liverpool", "leeds", "bristol",
    "nairobi", "lagos", "accra", "johannesburg", "cape town", "casablanca",
    "tunis", "algiers", "addis ababa", "kinshasa", "dar es salaam",
    "mexico city", "sao paulo", "rio de janeiro", "buenos aires", "lima",
    "bogota", "santiago", "caracas", "quito", "la paz", "montevideo",
    "jakarta", "manila", "kuala lumpur", "hanoi", "ho chi minh",
    "phnom penh", "yangon", "vientiane", "taipei", "seoul", "osaka",
    "kyoto", "hiroshima", "nagoya", "sapporo", "auckland", "melbourne",
    "brisbane", "perth", "adelaide", "wellington", "christchurch",
    "vancouver", "montreal", "calgary", "ottawa", "winnipeg", "quebec",
    "goa", "jaipur", "agra", "varanasi", "amritsar", "kochi", "bhopal",
    "lucknow", "patna", "bhubaneswar", "indore", "nagpur", "surat",
    "ahmedabad", "vadodara", "rajkot", "chandigarh", "dehradun",
    "shimla", "manali", "mussoorie", "nainital", "rishikesh", "haridwar",
    "mysore", "coimbatore", "madurai", "tiruchirappalli", "visakhapatnam",
    "vijayawada", "guntur", "warangal", "tirupati", "mangalore",
    "hubli", "belgaum", "dharwad", "gulbarga", "bellary",
    "doha", "abu dhabi", "sharjah", "muscat", "kuwait city", "manama",
    "amman", "beirut", "damascus", "baghdad", "jerusalem", "tel aviv",
    "islamabad", "peshawar", "quetta", "multan", "faisalabad",
    "kabul", "herat", "mazar", "tashkent", "almaty", "astana",
    "baku", "tbilisi", "yerevan", "minsk", "kyiv", "warsaw",
    "sofia", "bucharest", "belgrade", "zagreb", "sarajevo", "skopje",
    "tirana", "podgorica", "valletta", "nicosia", "reykjavik",
]

# ── UNIT CONVERSIONS ──────────────────────────────────────────────────────────
def do_unit_conversion(text):
    text = text.lower()
    patterns = [
        (r"(\d+\.?\d*)\s*km\s+(?:to|in)\s+miles",
         lambda m: f"{m.group(1)} km = {float(m.group(1))*0.621371:.2f} miles"),
        (r"(\d+\.?\d*)\s*miles?\s+(?:to|in)\s+km",
         lambda m: f"{m.group(1)} miles = {float(m.group(1))*1.60934:.2f} km"),
        (r"(\d+\.?\d*)\s*(?:celsius|c)\s+(?:to|in)\s+(?:fahrenheit|f)",
         lambda m: f"{m.group(1)} Celsius = {float(m.group(1))*9/5+32:.1f} Fahrenheit"),
        (r"(\d+\.?\d*)\s*(?:fahrenheit|f)\s+(?:to|in)\s+(?:celsius|c)",
         lambda m: f"{float(m.group(1))-32:.1f} Fahrenheit = {(float(m.group(1))-32)*5/9:.1f} Celsius"),
        (r"(\d+\.?\d*)\s*kg\s+(?:to|in)\s+(?:pounds?|lbs?)",
         lambda m: f"{m.group(1)} kg = {float(m.group(1))*2.20462:.2f} pounds"),
        (r"(\d+\.?\d*)\s*(?:pounds?|lbs?)\s+(?:to|in)\s+kg",
         lambda m: f"{m.group(1)} pounds = {float(m.group(1))*0.453592:.2f} kg"),
        (r"(\d+\.?\d*)\s*meters?\s+(?:to|in)\s+feet",
         lambda m: f"{m.group(1)} meters = {float(m.group(1))*3.28084:.2f} feet"),
        (r"(\d+\.?\d*)\s*feet\s+(?:to|in)\s+meters?",
         lambda m: f"{m.group(1)} feet = {float(m.group(1))*0.3048:.2f} meters"),
        (r"(\d+\.?\d*)\s*(?:litres?|liters?)\s+(?:to|in)\s+gallons?",
         lambda m: f"{m.group(1)} liters = {float(m.group(1))*0.264172:.2f} gallons"),
        (r"(\d+\.?\d*)\s*gallons?\s+(?:to|in)\s+(?:litres?|liters?)",
         lambda m: f"{m.group(1)} gallons = {float(m.group(1))*3.78541:.2f} liters"),
        (r"(\d+\.?\d*)\s*(?:inches?|in)\s+(?:to|in)\s+cm",
         lambda m: f"{m.group(1)} inches = {float(m.group(1))*2.54:.2f} cm"),
        (r"(\d+\.?\d*)\s*cm\s+(?:to|in)\s+(?:inches?|in)",
         lambda m: f"{m.group(1)} cm = {float(m.group(1))/2.54:.2f} inches"),
        (r"(\d+\.?\d*)\s*(?:mph)\s+(?:to|in)\s+(?:kmph|kph)",
         lambda m: f"{m.group(1)} mph = {float(m.group(1))*1.60934:.2f} kmph"),
        (r"(\d+\.?\d*)\s*(?:kmph|kph)\s+(?:to|in)\s+mph",
         lambda m: f"{m.group(1)} kmph = {float(m.group(1))*0.621371:.2f} mph"),
    ]
    for pat, func in patterns:
        m = re.search(pat, text)
        if m:
            try:
                return func(m) + " Boss."
            except:
                pass
    return None

# ── HELPER FUNCTIONS ──────────────────────────────────────────────────────────
def norm_punct(text):
    """Convert unicode punctuation/spaces to ASCII so words don't fuse when the
    non-ASCII strip drops them (keep "must-see", "Big Ben", "St Paul's")."""
    if not text:
        return text
    out = []
    for ch in text:
        o = ord(ch)
        if ch == "—":                         out.append(" - ")   # em dash
        elif o in (0x2010, 0x2011, 0x2012, 0x2013, 0x2212): out.append("-")
        elif ch in ("‘", "’", "‛"): out.append("'")
        elif ch in ("“", "”"):           out.append('"')
        elif ch == "…":                       out.append("...")
        elif ch == "•":                       out.append("- ")
        elif unicodedata.category(ch) == "Zs":     out.append(" ")     # any space
        else:                                       out.append(ch)
    return "".join(out)

def ascii_clean(text):
    if not text:
        return ""
    text = norm_punct(text)
    # Fix NYX dotted spelling and other dot-separated acronyms
    text = re.sub(r'\bN\s*\.\s*Y\s*\.\s*X\s*\.?\b', 'NYX', text, flags=re.IGNORECASE)
    text = re.sub(r'\b([A-Z])\s*\.\s*([A-Z])\s*\.\s*([A-Z])\s*\.\s*([A-Z])\s*\.\s*([A-Z])\s*\.\s*([A-Z])\b',
                  r'\1\2\3\4\5\6', text)
    text = re.sub(r'\b([A-Z])\s*\.\s*([A-Z])\s*\.\s*([A-Z])\s*\.\s*([A-Z])\s*\.\s*([A-Z])\b',
                  r'\1\2\3\4\5', text)
    text = re.sub(r'\b([A-Za-z])\s*\.\s*([A-Za-z])\b', r'\1\2', text)
    # Normalise common unicode punctuation to ASCII so words don't fuse when
    # the non-ASCII strip removes them (e.g. "5-day", "St Paul's", not "5day").
    for uni, asc in {"—": " - ", "–": "-", "‑": "-", "‒": "-",
                     "’": "'", "‘": "'", "“": '"', "”": '"',
                     "…": "...", "•": "-", " ": " "}.items():
        text = text.replace(uni, asc)
    # Remove remaining non-ASCII
    text = text.encode("ascii", "ignore").decode("ascii")
    # Clean extra whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text

# ── MATH / LATEX FORMATTING ───────────────────────────────────────────────────
_SUP = {"0":"⁰","1":"¹","2":"²","3":"³","4":"⁴","5":"⁵","6":"⁶","7":"⁷","8":"⁸",
        "9":"⁹","+":"⁺","-":"⁻","=":"⁼","(":"⁽",")":"⁾","n":"ⁿ","i":"ⁱ","x":"ˣ",
        "a":"ᵃ","b":"ᵇ","c":"ᶜ","d":"ᵈ","k":"ᵏ","m":"ᵐ","t":"ᵗ"}
_SUB = {"0":"₀","1":"₁","2":"₂","3":"₃","4":"₄","5":"₅","6":"₆","7":"₇","8":"₈",
        "9":"₉","+":"₊","-":"₋","=":"₌","(":"₍",")":"₎","a":"ₐ","x":"ₓ","n":"ₙ",
        "i":"ᵢ","k":"ₖ","m":"ₘ","t":"ₜ"}
_MATH_CMDS = {
    "times":"×","cdot":"·","div":"÷","pm":"±","mp":"∓","leq":"≤","le":"≤",
    "geq":"≥","ge":"≥","neq":"≠","approx":"≈","equiv":"≡","propto":"∝","pi":"π",
    "theta":"θ","alpha":"α","beta":"β","gamma":"γ","delta":"δ","Delta":"Δ",
    "lambda":"λ","mu":"μ","sigma":"σ","Sigma":"Σ","omega":"ω","Omega":"Ω",
    "phi":"φ","rho":"ρ","tau":"τ","sum":"Σ","prod":"∏","int":"∫","infty":"∞",
    "rightarrow":"→","to":"→","Rightarrow":"⇒","leftarrow":"←","deg":"°",
    "circ":"°","angle":"∠","partial":"∂","nabla":"∇","in":"∈","forall":"∀",
    "exists":"∃","sqrt":"√",
}

def format_math(text):
    """Convert LaTeX-style math in AI answers to clean readable text for DISPLAY
    (e.g. \\(a^{2}+b^{2}=c^{2}\\) -> a²+b²=c²)."""
    if not text:
        return text
    text = re.sub(r'\\[\(\)\[\]]', '', text)          # \( \) \[ \]
    text = text.replace('$$', '').replace('$', '')
    text = re.sub(r'\\frac\{([^{}]*)\}\{([^{}]*)\}', r'(\1)/(\2)', text)
    text = re.sub(r'\\sqrt\{([^{}]*)\}', r'√(\1)', text)
    for name, sym in _MATH_CMDS.items():
        text = re.sub(r'\\' + name + r'(?![a-zA-Z])', sym, text)
    text = re.sub(r'\^\{([^{}]*)\}', lambda m: "".join(_SUP.get(c, c) for c in m.group(1)), text)
    text = re.sub(r'\^(\w)', lambda m: _SUP.get(m.group(1), "^" + m.group(1)), text)
    text = re.sub(r'_\{([^{}]*)\}', lambda m: "".join(_SUB.get(c, c) for c in m.group(1)), text)
    text = re.sub(r'_(\w)', lambda m: _SUB.get(m.group(1), "_" + m.group(1)), text)
    text = re.sub(r'\\[,;!:]', ' ', text)             # spacing commands
    text = re.sub(r'\\([a-zA-Z]+)', r'\1', text)      # strip any leftover \cmd
    text = text.replace('{', '').replace('}', '')
    return text

def speak_math(text):
    """Convert LaTeX-style math to spoken words for TTS
    (a^{2}+b^{2}=c^{2} -> a squared plus b squared equals c squared)."""
    if not text:
        return text
    text = re.sub(r'\\[\(\)\[\]]', ' ', text)
    text = text.replace('$', '')
    text = re.sub(r'\\frac\{([^{}]+)\}\{([^{}]+)\}', r' \1 over \2 ', text)
    text = re.sub(r'\\sqrt\{([^{}]+)\}', r' square root of \1 ', text)
    text = re.sub(r'\^\{?2\}?', ' squared ', text)
    text = re.sub(r'\^\{?3\}?', ' cubed ', text)
    text = re.sub(r'\^\{([^{}]+)\}', r' to the power \1 ', text)
    text = re.sub(r'\^(\w)', r' to the power \1 ', text)
    text = re.sub(r'_\{([^{}]+)\}', r' sub \1 ', text)
    text = re.sub(r'_(\w)', r' sub \1 ', text)
    text = text.replace('=', ' equals ').replace('+', ' plus ')
    text = re.sub(r'\\times', ' times ', text)
    text = re.sub(r'\\[a-zA-Z]+', ' ', text)
    text = text.replace('{', '').replace('}', '')
    return re.sub(r'\s{2,}', ' ', text)

def display_clean(text):
    """Tidy text for on-screen display while PRESERVING unicode (math symbols,
    superscripts, accents) — unlike ascii_clean which strips them."""
    if not text:
        return ""
    text = re.sub(r'\bN\s*\.\s*Y\s*\.\s*X\s*\.?\b', 'NYX', text, flags=re.IGNORECASE)
    text = norm_punct(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def extract_city(command):
    """Extract city name from weather command - handles all phrasings"""
    c = command.lower()
    # Remove all weather-related words
    for w in ["whats", "what's", "what is", "what", "tell me",
              "the weather", "weather", "temperature", "forecast",
              "climate", "how is", "how's", "is it", "will it",
              "raining", "sunny", "cloudy", "hot", "cold",
              "in", "at", "for", "of", "today", "now", "please",
              "right now", "currently", "outside", "like", "there"]:
        c = c.replace(w, " ")
    c = re.sub(r"\s+", " ", c).strip()
    # Remove punctuation
    c = re.sub(r"[^\w\s]", "", c).strip()
    # Remove common filler words
    for w in ["the", "a", "an", "is", "how", "be", "will", "get"]:
        c = re.sub(r"\b" + w + r"\b", "", c).strip()
    c = re.sub(r"\s+", " ", c).strip()
    # Check if remaining text matches a known city
    for city in WORLD_CITIES:
        if city in c:
            return city.title()
    # Return remaining text as city if it looks valid
    if len(c) > 1 and len(c) < 30:
        return c.strip().title()
    return None

def get_day_greeting():
    h = datetime.datetime.now().hour
    if h < 12:   return "Good morning"
    if h < 17:   return "Good afternoon"
    return "Good evening"   # "Good night" is a farewell, not a greeting

def get_system_voices():
    """Get all available Windows TTS voices"""
    try:
        eng = pyttsx3.init()
        voices = eng.getProperty("voices")
        result = {}
        for v in voices:
            result[v.name] = v.id
        try: eng.stop()
        except: pass
        return result
    except Exception as e:
        print(f"get_system_voices error: {e}")
        return {}

def parse_math(expr):
    """Parse and evaluate math - handles 30+3= and all natural language"""
    expr = str(expr).lower().strip()

    # Remove = sign at end (like 30+3=)
    expr = expr.rstrip("=").strip()

    # Remove question words
    for w in ["what is", "whats", "what's", "calculate", "compute", "solve",
              "how much is", "how much", "equals", "the answer to",
              "please", "boss", "nyx", "tell me"]:
        expr = expr.replace(w, "")
    expr = expr.strip()

    # Word to operator
    expr = expr.replace("plus", "+")
    expr = expr.replace("minus", "-")
    expr = expr.replace("times", "*")
    expr = expr.replace("multiplied by", "*")
    expr = expr.replace("divided by", "/")
    expr = expr.replace("over", "/")
    expr = expr.replace("mod", "%")
    expr = expr.replace("^", "**")
    expr = re.sub(r"\bx\b", "*", expr)

    # Square root
    m = re.search(r"square\s*root\s*of\s*([\d\.]+)", expr)
    if m:
        try:
            return str(round(math.sqrt(float(m.group(1))), 4))
        except: pass

    m = re.search(r"sqrt\s*\(?([\d\.]+)\)?", expr)
    if m:
        try:
            return str(round(math.sqrt(float(m.group(1))), 4))
        except: pass

    # Power
    m = re.search(r"([\d\.]+)\s*(?:to\s*the\s*power\s*of|power|raised\s*to)\s*([\d\.]+)", expr)
    if m:
        try:
            return str(round(float(m.group(1)) ** float(m.group(2)), 4))
        except: pass

    # Percentage
    m = re.search(r"([\d\.]+)\s*(?:percent|%)\s*(?:of\s*)?([\d\.]+)", expr)
    if m:
        try:
            return str(round(float(m.group(1)) * float(m.group(2)) / 100, 4))
        except: pass

    # Factorial
    m = re.search(r"(?:factorial\s*of\s*)?([\d]+)\s*(?:factorial|!)", expr)
    if m:
        try:
            n = int(m.group(1))
            if n <= 20:
                r = 1
                for i in range(1, n+1): r *= i
                return str(r)
        except: pass

    # Trig
    m = re.search(r"(sin|cos|tan)\s*(?:of\s*)?([\d\.]+)\s*(?:degrees?|deg)?", expr)
    if m:
        try:
            func, val = m.group(1), float(m.group(2))
            rad = math.radians(val)
            res = {"sin": math.sin, "cos": math.cos, "tan": math.tan}[func](rad)
            return str(round(res, 4))
        except: pass

    # Safe eval — works for 30+3, 50*2, (10+5)*3 etc.
    # IMPORTANT: only evaluate when a real math OPERATOR is present, otherwise a
    # sentence like "...population as of 2026" would wrongly return "2026".
    # A mid-string "=" (e.g. "7*8=56") must not glue both sides into one number
    # ("7*856"), so only the left-hand side is evaluated.
    if "=" in expr:
        expr = expr.split("=")[0]
    clean = re.sub(r"[^\d\+\-\*\/\.\(\)\%\s]", "", expr).strip()
    if clean and re.search(r"\d", clean) and re.search(r"[\+\-\*/%]", clean):
        try:
            result = eval(clean)
            if isinstance(result, float):
                if result == int(result):
                    return str(int(result))
                return str(round(result, 6))
            return str(result)
        except: pass

    return None

def check_math_claim(text):
    """Handle claims/explanations like 'is 7*8=54?' or 'explain why 7*8=56'.
    Returns a spoken reply, or None when the text isn't an 'A op B = C' claim."""
    t = str(text).lower().replace("×", "*").replace("÷", "/")
    t = re.sub(r"(?<=\d)\s*x\s*(?=\d)", "*", t)
    m = re.search(r"(\d[\d\s\+\-\*/\.\(\)%]*?)\s*=\s*(-?\d+(?:\.\d+)?)", t)
    if not m:
        return None
    left, claimed = m.group(1).strip(), m.group(2)
    if not re.search(r"[\+\-\*/%]", left):
        return None
    actual = parse_math(left)
    if actual is None:
        return None
    try:
        ok = abs(float(actual) - float(claimed)) < 1e-6
    except ValueError:
        return None
    expr = re.sub(r"\s+", "", left)
    explain = bool(re.search(r"\b(why|explain|how)\b", t))

    if not ok:
        return f"No, {expr} is {actual}, not {claimed}."
    reply = f"Yes, {expr} equals {actual}."
    if explain:
        mul = re.fullmatch(r"(\d+)\*(\d+)", expr)
        if mul:
            a, b = int(mul.group(1)), int(mul.group(2))
            a, b = min(a, b), max(a, b)
            if 1 < a <= 12:
                steps = " plus ".join([str(b)] * a)
                reply += (f" Multiplication is repeated addition. {a} times {b} "
                          f"means adding {b}, {a} times: {steps}, which makes {actual}.")
                return reply
        reply += f" Working it out step by step, {expr} gives {actual}."
    return reply

def is_connected():
    try:
        requests.get("https://google.com", timeout=3)
        return True
    except:
        return False

def find_app_in_registry(app_name):
    """Search Windows registry for installed app paths - most reliable method"""
    try:
        import winreg
        app_lower = app_name.lower().strip()
        reg_paths = [
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
            r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
        ]
        hives = [winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER]
        for hive in hives:
            for reg_path in reg_paths:
                try:
                    key = winreg.OpenKey(hive, reg_path)
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        try:
                            subkey_name = winreg.EnumKey(key, i)
                            subkey      = winreg.OpenKey(key, subkey_name)
                            try:
                                display_name = winreg.QueryValueEx(subkey, "DisplayName")[0].lower()
                                if (app_lower in display_name or
                                        display_name in app_lower or
                                        all(w in display_name for w in app_lower.split())):
                                    # Try to get install location
                                    for val in ["InstallLocation", "DisplayIcon"]:
                                        try:
                                            path = winreg.QueryValueEx(subkey, val)[0]
                                            path = path.strip('"').strip()
                                            if val == "DisplayIcon":
                                                # DisplayIcon often has ,0 at end
                                                path = path.split(",")[0].strip()
                                            if path and os.path.exists(path):
                                                if os.path.isdir(path):
                                                    # Search for exe in this dir
                                                    words = app_lower.split()
                                                    for f in os.listdir(path):
                                                        if f.lower().endswith(".exe"):
                                                            if (words[0] in f.lower() or
                                                                    app_lower.replace(" ","") in f.lower()):
                                                                return os.path.join(path, f)
                                                    # Return first exe found
                                                    for f in os.listdir(path):
                                                        if f.lower().endswith(".exe"):
                                                            return os.path.join(path, f)
                                                elif path.endswith(".exe"):
                                                    return path
                                        except:
                                            pass
                            except:
                                pass
                            winreg.CloseKey(subkey)
                        except:
                            pass
                    winreg.CloseKey(key)
                except:
                    pass
    except ImportError:
        pass
    except Exception as e:
        print(f"Registry search error: {e}")
    return None

def find_installed_app(app_name):
    """
    Search for installed app - checks registry first (most reliable),
    then Start Menu shortcuts, then Program Files directories.
    """
    app_lower = app_name.lower().strip()

    # ── Step 0: Check Windows Registry (MOST RELIABLE) ──
    reg_path = find_app_in_registry(app_name)
    if reg_path:
        return reg_path
    # This is the MOST reliable method - if app is installed it has a shortcut
    start_menu_dirs = [
        os.path.join(os.environ.get("APPDATA", ""),
                     "Microsoft", "Windows", "Start Menu", "Programs"),
        os.path.join(os.environ.get("PROGRAMDATA", r"C:\ProgramData"),
                     "Microsoft", "Windows", "Start Menu", "Programs"),
        os.path.join(os.path.expanduser("~"), "Desktop"),
        os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop"),
        os.path.join(os.environ.get("PUBLIC", r"C:\Users\Public"), "Desktop"),
    ]
    for sdir in start_menu_dirs:
        if not sdir or not os.path.exists(sdir):
            continue
        try:
            for root_dir, dirs, files in os.walk(sdir):
                for f in files:
                    fname = f.lower()
                    # Check if shortcut name matches app name
                    name_no_ext = fname.replace(".lnk", "").replace(".exe", "")
                    if (app_lower in name_no_ext or
                            name_no_ext in app_lower or
                            # Fuzzy: all words of app_lower present in filename
                            all(w in name_no_ext for w in app_lower.split())):
                        full = os.path.join(root_dir, f)
                        if f.endswith(".lnk"):
                            # Resolve shortcut to actual exe
                            try:
                                import win32com.client
                                shell = win32com.client.Dispatch("WScript.Shell")
                                target = shell.CreateShortCut(full).Targetpath
                                if target and os.path.exists(target):
                                    return target
                            except:
                                # If can't resolve, just return the lnk path
                                # Windows can launch it directly
                                return full
                        elif f.endswith(".exe"):
                            return full
        except Exception:
            continue

    # ── Step 2: Build exe candidates from app name ──
    words      = app_lower.split()
    candidates = []
    candidates.append(app_lower.replace(" ", "") + ".exe")
    candidates.append(app_lower.replace(" ", "_") + ".exe")
    candidates.append(app_lower.replace(" ", "-") + ".exe")
    candidates.append(words[0] + ".exe")
    if len(words) > 1:
        candidates.append("".join(words) + ".exe")
        candidates.append(words[0] + words[1] + ".exe")
        candidates.append(words[-1] + ".exe")

    # ── Known special cases ──
    special = {
        "arduino ide":          ["arduino_ide.exe", "arduino.exe", "arduino-ide.exe"],
        "arduino":              ["arduino_ide.exe", "arduino.exe", "arduino-ide.exe"],
        "vs code":              ["code.exe"],
        "visual studio code":   ["code.exe"],
        "visual studio":        ["devenv.exe"],
        "android studio":       ["studio64.exe", "studio.exe"],
        "postman":              ["postman.exe"],
        "obs":                  ["obs64.exe", "obs.exe"],
        "obs studio":           ["obs64.exe", "obs.exe"],
        "blender":              ["blender.exe"],
        "unity":                ["unity.exe", "unityhub.exe"],
        "unity hub":            ["unityhub.exe"],
        "sublime":              ["sublime_text.exe"],
        "sublime text":         ["sublime_text.exe"],
        "notepad plus":         ["notepad++.exe"],
        "notepad++":            ["notepad++.exe"],
        "7zip":                 ["7zfm.exe", "7z.exe"],
        "7 zip":                ["7zfm.exe"],
        "winrar":               ["winrar.exe"],
        "vlc":                  ["vlc.exe"],
        "audacity":             ["audacity.exe"],
        "gimp":                 ["gimp.exe", "gimp-2.10.exe", "gimp-2.99.exe"],
        "inkscape":             ["inkscape.exe"],
        "telegram":             ["telegram.exe"],
        "signal":               ["signal.exe"],
        "slack":                ["slack.exe"],
        "figma":                ["figma.exe"],
        "zoom":                 ["zoom.exe"],
        "skype":                ["skype.exe"],
        "minecraft":            ["minecraft.exe", "minecraftlauncher.exe"],
        "steam":                ["steam.exe"],
        "epic games":           ["epicgameslauncher.exe"],
        "epic":                 ["epicgameslauncher.exe"],
        "origin":               ["origin.exe"],
        "ea app":               ["eadesktop.exe"],
        "battle net":           ["battle.net.exe", "battlenet.exe"],
        "league of legends":    ["leagueclient.exe"],
        "valorant":             ["valorant.exe"],
        "tor browser":          ["firefox.exe"],
        "git bash":             ["git-bash.exe"],
        "git":                  ["git.exe", "git-bash.exe"],
        "python":               ["python.exe", "python3.exe"],
        "node":                 ["node.exe"],
        "npm":                  ["npm.cmd"],
        "pycharm":              ["pycharm64.exe", "pycharm.exe"],
        "intellij":             ["idea64.exe"],
        "eclipse":              ["eclipse.exe"],
        "netbeans":             ["netbeans64.exe"],
        "wamp":                 ["wampmanager.exe"],
        "xampp":                ["xampp-control.exe"],
        "mysql workbench":      ["mysqlworkbench.exe"],
        "dbeaver":              ["dbeaver.exe"],
        "filezilla":            ["filezilla.exe"],
        "putty":                ["putty.exe"],
        "winscp":               ["winscp.exe"],
        "rufus":                ["rufus.exe"],
        "cpu z":                ["cpuz.exe", "cpuz_x64.exe"],
        "gpu z":                ["gpuz.exe"],
        "ccleaner":             ["ccleaner64.exe", "ccleaner.exe"],
        "malwarebytes":         ["malwarebytes.exe"],
        "adobe reader":         ["acrord32.exe", "acrobat.exe"],
        "acrobat":              ["acrobat.exe", "acrord32.exe"],
        "photoshop":            ["photoshop.exe"],
        "illustrator":          ["illustrator.exe"],
        "premiere":             ["premiere pro.exe"],
        "after effects":        ["afterfx.exe"],
        "lightroom":            ["lightroom.exe"],
        "winamp":               ["winamp.exe"],
        "media player classic": ["mpc-hc64.exe", "mpc-hc.exe"],
        "krita":                ["krita.exe"],
        "handbrake":            ["handbrake.exe"],
        "cpu-z":                ["cpuz_x64.exe", "cpuz.exe"],
        "hwinfo":               ["hwinfo64.exe", "hwinfo.exe"],
        "speccy":               ["speccy64.exe", "speccy.exe"],
        "etcher":               ["balenaetcher.exe"],
        "rufus":                ["rufus.exe"],
        "ventoy":               ["ventoy2disk.exe"],
        "windhawk":             ["windhawk.exe"],
        "powertoys":            ["powertoys.exe"],
        "everything":           ["everything.exe"],
        "keypirinha":           ["keypirinha.exe"],
        "autoruns":             ["autoruns64.exe", "autoruns.exe"],
        "process hacker":       ["processhacker.exe"],
        "process explorer":     ["procexp64.exe", "procexp.exe"],
        "wireshark":            ["wireshark.exe"],
        "nmap":                 ["nmap.exe"],
        "burp suite":           ["burpsuite.exe", "burpsuite_community.exe"],
        "virtualbox":           ["virtualbox.exe"],
        "vmware":               ["vmware.exe", "vmplayer.exe"],
        "hyper v":              ["vmconnect.exe"],
        "docker":               ["docker desktop.exe", "docker.exe"],
        "wsl":                  ["wsl.exe"],
    }
    if app_lower in special:
        candidates = special[app_lower] + candidates

    # ── Step 3: Search common install directories ──
    search_dirs = []
    # Add all drive letters
    for drive in ["C", "D", "E", "F"]:
        search_dirs += [
            f"{drive}:\\Program Files",
            f"{drive}:\\Program Files (x86)",
            os.path.join(f"{drive}:\\Users",
                         os.environ.get("USERNAME", ""),
                         "AppData", "Local", "Programs"),
            f"{drive}:\\tools",
            f"{drive}:\\dev",
            f"{drive}:\\apps",
        ]
    # Also add user-specific paths
    search_dirs += [
        os.path.join(os.path.expanduser("~"), "AppData", "Local", "Programs"),
        os.path.join(os.path.expanduser("~"), "AppData", "Roaming"),
        os.path.join(os.path.expanduser("~"), "Desktop"),
        os.path.join(os.path.expanduser("~"), "OneDrive", "Desktop"),
        os.environ.get("PROGRAMFILES",      r"C:\Program Files"),
        os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs"),
    ]
    # Remove duplicates and nonexistent
    seen_dirs = set()
    clean_dirs = []
    for d in search_dirs:
        if d and d not in seen_dirs and os.path.exists(d):
            seen_dirs.add(d)
            clean_dirs.append(d)

    for search_dir in clean_dirs:
        try:
            for root_dir, dirs, files in os.walk(search_dir):
                for f in files:
                    f_lower = f.lower()
                    for cand in candidates:
                        if f_lower == cand.lower():
                            return os.path.join(root_dir, f)
                    # Also do fuzzy folder name match - app folder often contains app name
                    folder = os.path.basename(root_dir).lower()
                    if (app_lower in folder or
                            all(w in folder for w in app_lower.split())):
                        if f_lower.endswith(".exe") and words[0] in f_lower:
                            return os.path.join(root_dir, f)
                # Limit depth to avoid very slow search
                depth = root_dir[len(search_dir):].count(os.sep)
                if depth >= 5:
                    dirs.clear()
        except Exception:
            continue

    return None

# ── MEMORY MANAGER ────────────────────────────────────────────────────────────
class MemoryManager:
    def __init__(self):
        self.pfile = "nyx_profile.json"
        self.hfile = "nyx_history.json"
        # Notes go on the REAL desktop (OneDrive-redirected desktops have no
        # plain ~/Desktop, which made note-saving silently fail).
        _u = os.environ.get("USERPROFILE", os.path.expanduser("~"))
        _desk = next((d for d in [os.path.join(_u, "Desktop"),
                                  os.path.join(_u, "OneDrive", "Desktop")]
                      if os.path.exists(d)), _u)
        self.nfile = os.path.join(_desk, "nyx_notes.txt")
        self.profile = self._load(self.pfile, {
            "name":       "",
            "city":       "Pune",
            "country":    "India",
            "voice_id":   "",
            "voice_name": "",
            "rate":       160,
            "wake":       True,
            "facts":      [],
            "todos":      [],
        })
        self.history = self._load(self.hfile, [])

    def _load(self, path, default):
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    return json.load(f)
            except:
                pass
        return default

    def save_profile(self):
        try:
            with open(self.pfile, "w", encoding="utf-8") as f:
                json.dump(self.profile, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"save_profile error: {e}")

    def add_history(self, role, text):
        try:
            # Preserve unicode (Hindi/Marathi) so multi-turn context isn't lost.
            clean = re.sub(r"\s+", " ", (text or "")).strip()[:2000]
            self.history.append({
                "role": role,
                "text": clean,
                "ts":   str(datetime.datetime.now())
            })
            if len(self.history) > 500:
                self.history = self.history[-500:]
            with open(self.hfile, "w", encoding="utf-8") as f:
                json.dump(self.history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"add_history error: {e}")

    def add_fact(self, fact):
        fact = ascii_clean(fact)
        if fact and fact not in self.profile["facts"]:
            self.profile["facts"].append(fact)
            self.save_profile()

    def ctx(self):
        parts = []
        if self.profile["facts"]:
            parts.append("Known facts: " + "; ".join(self.profile["facts"][-8:]))
        return " ".join(parts)

    def add_note(self, text):
        try:
            with open(self.nfile, "a", encoding="utf-8") as f:
                f.write(f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')} - {text}\n")
        except Exception as e:
            print(f"add_note error: {e}")

    def get_notes(self, n=3):
        try:
            if os.path.exists(self.nfile):
                with open(self.nfile, encoding="utf-8") as f:
                    lines = [l.strip() for l in f.readlines() if l.strip()]
                return lines[-n:]
        except:
            pass
        return []

    def add_todo(self, item):
        self.profile["todos"].append({"item": item, "done": False})
        self.save_profile()

    def get_todos(self):
        return self.profile.get("todos", [])

    def complete_todo(self, index):
        todos = self.profile.get("todos", [])
        if 0 <= index < len(todos):
            todos[index]["done"] = True
            self.save_profile()
            return True
        return False

# ── GROQ API KEY ──────────────────────────────────────────────────────────────
# Key is no longer hardcoded. It is read from the GROQ_API_KEY environment
# variable, or (if that's not set) from a local config.json file that sits
# next to this script and is NOT pushed to GitHub (see .gitignore).
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
if not GROQ_API_KEY:
    try:
        import json as _json
        _cfg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
        with open(_cfg_path, "r", encoding="utf-8") as _f:
            GROQ_API_KEY = _json.load(_f).get("GROQ_API_KEY", "")
    except Exception:
        GROQ_API_KEY = ""
# NOTE: Groq decommissioned the llama-3.3 models (they now 404). This key has
# access to openai/gpt-oss-120b (strong general chat model) — used with
# reasoning_effort=low so it returns clean answers, not empty/oversized ones.
GROQ_MODEL   = "openai/gpt-oss-120b"
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"

# ── AI BRAIN ──────────────────────────────────────────────────────────────────
class Brain:
    def __init__(self, mem: MemoryManager):
        self.mem = mem
        self.reply_ctx = None   # set when the user replies to a specific message

    def _sys(self, lang="en"):
        """Build system prompt - supports Hindi and English"""
        p = self.mem.profile
        facts_text = ""
        if p.get("facts"):
            facts_text = "Known facts about user: " + "; ".join(p["facts"][-10:]) + "."

        name = p.get("name", "") or ""
        if lang == "mr":
            return (
                "तुम्ही NYX आहात, एक प्रगत AI वैयक्तिक सहाय्यक. "
                "महत्त्वाचे: फक्त मराठी भाषेत, देवनागरी लिपीत उत्तर द्या (रोमन लिपीत नाही). "
                f"तुम्ही {name} ची सेवा करत आहात जे {p['city']}, {p['country']} येथे राहतात. "
                f"आजची तारीख {datetime.datetime.now().strftime('%d %B %Y')} आहे. "
                f"वेळ {datetime.datetime.now().strftime('%I:%M %p')} आहे. "
                "वापरकर्त्याला त्यांच्या नावाने संबोधा, 'Boss' कधीही म्हणू नका. "
                "हुशार, थोडक्यात आणि उपयुक्त राहा, २-४ वाक्यांत उत्तर द्या. "
                "कधीही म्हणू नका की तुम्ही उत्तर देऊ शकत नाही. "
                "जर 'LIVE REAL-TIME WEB RESULTS' दिले असतील तर त्यांच्या आधारे उत्तर द्या - "
                "सध्याचे राष्ट्रपती, मंत्री, तारीख किंवा बातम्या स्वतःच्या स्मृतीतून सांगू नका. "
                f"{facts_text}"
            )
        if lang == "hi":
            return (
                f"Aap NYX hain, ek advanced AI personal assistant. "
                f"Aap {name} ki seva kar rahe hain jo {p['city']}, {p['country']} mein rehte hain. "
                f"Aaj ki taareekh {datetime.datetime.now().strftime('%A, %d %B %Y')} hai. "
                f"Samay hai {datetime.datetime.now().strftime('%I:%M %p')}. "
                f"User ko unke naam se ya seedhe baat karein. 'Boss' kabhi mat kahein. "
                f"Hindi mein jawab dein. Seedha aur helpful jawab dein, 2-4 sentences mein. "
                f"Kabhi mat kahein ki aap AI hain ya kuch nahi kar sakte. "
                f"Agar 'LIVE REAL-TIME WEB RESULTS' diye gaye hain to unhi ke aadhaar par "
                f"jawab dein - current president, minister, date, ya news apni memory se mat batayein. "
                f"{facts_text}"
            )
        return (
            f"You are NYX, an advanced AI personal assistant. "
            f"You serve {name} who lives in {p['city']}, {p['country']}. "
            f"Today is {datetime.datetime.now().strftime('%A, %d %B %Y')}. "
            f"Time is {datetime.datetime.now().strftime('%I:%M %p')}. "
            f"Speak naturally and directly without using titles or nicknames "
            f"(never say 'Boss' or 'Sir'). "
            f"Be smart, concise, helpful. Reply in 2-4 sentences. "
            f"NEVER say you cannot answer. Always give a helpful response. "
            f"You have full file system access and can find, read, open any files or "
            f"folders on the user's computer. "
            f"IMPORTANT: Your training data is out of date. For anything current - the "
            f"present president, prime minister, ministers, office-holders, prices, scores, "
            f"dates or recent events - you MUST rely ONLY on the 'LIVE REAL-TIME WEB RESULTS' "
            f"provided in this conversation and never contradict them from memory. "
            f"You have access to user conversation history and remember previous messages. "
            f"{facts_text}"
        )

    def _build_messages(self, prompt, lang="en", web=""):
        """Build messages for Groq with conversation history + live web context."""
        messages = [{"role": "system", "content": self._sys(lang)}]
        # If the user is replying to a specific earlier message, quote it so the
        # model answers with that exact context in mind.
        if self.reply_ctx:
            messages.append({
                "role": "system",
                "content": (f'The user is replying to this earlier message: '
                            f'"{self.reply_ctx[:500]}". Answer their reply with '
                            f'that context in mind.')
            })
        # Inject fresh real-time web results so answers aren't limited to
        # the model's training cut-off.
        if web:
            messages.append({
                "role": "system",
                "content": (
                    f"LIVE REAL-TIME WEB RESULTS (retrieved just now, "
                    f"{datetime.datetime.now().strftime('%d %B %Y %I:%M %p')}). "
                    f"These are CURRENT and OVERRIDE anything in your training "
                    f"data. Base your answer on them:\n{web}"
                )
            })
        # Send last 8 messages as context
        recent = self.mem.history[-8:] if self.mem.history else []
        for h in recent:
            role = "user" if h["role"] == "user" else "assistant"
            text = h["text"][:300]
            messages.append({"role": role, "content": text})
        messages.append({"role": "user", "content": prompt})
        return messages

    def _is_timely(self, prompt):
        """True if the question likely needs current, real-time information."""
        p = prompt.lower()
        kws = ["latest", "current", "currently", "today", "yesterday", "recent",
               "recently", "right now", "this week", "this month", "this year",
               "breaking", "2024", "2025", "2026", "election", "elected",
               "appointed", "resigned", "who is the", "who's the", "prime minister",
               "president", "minister", "ceo", "score", "news", "update", "updates",
               "price of", "stock", "happening", "live", "just now", "new "]
        return any(k in p for k in kws)

    def _news_search(self, query, n=6):
        """Fresh headlines via Google News RSS search (great for current events)."""
        try:
            url = ("https://news.google.com/rss/search?q="
                   + urllib.parse.quote(query)
                   + "&hl=en-IN&gl=IN&ceid=IN:en")
            r = requests.get(url, timeout=10,
                             headers={"User-Agent": "Mozilla/5.0"})
            root = ET.fromstring(r.content)
            lines = []
            for it in root.findall("./channel/item")[:n]:
                t = it.find("title")
                d = it.find("pubDate")
                if t is None or not t.text:
                    continue
                line = ascii_clean(t.text)
                if d is not None and d.text:
                    line += f" ({d.text[:16]})"
                lines.append("- " + line)
            return "\n".join(lines)
        except Exception as e:
            print(f"News search failed: {e}")
        return ""

    def _ddg_search(self, query, n=4):
        """Live DuckDuckGo web search via ddgs — title + snippet. Good for
        obscure/factual current questions news feeds don't cover."""
        if not DDG:
            return ""
        try:
            with DDGS() as d:
                results = list(d.text(query, max_results=n))
            lines = []
            for r in results[:n]:
                title = ascii_clean(r.get("title", ""))
                body  = ascii_clean(r.get("body", ""))
                if body:
                    lines.append(f"- {title}: {body}"[:240])
            return "\n".join(lines)
        except Exception as e:
            print(f"DDG search failed: {e}")
        return ""

    def _web_context(self, query, n=6):
        """Combine live news headlines + live web snippets into one digest so
        Groq can answer current questions accurately. Returns '' if both fail."""
        parts = []
        news = self._news_search(query, n)
        if news:
            parts.append("RECENT NEWS HEADLINES:\n" + news)
        web = self._ddg_search(query, 4)
        if web:
            parts.append("WEB RESULTS:\n" + web)
        return "\n\n".join(parts)

    @staticmethod
    def _digest(web):
        """Flatten a labelled web-context block into one readable sentence run
        (used when answering directly from live results without an LLM)."""
        txt = re.sub(r"(RECENT NEWS HEADLINES:|WEB RESULTS:)", "", web)
        txt = txt.replace("- ", "")
        txt = re.sub(r"\s*\n\s*", ". ", txt)
        txt = re.sub(r"\s{2,}", " ", txt)
        return txt.strip()

    def _recent_user_text(self):
        """The user's previous question (excluding the current one), for
        disambiguating short follow-ups."""
        hist = self.mem.history[:-1] if self.mem.history else []
        for h in reversed(hist):
            if h.get("role") == "user" and h.get("text"):
                return h["text"]
        return ""

    def ask(self, prompt, lang="en"):
        """AI brain — pulls LIVE web context for current events, feeds it to
        Groq (RAG), then falls back to web digest / DDG / Wikipedia / built-in.
        NEVER refuses and is not limited to the model's training cut-off."""

        # ── Build a search query, augmenting vague/short follow-ups with the
        #    previous user turn (so "America?" after "who is the president"
        #    still gets grounded in live results). ──
        search_q = prompt
        if len(prompt.split()) <= 3:
            prev = self._recent_user_text()
            if prev:
                search_q = f"{prev} {prompt}".strip()

        # ── Fetch fresh real-time context up front for timely questions ──
        web = ""
        if self._is_timely(search_q):
            print(f"Fetching live web context for: {search_q!r}")
            web = self._web_context(search_q)
            if web:
                print(f"Live web context found ({web.count(chr(10))+1} items)")
            else:
                print("Live web context: none")

        # ── a. GROQ API (grounded on live web results when available) ──
        if GROQ_API_KEY and "YOUR_GROQ" not in GROQ_API_KEY:
            print(f"[NYX Brain] Question: {prompt}")
            print(f"[NYX Brain] Trying Groq ({GROQ_MODEL})...")
            try:
                response = requests.post(
                    GROQ_URL,
                    headers={
                        "Authorization": f"Bearer {GROQ_API_KEY}",
                        "Content-Type":  "application/json"
                    },
                    json={
                        "model":            GROQ_MODEL,
                        "messages":         self._build_messages(prompt, lang, web),
                        "max_tokens":       900,
                        "temperature":      0.7,
                        # gpt-oss is a reasoning model — keep effort low so it
                        # returns the actual answer instead of empty content.
                        "reasoning_effort": "low",
                    },
                    timeout=20
                )
                print(f"[NYX Brain] Groq status: {response.status_code}")
                if response.status_code == 200:
                    text = response.json()["choices"][0]["message"]["content"] or ""
                    # Strip any reasoning tags some models emit.
                    text = re.sub(r"<think>.*?</think>", "", text,
                                  flags=re.DOTALL).strip()
                    if text:
                        print(f"[NYX Brain] Groq SUCCESS: {text[:100]}")
                        # Hindi/Marathi keep Devanagari; tables keep newlines +
                        # column spacing; plain prose gets the tidy ascii clean.
                        if lang in ("hi", "mr"):
                            return text
                        if ("\n" in text) or (text.count("|") >= 3):
                            return norm_punct(text).encode(
                                "ascii", "ignore").decode("ascii").strip()
                        return ascii_clean(text)
                    print("[NYX Brain] Groq FAILED: empty response")
                else:
                    print(f"[NYX Brain] Groq FAILED: {response.text[:200]}")
            except Exception as e:
                print(f"[NYX Brain] Groq EXCEPTION: {e}")

        # ── b. Groq unavailable → answer directly from live web results ──
        if web:
            print("Answering from live web results")
            return ascii_clean("Here is the latest. " + self._digest(web))[:600]

        # ── c. Live web search for any remaining factual question ──
        print("Trying live web search...")
        web2 = self._web_context(search_q)
        if web2:
            print("Web search success")
            return ascii_clean("Here is what I found. " + self._digest(web2))[:600]

        # ── d. Wikipedia ──
        print("Trying Wikipedia...")
        try:
            q = prompt.lower()
            for w in ["who is", "who was", "what is", "what was", "tell me about",
                      "explain", "define", "please", "can you", "do you know"]:
                q = q.replace(w, "").strip()
            hits = wikipedia.search(q or prompt, results=4)
            for h in hits:
                try:
                    s = ascii_clean(
                        wikipedia.summary(h, sentences=3, auto_suggest=False))
                    if s and len(s) > 40:
                        print("Wikipedia success")
                        return s
                except Exception:
                    continue
            print("Wikipedia failed: no summary")
        except Exception as e:
            print(f"Wikipedia failed: {e}")

        # ── e. Built-in helpful answer (NEVER a flat refusal) ──
        print("All sources failed — using built-in helpful answer.")
        p = prompt.lower()
        if any(w in p for w in ["visit", "see there", "tourist", "travel to",
                                 "trip to", "going to", "things to do", "places to visit",
                                 "sightseeing", "what to see", "itinerary"]):
            for city in WORLD_CITIES:
                if city in p:
                    c = city.title()
                    return (f"{c} is a fantastic destination Boss! Must-see attractions "
                            f"include its famous landmarks, museums, and cultural sites. "
                            f"Try the local cuisine and explore the historic areas.")
            return ("That sounds like a wonderful trip Boss! I recommend researching top "
                    "attractions, local food, transport, and accommodation.")
        if any(w in p for w in ["recipe", "how to make", "how to cook", "ingredients"]):
            return ("Great choice Boss! Start by gathering the ingredients, prep them, "
                    "then cook step by step. I can open a detailed recipe for you if you like.")
        if "how to" in p or "how do i" in p:
            return ("Good question Boss. The best approach is to break it into steps and follow "
                    "a trusted guide. I can open a detailed tutorial for you if you want.")
        # Absolute last resort — still a useful, on-topic reply
        return (f"Here is what I can tell you Boss: {prompt.strip().capitalize()} "
                f"is a good topic to explore. I can search the web for the very latest "
                f"details if you would like me to.")

    def weather(self, city):
        """Get weather using JSON API - no encoding issues"""
        try:
            url = f"https://wttr.in/{urllib.parse.quote(city)}?format=j1"
            r = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200:
                d   = r.json()["current_condition"][0]
                temp  = d["temp_C"]
                feels = d["FeelsLikeC"]
                desc  = d["weatherDesc"][0]["value"]
                hum   = d["humidity"]
                wind  = d["windspeedKmph"]
                return (f"{desc}, {temp} degrees Celsius, "
                        f"feels like {feels} degrees, "
                        f"humidity {hum} percent, "
                        f"wind {wind} km per hour")
        except Exception as e:
            print(f"Weather error: {e}")
        return None

    def news(self, topic="world", count=5):
        """Fetch news headlines from multiple RSS sources - respects count"""
        topic_l = topic.lower()
        # Find matching sources
        sources = ["bbc world", "reuters", "al jazeera"]
        for kw, srcs in TOPIC_MAP.items():
            if kw in topic_l:
                sources = srcs
                break

        # Always add extra sources to fill up count
        extra_sources = ["bbc world", "reuters", "cnn", "al jazeera", "toi", "ndtv", "bbc tech", "bbc sport"]
        for s in extra_sources:
            if s not in sources:
                sources.append(s)

        headlines = []
        seen = set()  # avoid duplicates

        for src in sources:
            if len(headlines) >= count:
                break
            url = NEWS_RSS.get(src)
            if not url:
                continue
            try:
                r    = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
                root = ET.fromstring(r.content)
                kws  = topic_l.split()
                for item in root.findall("./channel/item")[:30]:
                    if len(headlines) >= count:
                        break
                    t = item.find("title")
                    if t is None or not t.text:
                        continue
                    title = ascii_clean(t.text.strip())
                    if not title or title in seen:
                        continue
                    seen.add(title)
                    if topic_l in ["world", "general"]:
                        headlines.append(f"{src.upper()}: {title}")
                    elif any(k in title.lower() for k in kws):
                        headlines.append(f"{src.upper()}: {title}")
                    elif len(headlines) < 3:
                        # Add anyway if we have very few results
                        headlines.append(f"{src.upper()}: {title}")
            except Exception as e:
                print(f"News {src}: {e}")

        return headlines[:count]

# ── MAIN APP ──────────────────────────────────────────────────────────────────
class Nyx(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("NYX v1.0")

        # Center window on screen — 1200x800 minimum, resizable
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        W, H   = 1200, 800
        self.geometry(f"{W}x{H}+{max(0,(sw-W)//2)}+{max(0,(sh-H)//2)}")
        self.minsize(1200, 800)
        self.resizable(True, True)
        self.configure(fg_color="#050515")

        # Core modules
        self.mem   = MemoryManager()
        self.brain = Brain(self.mem)

        # Speech recognition — tuned for cleaner recognition of full sentences
        self.rec = sr.Recognizer()
        self.rec.dynamic_energy_threshold = True
        self.rec.energy_threshold      = 300    # lower = picks up quieter speech
        self.rec.pause_threshold       = 0.9    # end phrase after silence
        self.rec.non_speaking_duration = 0.4    # keep a little audio around speech
        self.phrase_time_limit         = 12

        # !! CRITICAL: use jstate NOT state (avoids CTk conflict) !!
        self.jstate    = "INITIALIZING"
        self.running   = True
        self.Q         = queue.Queue()
        self.think_wid = None
        self.input_mode = "VOICE"   # Background voice assistant — wake word always on

        # Background / tray mode.
        # Launched at Windows boot (autostart adds "--tray") -> start hidden in
        # the tray. Launched manually -> show the dashboard window.
        self.headless_mode = ("--tray" in sys.argv)
        # Speech-to-text (wake word + mic) only runs while the window is visible.
        self._visible = not self.headless_mode

        # Quick-access folder/app shortcuts
        self.shortcuts = self._load_shortcuts()

        # Voice engine - single voice, thread safe, interruptible
        self.speak_lock        = threading.Lock()
        self.stop_flag         = False
        self._cur_engine       = None      # active pyttsx3 engine (for interrupt)
        self._mci_alias        = None      # active gTTS/MCI playback (for interrupt)
        self._last_image       = None      # last generated image (temp path)
        self._last_image_caption = ""
        self._reply_to         = None      # message the user is replying to
        self.pending_exe       = None      # .exe awaiting yes/no safety confirm
        self._pending_exe_time = 0
        self.voices_map        = get_system_voices()
        self.selected_voice_id = self.mem.profile.get("voice_id", "")
        self.speech_rate       = self.mem.profile.get("rate", 160)

        # Set default voice - prefer female
        if not self.selected_voice_id and self.voices_map:
            female = next(
                (vid for vname, vid in self.voices_map.items()
                 if any(k in vname.lower() for k in ["zira","hazel","susan","female","aria"])),
                None
            )
            self.selected_voice_id = female or list(self.voices_map.values())[0]

        self._build_ui()
        self._logo_init()
        # X button just hides to tray (background assistant keeps running)
        self.protocol("WM_DELETE_WINDOW", self._hide_to_tray)

        # Sync the mode button/mic with the VOICE default
        try:
            self.mode_btn.configure(text="🎙  VOICE", fg_color="#0040ff")
            self._mic_btn.configure(state="normal", fg_color="#0a1628")
        except Exception:
            pass

        # System tray icon (created once; lets user reopen the dashboard)
        self._create_tray_icon()

        # On first run, register NYX to start in the tray on Windows boot (so
        # it's ready when the laptop starts). Done once — a later "disable
        # autostart" then sticks instead of being re-enabled every launch.
        if not self.mem.profile.get("autostart_setup_done"):
            try:
                self._enable_autostart()
                self.mem.profile["autostart_setup_done"] = True
                self.mem.save_profile()
                print("[NYX] Auto-start on boot enabled (starts in tray).")
            except Exception as e:
                print(f"Autostart register error: {e}")

        # Start hidden in the background if launched at boot (--tray)
        if self.headless_mode:
            self.withdraw()

        # Start background threads
        threading.Thread(target=self._startup,   daemon=True).start()
        threading.Thread(target=self._wake_loop, daemon=True).start()
        threading.Thread(target=self._reminder_loop, daemon=True).start()
        self._process()

    # ── BUILD UI ─────────────────────────────────────────────────────────────
    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        BG = "#050515"

        # Display attributes read by the header canvas each frame
        self._jdisp = "INITIALIZING"
        self._jcol  = "#ffffff"
        self._hw    = 1200          # live header width (updated on resize)

        # ── HEADER CANVAS (arc reactor + title + status pill + starfield) ──
        self.header_canvas = tk.Canvas(self, height=362, bg=BG,
                                       highlightthickness=0, bd=0)
        self.header_canvas.grid(row=0, column=0, sticky="ew")
        self.header_canvas.bind(
            "<Configure>",
            lambda e: setattr(self, "_hw", max(400, e.width)))
        # keep self.canvas as an alias for backward references
        self.canvas = self.header_canvas

        # ── CHAT AREA ──
        self.chat = ctk.CTkScrollableFrame(
            self, fg_color="#060616",
            scrollbar_button_color="#0a1628",
            scrollbar_button_hover_color="#00d4ff")
        self.chat.grid(row=1, column=0, sticky="nsew", padx=14, pady=(2, 4))

        # ── BOTTOM PANEL ──
        bot = ctk.CTkFrame(self, fg_color="#070718", corner_radius=0,
                            border_width=1, border_color="#122044")
        bot.grid(row=2, column=0, sticky="ew")
        bot.grid_columnconfigure(0, weight=1)

        # Row 1 - Voice + Mode
        r1 = ctk.CTkFrame(bot, fg_color="transparent")
        r1.grid(row=0, column=0, sticky="ew", padx=26, pady=(12, 4))

        ctk.CTkLabel(r1, text="VOICE", text_color="#3d6699",
                     font=("Courier New", 12, "bold")).pack(side="left")

        voice_names = list(self.voices_map.keys()) or ["No voices found"]
        current_name = next(
            (n for n, i in self.voices_map.items() if i == self.selected_voice_id),
            voice_names[0]
        )
        self.voice_var = ctk.StringVar(value=current_name)
        self.voice_menu = ctk.CTkOptionMenu(
            r1, values=voice_names, variable=self.voice_var,
            command=self._save_voice, width=230, height=34, corner_radius=17,
            fg_color="#0a1628", button_color="#12225a",
            button_hover_color="#00d4ff",
            font=("Arial", 12))
        self.voice_menu.pack(side="left", padx=10)

        ctk.CTkButton(r1, text="TEST", width=60, height=34, corner_radius=17,
                      fg_color="#12225a", hover_color="#00d4ff",
                      font=("Courier New", 11, "bold"),
                      command=self._test_voice).pack(side="left", padx=4)

        ctk.CTkLabel(r1, text="   MODE", text_color="#3d6699",
                     font=("Courier New", 12, "bold")).pack(side="left", padx=(12, 0))

        self.mode_btn = ctk.CTkButton(
            r1, text="⌨  TYPE", width=110, height=34, corner_radius=17,
            fg_color="#334466", hover_color="#0040ff",
            font=("Arial", 13, "bold"),
            command=self._toggle_mode)
        self.mode_btn.pack(side="left", padx=10)

        # Row 2 - Speed and language
        r2 = ctk.CTkFrame(bot, fg_color="transparent")
        r2.grid(row=1, column=0, sticky="ew", padx=26, pady=4)

        ctk.CTkLabel(r2, text="SPEED", text_color="#3d6699",
                     font=("Courier New", 12, "bold")).pack(side="left")

        self.rslider = ctk.CTkSlider(
            r2, from_=100, to=220, width=240,
            button_color="#00d4ff", progress_color="#0040ff",
            command=self._save_rate)
        self.rslider.set(self.speech_rate)
        self.rslider.pack(side="left", padx=12)

        ctk.CTkLabel(r2, text="   LANG", text_color="#3d6699",
                     font=("Courier New", 12, "bold")).pack(side="left", padx=(12, 0))

        self.lang_var = ctk.StringVar(value="English (en-US)")
        ctk.CTkOptionMenu(
            r2,
            values=["English (en-US)", "Hindi (hi-IN)", "Marathi (mr-IN)",
                    "Hinglish (en-IN)"],
            variable=self.lang_var, width=180, height=34, corner_radius=17,
            fg_color="#0a1628", button_color="#12225a",
            font=("Arial", 12)).pack(side="left", padx=10)

        # Reply banner (hidden until the user replies to a message)
        self.reply_bar = ctk.CTkFrame(bot, fg_color="#0c1a3a", corner_radius=12,
                                      border_width=1, border_color="#12326a")
        self.reply_bar.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(self.reply_bar, text="↩", text_color="#00d4ff",
                     font=("Arial", 16, "bold")).grid(row=0, column=0,
                                                      padx=(14, 8), pady=8)
        self.reply_lbl = ctk.CTkLabel(self.reply_bar, text="", anchor="w",
                                      justify="left", text_color="#9fe4ff",
                                      font=("Arial", 11))
        self.reply_lbl.grid(row=0, column=1, sticky="w", pady=8)
        ctk.CTkButton(self.reply_bar, text="✕", width=30, height=30,
                      corner_radius=15, fg_color="#12225a",
                      hover_color="#ff2244", font=("Arial", 13, "bold"),
                      command=self._clear_reply).grid(row=0, column=2,
                                                      padx=(8, 12), pady=6)
        # shown/hidden via grid in _set_reply / _clear_reply

        # Row 3 - Input bar
        r3 = ctk.CTkFrame(bot, fg_color="transparent")
        r3.grid(row=3, column=0, sticky="ew", padx=22, pady=(8, 16))
        r3.grid_columnconfigure(0, weight=1)

        self.entry = ctk.CTkEntry(
            r3,
            placeholder_text="  Message NYX...",
            height=54, font=("Arial", 15),
            fg_color="#0a1628", border_color="#12326a",
            border_width=2, text_color="#c8e6ff",
            placeholder_text_color="#3d6699", corner_radius=27)
        self.entry.grid(row=0, column=0, sticky="ew", padx=(0, 12))
        self.entry.bind("<Return>", lambda e: self._send())
        # Cyan border on focus
        self.entry.bind("<FocusIn>",
                        lambda e: self.entry.configure(border_color="#00d4ff"))
        self.entry.bind("<FocusOut>",
                        lambda e: self.entry.configure(border_color="#12326a"))

        bf = ctk.CTkFrame(r3, fg_color="transparent")
        bf.grid(row=0, column=1)

        self._mic_btn = None
        for i, (txt, fg, hov, cmd) in enumerate([
            ("➤",  "#0040ff", "#0066ff", self._send),
            ("🎙", "#0a1628", "#ff2244", self._mic),
            ("🗑", "#0a1628", "#440011", self._clear),
            ("⚙",  "#0a1628", "#334466", self._settings),
        ]):
            b = ctk.CTkButton(
                bf, text=txt, width=54, height=54,
                corner_radius=27, fg_color=fg,
                hover_color=hov, border_width=1,
                border_color="#12326a",
                font=("Arial", 20), command=cmd)
            b.pack(side="left", padx=4)
            if i == 1:
                self._mic_btn = b

        # Disable mic in TYPE mode
        if self.input_mode == "TYPE":
            self._mic_btn.configure(state="disabled", fg_color="#111")

        # ── ANIMATED LIGHT STREAKS (bottom) ──
        self.streak_canvas = tk.Canvas(self, height=44, bg=BG,
                                       highlightthickness=0, bd=0)
        self.streak_canvas.grid(row=3, column=0, sticky="ew")
        self.streak_canvas.bind(
            "<Configure>",
            lambda e: setattr(self, "_sw", max(400, e.width)))
        self._sw = 1200

    # ── VOICE CONTROLS ────────────────────────────────────────────────────────
    def _save_voice(self, choice):
        if choice in self.voices_map:
            self.selected_voice_id          = self.voices_map[choice]
            self.mem.profile["voice_id"]    = self.selected_voice_id
            self.mem.profile["voice_name"]  = choice
            self.mem.save_profile()

    def _save_rate(self, v):
        self.speech_rate            = int(v)
        self.mem.profile["rate"]    = self.speech_rate
        self.mem.save_profile()

    def _test_voice(self):
        self._speak_safe("Testing voice Boss. All systems nominal.")

    def _toggle_mode(self):
        if self.input_mode == "TYPE":
            self.input_mode = "VOICE"
            self.mode_btn.configure(text="🎙  VOICE", fg_color="#0040ff")
            self._mic_btn.configure(state="normal", fg_color="#0a1628")
        else:
            self.input_mode = "TYPE"
            self.mode_btn.configure(text="⌨  TYPE", fg_color="#334466")
            self._mic_btn.configure(state="disabled", fg_color="#111")
            self.stop_flag = True

    def _clear(self):
        for w in self.chat.winfo_children():
            w.destroy()

    # ── LOGO / HEADER ANIMATION ───────────────────────────────────────────────
    def _logo_init(self):
        self._ao = self._am = self._ai = 0.0
        self._pulse = 0.0
        self._pdir  = 1
        self._frame = 0
        # Pre-compute a layered starfield (fractions so it scales with width).
        # Brighter, sparser "hero" stars sit on top of a dim dust layer.
        self._stars = []
        for _ in range(150):
            bright = random.random() < 0.18
            self._stars.append((
                random.random(),                     # x fraction
                random.random(),                     # y fraction
                2 if bright else random.choice([1, 1, 1, 2]),
                random.choice(["#3a6fd8", "#4f8fff", "#66c2ff"]) if bright
                    else random.choice(["#16305c", "#1d3f75", "#24507f", "#2a2f66"]),
                random.uniform(0, 6.28),             # twinkle phase
                bright,
            ))
        # Shooting star + energy-pulse-wave state
        self._shoot = None       # dict: x, y, vx, vy, life
        self._pulses = []        # expanding energy rings [radius, ...]
        self._streak_off = 0.0
        self._logo()
        self._streaks()

    @staticmethod
    def _mix(c1, c2, t):
        """Blend two #rrggbb colors, t in 0..1."""
        a = tuple(int(c1[i:i+2], 16) for i in (1, 3, 5))
        b = tuple(int(c2[i:i+2], 16) for i in (1, 3, 5))
        m = tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))
        return f"#{m[0]:02x}{m[1]:02x}{m[2]:02x}"

    def _logo(self):
        cv = self.header_canvas
        cv.delete("all")
        W   = self._hw
        cx  = W // 2
        cy  = 114             # reactor center Y
        s   = self.jstate
        BG  = "#050515"

        if s == "LISTENING":
            col = "#00d4ff"; ring = "#0a3a52"; accent = "#66f2ff"; spin = 4; pr = 3
        elif s == "THINKING":
            col = "#b15cff"; ring = "#2a1240"; accent = "#e392ff"; spin = 5; pr = 2.5
        elif s == "SPEAKING":
            col = "#32ffda"; ring = "#0d3a30"; accent = "#8dfff8"; spin = 3.5; pr = 4
        else:
            col = "#4f9fff"; ring = "#0f2a52"; accent = "#80c2ff"; spin = 0.9; pr = 1

        self._ao    += spin
        self._frame += 1
        self._pulse += self._pdir * pr
        if self._pulse > 10: self._pdir = -1
        if self._pulse < 0:  self._pdir = 1
        breathe = 0.5 + 0.5 * math.sin(self._frame * 0.06)   # 0..1 slow pulse

        # ── Layered starfield with twinkle + glow on hero stars ──
        for (xf, yf, r, sc, ph, bright) in self._stars:
            x = xf * W
            y = yf * 362
            tw = 0.35 + 0.65 * (0.5 + 0.5 * math.sin(self._frame * 0.05 + ph))
            fc = self._mix(BG, sc, tw)
            if bright:
                gc = self._mix(BG, sc, tw * 0.35)
                cv.create_oval(x-r-2, y-r-2, x+r+2, y+r+2, fill=gc, outline="")
                if tw > 0.85:   # sparkle cross
                    cv.create_line(x-4, y, x+4, y, fill=fc)
                    cv.create_line(x, y-4, x, y+4, fill=fc)
            cv.create_oval(x-r, y-r, x+r, y+r, fill=fc, outline="")

        # ── Shooting star (occasional) ──
        if self._shoot is None and self._frame % 130 == 0:
            self._shoot = {
                "x": random.uniform(W*0.1, W*0.6), "y": random.uniform(20, 90),
                "vx": random.uniform(9, 14), "vy": random.uniform(2.5, 5), "life": 26,
            }
        if self._shoot:
            sh = self._shoot
            for t in range(8):
                x0 = sh["x"] - sh["vx"] * t
                y0 = sh["y"] - sh["vy"] * t
                cc = self._mix(BG, "#bfe6ff", 0.9 * (1 - t / 8))
                cv.create_line(x0, y0, x0 - sh["vx"], y0 - sh["vy"], fill=cc, width=2)
            sh["x"] += sh["vx"]; sh["y"] += sh["vy"]; sh["life"] -= 1
            if sh["life"] <= 0 or sh["x"] > W:
                self._shoot = None

        outer = 98 + self._pulse * 0.55
        mid   = 72
        core  = 44

        # ── Multi-layer radial bloom behind the reactor ──
        for i in range(16, 0, -1):
            gr = 46 + i * 8
            t  = i / 16.0
            gc = self._mix(BG, col, (0.20 * (1 - t) ** 2) + 0.015 + 0.05 * breathe * (1 - t))
            cv.create_oval(cx-gr, cy-gr, cx+gr, cy+gr, fill="", outline=gc, width=5)

        # ── Expanding energy pulse waves ──
        if self._frame % 22 == 0:
            self._pulses.append(core + 6)
        nxt = []
        for pr_ in self._pulses:
            pr_ += 2.4
            if pr_ < outer + 22:
                fade = 1 - (pr_ - core) / (outer + 22 - core)
                pc = self._mix(BG, accent, 0.5 * max(0, fade))
                cv.create_oval(cx-pr_, cy-pr_, cx+pr_, cy+pr_, outline=pc, width=2)
                nxt.append(pr_)
        self._pulses = nxt

        # ── Outer HUD tick ring (many small radial ticks) ──
        for i in range(60):
            a = math.radians(i * 6 + self._ao * 0.4)
            r1 = outer + 16
            r2 = outer + (26 if i % 5 == 0 else 21)
            tc = col if i % 5 == 0 else ring
            cv.create_line(cx + r1*math.cos(a), cy + r1*math.sin(a),
                           cx + r2*math.cos(a), cy + r2*math.sin(a),
                           fill=tc, width=2 if i % 5 == 0 else 1)

        # ── Concentric rings ──
        cv.create_oval(cx-outer-13, cy-outer-13, cx+outer+13, cy+outer+13,
                       outline=ring, width=1)
        cv.create_oval(cx-outer, cy-outer, cx+outer, cy+outer, outline=col, width=3)
        cv.create_oval(cx-outer+6, cy-outer+6, cx+outer-6, cy+outer-6,
                       outline=ring, width=1)

        # Glowing rotating arc segments (draw a wide faint glow, bright arc on top)
        for i, (start, extent) in enumerate([(6, 104), (150, 74), (250, 92)]):
            a0 = start + self._ao * (1 if i % 2 == 0 else -1)
            cv.create_arc(cx-outer, cy-outer, cx+outer, cy+outer,
                          start=a0, extent=extent, style="arc",
                          outline=self._mix(BG, accent, 0.35), width=8)
            cv.create_arc(cx-outer+2, cy-outer+2, cx+outer-2, cy+outer-2,
                          start=a0, extent=extent, style="arc",
                          outline=accent, width=3)

        # Counter-rotating middle ring segments
        mr = mid + 16
        for i in range(3):
            cv.create_arc(cx-mr, cy-mr, cx+mr, cy+mr,
                          start=i * 120 - self._ao * 1.5, extent=48,
                          style="arc", outline=col, width=2)

        # ── Orbiting energy particles with trails ──
        for i in range(6):
            base = i * 60 + self._ao * 0.9
            for t in range(6):
                a = math.radians(base - t * 5)
                x = cx + mid * math.cos(a); y = cy + mid * math.sin(a)
                tc = self._mix(BG, accent, 0.85 * (1 - t / 6))
                rr = 4 - t * 0.5
                if rr > 0:
                    cv.create_oval(x-rr, y-rr, x+rr, y+rr, fill=tc, outline="")

        # Rotating spokes
        for i in range(6):
            a = math.radians(i * 60 - self._ao * 0.6)
            cv.create_line(cx + core*math.cos(a), cy + core*math.sin(a),
                           cx + (mid-6)*math.cos(a), cy + (mid-6)*math.sin(a),
                           fill=ring, width=1)

        # ── Pulsing energy core (gradient fill) ──
        for i in range(core, 0, -3):
            t  = i / core
            fc = self._mix("#020a16", col, (1 - t) * (0.30 + 0.20 * breathe))
            cv.create_oval(cx-i, cy-i, cx+i, cy+i, fill=fc, outline="")
        cv.create_oval(cx-core, cy-core, cx+core, cy+core, outline=col, width=2)
        cv.create_oval(cx-core-2, cy-core-2, cx+core+2, cy+core+2,
                       outline=self._mix(BG, col, 0.4 + 0.3*breathe), width=1)

        # Glowing NYX wordmark (halo underneath, crisp white on top)
        cv.create_text(cx, cy, text="NYX",
                       font=("Courier New", 31, "bold"),
                       fill=self._mix(BG, accent, 0.55 + 0.3*breathe))
        cv.create_text(cx, cy, text="NYX",
                       font=("Courier New", 30, "bold"), fill="#ffffff")

        if s == "SPEAKING":
            for i in range(4):
                r = core + 14 + i * 11 + (self._pulse * 0.3)
                cv.create_oval(cx-r, cy-r, cx+r, cy+r,
                               outline=accent, width=1)

        # ── Title + subtitle ──
        cv.create_text(cx, cy + outer + 30, text="NYX",
                       font=("Courier New", 34, "bold"), fill="#00d4ff")
        cv.create_text(cx, cy + outer + 56, text="ADVANCED AI ASSISTANT  v1.0",
                       font=("Courier New", 11), fill="#3d6699")

        # ── Status pill (full-width, gradient dark-blue, cyan border) ──
        py   = 310
        px0  = 24
        px1  = W - 24
        ph   = 44
        self._round_rect(cv, px0, py, px1, py + ph, 22,
                         fill="#081030", outline="#00d4ff", width=1)
        # subtle inner gradient bands
        for i in range(3):
            self._round_rect(cv, px0+3, py+3+i, px1-3, py+ph-3, 20,
                             fill="", outline=self._mix("#081030", "#12326a", 0.4-i*0.12),
                             width=1)

        dcol = self._jcol
        cv.create_oval(px0+22, py+ph//2-6, px0+34, py+ph//2+6,
                       fill=dcol, outline=accent, width=1)
        cv.create_text(px0+48, py+ph//2, anchor="w", text=self._jdisp,
                       font=("Courier New", 13, "bold"), fill=dcol)

        # center: mode
        mode_txt = "[ VOICE MODE ]" if self.input_mode == "VOICE" else "[ TYPE MODE ]"
        mode_col = "#00d4ff" if self.input_mode == "VOICE" else "#6699cc"
        cv.create_text(cx, py+ph//2, text=mode_txt,
                       font=("Courier New", 12, "bold"), fill=mode_col)

        # right: WAKE READY (green when voice mode on)
        if self.input_mode == "VOICE" and self.mem.profile.get("wake", True):
            wtxt = "WAKE ACTIVE" if s == "LISTENING" else "WAKE READY"
            cv.create_text(px1-24, py+ph//2, anchor="e", text=wtxt,
                           font=("Courier New", 11, "bold"), fill="#33ff99")

        cv.after(30, self._logo)

    @staticmethod
    def _round_rect(cv, x0, y0, x1, y1, r, **kw):
        """Draw a rounded rectangle polygon on a canvas."""
        pts = [
            x0+r, y0, x1-r, y0, x1, y0, x1, y0+r, x1, y1-r, x1, y1,
            x1-r, y1, x0+r, y1, x0, y1, x0, y1-r, x0, y0+r, x0, y0,
        ]
        return cv.create_polygon(pts, smooth=True, **kw)

    # ── ANIMATED LIGHT STREAKS (flowing light comets) ─────────────────────────
    def _streaks(self):
        cv = self.streak_canvas
        cv.delete("all")
        W  = self._sw
        BG = "#050515"
        self._streak_off += 7.0
        # each lane: baseline y, color, speed, how many comets across the width
        lanes = [
            (11, "#00d4ff", 1.30, 2),
            (20, "#2a6bff", 0.95, 3),
            (29, "#00e6b4", 0.70, 2),
            (37, "#20408c", 0.50, 3),
        ]
        span = W + 260
        for li, (y, colr, speed, n) in enumerate(lanes):
            # faint continuous baseline
            cv.create_line(0, y, W, y, fill=self._mix(BG, colr, 0.10), width=1)
            for k in range(n):
                head = (self._streak_off * speed + li * 90 + k * (span / n)) % span - 130
                tail = 130
                steps = 14
                for s in range(steps):
                    t   = s / steps
                    x0  = head - tail * t
                    x1  = head - tail * (t + 1.0 / steps)
                    if x1 > W or x0 < 0:
                        continue
                    # bright head fading to nothing along the tail
                    col = self._mix(BG, colr, 0.95 * (1 - t) ** 1.6)
                    cv.create_line(x0, y, x1, y, fill=col, width=2)
        cv.after(40, self._streaks)

    # ── STATE MANAGEMENT ──────────────────────────────────────────────────────
    def set_jstate(self, s):
        """ALWAYS use set_jstate, NEVER self.state.
        Stores display text/color; the header canvas renders them each frame."""
        self.jstate = s
        cfg = {
            "SLEEPING":     ("SLEEPING",     "#4f9fff"),
            "LISTENING":    ("LISTENING",    "#00ff9d"),
            "THINKING":     ("THINKING...",  "#ff9900"),
            "SPEAKING":     ("SPEAKING",     "#00d4ff"),
            "INITIALIZING": ("INITIALIZING", "#ffffff"),
        }
        t, c = cfg.get(s, ("SLEEPING", "#4f9fff"))
        self._jdisp = t
        self._jcol  = c

    # ── ADDRESS SANITISER ─────────────────────────────────────────────────────
    @staticmethod
    def _deboss(text):
        """The user dislikes being called 'Boss' — strip that form of address
        from every outgoing (displayed + spoken) string, tidying punctuation."""
        if not text:
            return text
        # Remove "Boss" as a form of address, with any leading comma/space.
        text = re.sub(r"[,\s]*\bBoss\b", "", text, flags=re.IGNORECASE)
        # Tidy up: no space before punctuation, collapse double spaces,
        # and drop any punctuation left stranded at the very start.
        text = re.sub(r"\s+([.!?,])", r"\1", text)
        text = re.sub(r"\s{2,}", " ", text)
        text = re.sub(r"^[\s,!?.]+", "", text)
        return text.strip()

    # ── REPLY-TO-MESSAGE ──────────────────────────────────────────────────────
    def _set_reply(self, text):
        """Start replying to a specific message — show the quote banner."""
        text = (text or "").strip()
        if not text:
            return
        self._reply_to = text
        snippet = text if len(text) <= 90 else text[:87] + "..."
        self.reply_lbl.configure(text=f"Replying to:  {snippet}")
        self.reply_bar.grid(row=2, column=0, sticky="ew", padx=22, pady=(6, 0))
        try:
            self.entry.focus_set()
        except Exception:
            pass

    def _clear_reply(self):
        self._reply_to = None
        try:
            self.reply_bar.grid_remove()
        except Exception:
            pass

    # ── CHAT BUBBLES ──────────────────────────────────────────────────────────
    def _link_chip(self, parent, url, anchor, on_dark=True):
        """Add a clickable underlined link label that opens the URL in a browser."""
        disp = url.replace("https://", "").replace("http://", "").rstrip("/")
        if len(disp) > 50:
            disp = disp[:47] + "..."
        col  = "#5ab0ff" if on_dark else "#dbe9ff"
        lk = ctk.CTkLabel(parent, text="🔗 " + disp, text_color=col,
                          cursor="hand2", justify="left", wraplength=560,
                          font=("Arial", 11, "underline"))
        lk.pack(anchor=anchor, pady=(3, 0))
        lk.bind("<Button-1>", lambda e, u=url: webbrowser.open(u))
        return lk

    @staticmethod
    def _is_tabular(text):
        """True if the text is a table / multi-line list whose layout matters."""
        return ("\n" in text.strip()) or (text.count("|") >= 3)

    @staticmethod
    def _clean_multiline(text):
        """Normalise a table/list for display, PRESERVING newlines, column
        spacing AND non-ASCII (Devanagari, symbols)."""
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        lines = [ln.rstrip() for ln in text.split("\n")]
        while lines and not lines[0].strip():
            lines.pop(0)
        while lines and not lines[-1].strip():
            lines.pop()
        return "\n".join(lines)

    def _quote_box(self, parent, quoted, bg, fg):
        """A small quoted-message preview shown at the top of a reply bubble."""
        q = quoted.strip().replace("\n", " ")
        if len(q) > 120:
            q = q[:117] + "..."
        box = ctk.CTkFrame(parent, fg_color=bg, corner_radius=8)
        box.pack(anchor="w", fill="x", pady=(0, 6))
        strip = ctk.CTkFrame(box, fg_color="#00d4ff", width=3, corner_radius=3)
        strip.pack(side="left", fill="y", padx=(0, 6), pady=2)
        ctk.CTkLabel(box, text=q, text_color=fg, justify="left",
                     wraplength=440, font=("Arial", 10)).pack(
                         side="left", anchor="w", padx=(0, 8), pady=4)

    def _reply_btn(self, parent, quoted, anchor, on_dark=True):
        """Small '↩ Reply' action that quotes this message for a follow-up."""
        col = "#6f9fd0" if on_dark else "#c8d8ff"
        lk = ctk.CTkLabel(parent, text="↩ Reply", text_color=col, cursor="hand2",
                          font=("Arial", 10))
        lk.pack(anchor=anchor, pady=(2, 0))
        lk.bind("<Button-1>", lambda e, q=quoted: self._set_reply(q))
        return lk

    def _bubble(self, text, user=False, link=None, quote=None):
        raw_for_reply = text   # keep original text for the reply feature
        # Render any LaTeX-style math (\(a^{2}+b^{2}=c^{2}\) -> a²+b²=c²).
        text = format_math(text)
        # Devanagari (Hindi/Marathi) must NOT be ascii-stripped or it vanishes.
        has_dev = any('ऀ' <= ch <= 'ॿ' for ch in text)
        tabular = self._is_tabular(text)
        if tabular:
            text = self._clean_multiline(text)
            if not user:   # strip "Boss" without collapsing the table's spacing
                text = re.sub(r"[,]?\s?\bBoss\b", "", text, flags=re.IGNORECASE)
        elif has_dev:
            # Preserve the Devanagari script; just tidy whitespace + drop "Boss".
            text = re.sub(r"\s+", " ", text).strip()
            if not user:
                text = re.sub(r"[,]?\s?\bBoss\b", "", text, flags=re.IGNORECASE).strip()
        else:
            # display_clean preserves unicode math symbols (², √, π, ×) instead
            # of stripping them like ascii_clean would.
            text = display_clean(text)
            if not user:
                text = self._deboss(text)
        if not text:
            return

        body_font = ("Consolas", 12) if tabular else ("Arial", 14)
        wrap      = 1000 if tabular else 560

        # Auto-detect any URLs written inside the text itself.
        urls = re.findall(r"https?://[^\s)>\]\"']+", text)
        if link and link not in urls:
            urls = [link] + urls

        outer = ctk.CTkFrame(self.chat, fg_color="transparent")
        outer.pack(fill="x", pady=5, padx=10)
        ts = datetime.datetime.now().strftime("%H:%M")

        if user:
            # Right-aligned blue-purple bubble, white text, timestamp + ✓✓
            b = ctk.CTkFrame(outer, fg_color="#1f3fae", corner_radius=20,
                             border_width=1, border_color="#2a54cc")
            b.pack(side="right", padx=6, ipadx=15, ipady=9)
            if quote:   # quoted message this reply refers to
                self._quote_box(b, quote, "#2a4fc0", "#bcd0ff")
            ctk.CTkLabel(b, text=text, text_color="#ffffff",
                         justify="left", wraplength=wrap,
                         font=body_font).pack(anchor="w")
            for u in urls[:3]:
                self._link_chip(b, u, "w", on_dark=False)
            meta = ctk.CTkFrame(b, fg_color="transparent")
            meta.pack(anchor="e")
            ctk.CTkLabel(meta, text=ts, text_color="#b8ccff",
                         font=("Arial", 9)).pack(side="left", padx=(0, 4))
            ctk.CTkLabel(meta, text="✓✓", text_color="#7fe0ff",
                         font=("Arial", 10, "bold")).pack(side="left")
            self._reply_btn(b, raw_for_reply, "e", on_dark=False)
        else:
            row = ctk.CTkFrame(outer, fg_color="transparent")
            row.pack(side="left", padx=4)
            # Cyan "N" avatar circle
            ctk.CTkLabel(row, text="N", width=40, height=40,
                         fg_color="#00d4ff", corner_radius=20,
                         font=("Courier New", 17, "bold"),
                         text_color="#04121f").pack(side="left",
                                                    anchor="n", padx=(0, 9), pady=2)
            # Wrapper keeps the cyan left-border the SAME height as the bubble
            wrap_f = ctk.CTkFrame(row, fg_color="transparent")
            wrap_f.pack(side="left")
            edge = ctk.CTkFrame(wrap_f, fg_color="#00d4ff", corner_radius=3, width=3)
            edge.pack(side="left", fill="y")
            b = ctk.CTkFrame(wrap_f, fg_color="#0a1628", corner_radius=18)
            b.pack(side="left", ipadx=15, ipady=9)
            if quote:
                self._quote_box(b, quote, "#122a4a", "#7fb0e0")
            body_lbl = ctk.CTkLabel(b, text=text, text_color="#9fe4ff",
                                    justify="left", wraplength=wrap,
                                    font=body_font)
            body_lbl.pack(anchor="w")
            for u in urls[:3]:
                self._link_chip(b, u, "w", on_dark=True)
            ts_lbl = ctk.CTkLabel(b, text=ts, text_color="#2c5578",
                                  font=("Arial", 9))
            ts_lbl.pack(anchor="w")
            self._reply_btn(b, raw_for_reply, "w", on_dark=True)
            self._last_nyx_bubble = (body_lbl, ts_lbl)

        self.update_idletasks()
        try:
            self.chat._parent_canvas.yview_moveto(1.0)
        except:
            pass

    # ── IMAGE GENERATION ──────────────────────────────────────────────────────
    def _provide_image(self, subject):
        """Generate an image of `subject` (Pollinations, free, no key) and show
        it inline. The file is kept only in TEMP — the user chooses whether to
        save it. Falls back to a web image search on failure."""
        self.Q.put(("jstate", ("THINKING",)))
        self._say(f"Generating an image of {subject}. One moment.")
        try:
            import tempfile
            url = ("https://image.pollinations.ai/prompt/"
                   + urllib.parse.quote(subject)
                   + "?width=768&height=512&nologo=true")
            r = requests.get(url, timeout=45,
                             headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200 and r.content and len(r.content) > 2000:
                fn = os.path.join(tempfile.gettempdir(),
                                  f"nyx_image_{int(time.time())}.png")
                with open(fn, "wb") as f:
                    f.write(r.content)
                self.Q.put(("image", (fn, subject)))
                return
            print(f"Image gen HTTP {r.status_code}, size {len(r.content)}")
        except Exception as e:
            print(f"Image gen error: {e}")
        self._fallback_image_search(subject)

    def _fallback_image_search(self, subject):
        url = "https://www.google.com/search?tbm=isch&q=" + urllib.parse.quote(subject)
        self._say(f"Here are images of {subject} from the web.", link=url)
        webbrowser.open(url)

    def _save_image(self, path, caption="image"):
        """Copy a (temp) generated image to the desktop on the user's request."""
        if not path or not os.path.exists(path):
            self._say("There is no image to save. Ask me to generate one first.")
            return
        import shutil
        safe = re.sub(r"[^\w\- ]", "", caption).strip().replace(" ", "_")[:40] or "image"
        dest = os.path.join(self._desktop_dir(), f"nyx_{safe}_{int(time.time())}.png")
        try:
            shutil.copy(path, dest)
            self._say(f"Saved the image to your desktop as {os.path.basename(dest)}.")
        except Exception as e:
            print(f"Save image error: {e}")
            self._say("Could not save the image.")

    def _image_bubble(self, path, caption):
        """Render a generated image as a NYX chat bubble (runs on main thread)."""
        try:
            pil = Image.open(path)
            w, h = pil.size
            maxw = 460
            if w > maxw:
                h = int(h * maxw / w); w = maxw
            ctkimg = ctk.CTkImage(light_image=pil, dark_image=pil, size=(w, h))
        except Exception as e:
            print(f"Image display error: {e}")
            self._say(f"I saved the image to your desktop, but could not display it.")
            return

        # keep a reference so the image isn't garbage-collected
        self._img_refs = getattr(self, "_img_refs", [])
        self._img_refs.append(ctkimg)
        # remember the latest image for the "save it" voice/text command
        self._last_image = path
        self._last_image_caption = caption

        outer = ctk.CTkFrame(self.chat, fg_color="transparent")
        outer.pack(fill="x", pady=5, padx=10)
        row = ctk.CTkFrame(outer, fg_color="transparent")
        row.pack(side="left", padx=4)
        ctk.CTkLabel(row, text="N", width=40, height=40,
                     fg_color="#00d4ff", corner_radius=20,
                     font=("Courier New", 17, "bold"),
                     text_color="#04121f").pack(side="left", anchor="n",
                                                padx=(0, 9), pady=2)
        b = ctk.CTkFrame(row, fg_color="#0a1628", corner_radius=18)
        b.pack(side="left", ipadx=10, ipady=10)
        ctk.CTkLabel(b, text=f"Image of {caption}", text_color="#9fe4ff",
                     font=("Arial", 12, "bold")).pack(anchor="w", pady=(0, 6))
        ctk.CTkLabel(b, image=ctkimg, text="").pack()

        # Save / Open actions (image is NOT saved unless you choose to).
        actions = ctk.CTkFrame(b, fg_color="transparent")
        actions.pack(anchor="w", pady=(8, 0))
        save_lbl = ctk.CTkLabel(actions, text="💾 Save to desktop",
                                text_color="#33ff99", cursor="hand2",
                                font=("Arial", 11, "underline"))
        save_lbl.pack(side="left", padx=(0, 16))
        save_lbl.bind("<Button-1>",
                      lambda e, p=path, c=caption: self._save_image(p, c))
        open_lbl = ctk.CTkLabel(actions, text="🔍 Open", text_color="#5ab0ff",
                                cursor="hand2", font=("Arial", 11, "underline"))
        open_lbl.pack(side="left")
        open_lbl.bind("<Button-1>", lambda e, p=path: os.startfile(p))

        self.update_idletasks()
        try:
            self.chat._parent_canvas.yview_moveto(1.0)
        except Exception:
            pass
        self.Q.put(("speak",
                    (f"Here is the image of {caption}. Click save or say save it "
                     f"to keep it.", "en")))

    def _show_think(self):
        outer = ctk.CTkFrame(self.chat, fg_color="transparent")
        outer.pack(fill="x", pady=4, padx=6)
        row = ctk.CTkFrame(outer, fg_color="transparent")
        row.pack(side="left", padx=6)
        ctk.CTkLabel(row, text="N", width=38, height=38,
                     fg_color="#ff9900", corner_radius=19,
                     font=("Courier New", 16, "bold"),
                     text_color="#050510").pack(side="left",
                                               anchor="n", padx=(0, 8), pady=3)
        b = ctk.CTkFrame(row, fg_color="#080f22", corner_radius=22,
                          border_width=1, border_color="#ff9900")
        b.pack(side="left", ipadx=14, ipady=8)
        ctk.CTkLabel(b, text="Thinking...", text_color="#ff9900",
                     font=("Courier New", 13)).pack()
        self.think_wid = outer
        self.update_idletasks()
        try:
            self.chat._parent_canvas.yview_moveto(1.0)
        except:
            pass

    def _hide_think(self):
        try:
            if self.think_wid:
                self.think_wid.destroy()
                self.think_wid = None
        except:
            pass

    # ── QUEUE PROCESSING ──────────────────────────────────────────────────────
    def _process(self):
        try:
            while True:
                task, args = self.Q.get_nowait()
                if task == "bubble":    self._bubble(*args)
                elif task == "greet_bubble":
                    # Startup greeting: remember its widgets so the greeting can
                    # be refreshed when the part of day changes (see below).
                    self._last_nyx_bubble = None
                    self._bubble(*args)
                    self._greet_widgets = self._last_nyx_bubble
                elif task == "speak":
                    # args = (text,) or (text, slang). _speak_safe serialises
                    # via the lock so only one voice plays at a time.
                    self._speak_safe(*args)
                elif task == "jstate":  self.set_jstate(args[0])
                elif task == "think":   self._show_think()
                elif task == "unthink": self._hide_think()
                elif task == "image":   self._image_bubble(*args)
        except queue.Empty:
            pass
        self._poll_visible()   # keep STT gated to when the window is shown
        self.after(55, self._process)
        if not getattr(self, "_greet_timer_on", False):
            self._greet_timer_on = True
            self.after(30000, self._refresh_greeting)

    def _refresh_greeting(self):
        """Keep the startup greeting truthful: if NYX has been open long enough
        for the part of day to change, rewrite that bubble (text + time) so a
        morning launch doesn't still say 'Good morning' in the afternoon."""
        try:
            g = get_day_greeting()
            w = getattr(self, "_greet_widgets", None)
            if w and g != getattr(self, "_greet_bubble_period", g):
                body, ts = w
                if body.winfo_exists():
                    nm = self.mem.profile.get("name", "").strip()
                    greet = f"{g} {nm}." if nm else f"{g}."
                    body.configure(text=f"{greet} Nyx is online. How may I assist you today?")
                    ts.configure(text=datetime.datetime.now().strftime("%H:%M"))
                self._greet_bubble_period = g
        except Exception as e:
            print(f"Greeting refresh: {e}")
        self.after(30000, self._refresh_greeting)

    # ── THREAD SAFE SPEAKING (English pyttsx3 + Hindi/Marathi gTTS) ────────────
    def _stop_speaking(self):
        """Interrupt whatever NYX is currently saying — immediately."""
        self.stop_flag = True
        eng = self._cur_engine
        if eng is not None:
            try:
                eng.stop()      # cuts the current pyttsx3 utterance (SAPI5)
            except Exception:
                pass
        alias = getattr(self, "_mci_alias", None)
        if alias:               # cuts the current gTTS/MCI playback
            try:
                from ctypes import windll
                windll.winmm.mciSendStringW(f"stop {alias}", None, 0, 0)
                windll.winmm.mciSendStringW(f"close {alias}", None, 0, 0)
            except Exception:
                pass

    def _speak_safe(self, text, slang="en"):
        if slang == "en":
            text = self._deboss(ascii_clean(text))
        else:   # Hindi / Marathi — keep Devanagari, just drop any "Boss"
            text = re.sub(r"[,]?\s?\bBoss\b", "", text, flags=re.IGNORECASE).strip()
        if not text:
            return
        # If already speaking, wait for the lock to free then speak.
        if self.speak_lock.locked():
            def _wait_and_speak():
                with self.speak_lock:
                    pass
                time.sleep(0.1)
                self._do_speak(text, slang)
            threading.Thread(target=_wait_and_speak, daemon=True).start()
            return
        self._do_speak(text, slang)

    def _do_speak(self, text, slang="en"):
        """Dispatch to the right engine in a locked worker thread."""
        def _run():
            with self.speak_lock:
                self.stop_flag = False
                self.Q.put(("jstate", ("SPEAKING",)))
                try:
                    if slang in ("hi", "mr") and GTTS_OK:
                        self._speak_indic_sync(text, slang)
                    else:
                        self._speak_en_sync(text)
                except Exception as e:
                    print(f"TTS error: {e}")
                finally:
                    self._cur_engine = None
                    self._mci_alias  = None
                    self.stop_flag   = False
                    self.Q.put(("jstate", ("SLEEPING",)))
        threading.Thread(target=_run, daemon=True).start()

    def _speak_en_sync(self, text):
        """English TTS via pyttsx3, sentence-by-sentence with a FRESH engine per
        sentence (avoids pyttsx3 cutting off on long text). Interruptible via
        stop_flag. Assumes the speak_lock is already held by the caller."""
        text = speak_math(text)   # a^{2} -> "a squared", etc. (no LaTeX read aloud)
        text = re.sub(r'\bN\.?Y\.?X\.?\b', 'Nyx', text, flags=re.IGNORECASE)
        text = re.sub(r'\bJ\.A\.R\.V\.I\.S\.?\b', 'Jarvis', text, flags=re.IGNORECASE)
        for pat in [r'\b([A-Z])\.([A-Z])\.([A-Z])\.([A-Z])\.([A-Z])\.([A-Z])\b',
                    r'\b([A-Z])\.([A-Z])\.([A-Z])\.([A-Z])\.([A-Z])\b',
                    r'\b([A-Z])\.([A-Z])\.([A-Z])\.([A-Z])\b',
                    r'\b([A-Z])\.([A-Z])\.([A-Z])\b',
                    r'\b([A-Z])\.([A-Z])\b']:
            text = re.sub(pat, lambda m: "".join(m.groups()), text)
        text = re.sub(r'https?://\S+', '', text)      # never speak URLs aloud
        text = re.sub(r'[*_#`|]', '', text)           # drop markdown symbols
        text = text.encode('ascii', 'ignore').decode('ascii').strip()
        if not text:
            return
        print(f"[NYX speaks] {text[:100]}...")
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
        for sent in sentences:
            if self.stop_flag:            # interrupted → stop now
                break
            try:
                eng = pyttsx3.init()      # FRESH engine per sentence
                self._cur_engine = eng
                if self.selected_voice_id:
                    eng.setProperty("voice", self.selected_voice_id)
                eng.setProperty("rate",   self.speech_rate)
                eng.setProperty("volume", 1.0)
                eng.say(sent)
                eng.runAndWait()
                try:
                    eng.stop()
                except Exception:
                    pass
                del eng
            except Exception as e:
                print(f"[TTS ERROR] {e}")

    def _speak_indic_sync(self, text, slang):
        """Hindi/Marathi TTS via gTTS → MP3 → Windows MCI playback, chunked so
        it can be interrupted. Falls back to an English note if offline."""
        import tempfile
        print(f"[NYX speaks {slang}] {text}")
        # Split on Devanagari danda (।) and western sentence enders.
        parts = [s.strip() for s in re.split(r'(?<=[।.!?])\s+', text) if s.strip()] \
            or [text]
        spoke = False
        for part in parts:
            if self.stop_flag:
                break
            fn = os.path.join(tempfile.gettempdir(),
                              f"nyx_tts_{int(time.time()*1000)}.mp3")
            try:
                gTTS(part, lang=slang).save(fn)
            except Exception as e:
                print(f"gTTS failed ({slang}): {e}")
                break
            if self.stop_flag:
                self._safe_remove(fn)
                break
            self._play_mp3(fn)
            spoke = True
            self._safe_remove(fn)
        if not spoke and not self.stop_flag:
            # Offline / synthesis failed — at least acknowledge in English.
            self._speak_en_sync("Here is your answer on screen.")

    def _play_mp3(self, path):
        """Play an MP3 via Windows MCI (no extra deps). Blocks until done or
        until _stop_speaking closes the alias."""
        from ctypes import windll, c_buffer
        alias = "nyxvoice"

        def mci(cmd):
            buf = c_buffer(256)
            windll.winmm.mciSendStringW(cmd, buf, 254, 0)
            return buf.value

        try:
            mci(f"close {alias}")
            self._mci_alias = alias
            if mci(f'open "{path}" type mpegvideo alias {alias}') is not None:
                pass
            mci(f"play {alias} wait")
        except Exception as e:
            print(f"MCI play error: {e}")
        finally:
            try:
                mci(f"close {alias}")
            except Exception:
                pass
            self._mci_alias = None

    @staticmethod
    def _safe_remove(path):
        try:
            os.remove(path)
        except Exception:
            pass

    # ── SAY / USER ────────────────────────────────────────────────────────────
    def _say(self, text, lang="en", link=None):
        if not text:
            return
        speak_text = text
        slang = "en"
        has_dev = any('\u0900' <= ch <= '\u097F' for ch in text)
        # Tables/lists: show the full grid but only SPEAK a short summary.
        if self._is_tabular(text):
            speak_text = ("Here is the information you asked for. "
                          "Please see the table on screen.")
        # Devanagari (Hindi / Marathi): speak it for real via gTTS.
        elif has_dev:
            speak_text = text                       # keep Devanagari for gTTS
            slang = "mr" if lang == "mr" else "hi"
        self.mem.add_history("nyx", text)
        self.Q.put(("unthink", ()))
        self.Q.put(("bubble",  (text, False, link)))
        self.Q.put(("speak",   (speak_text, slang)))

    def _user(self, text, quote=None):
        if not text:
            return
        self.mem.add_history("user", text)
        self.Q.put(("bubble", (text, True, None, quote)))
        self.Q.put(("think",  ()))

    # ── INPUT ─────────────────────────────────────────────────────────────────
    def _send(self):
        t = self.entry.get().strip()
        if t:
            self.entry.delete(0, tk.END)
            self._stop_speaking()   # interrupt any ongoing speech immediately
            reply = self._reply_to
            self._clear_reply()
            self._user(t, quote=reply)
            threading.Thread(target=self._cmd, args=(t,),
                             kwargs={"reply": reply}, daemon=True).start()

    def _mic(self):
        # While NYX is talking, the mic button doubles as an interrupt/stop.
        if self.jstate == "SPEAKING":
            self._stop_speaking()
            return
        if self.jstate in ["LISTENING", "THINKING"]:
            return
        if self.input_mode == "TYPE":
            return
        self._mic_btn.configure(fg_color="#ff2244", text="⏹")
        threading.Thread(target=self._mic_thread, daemon=True).start()

    def _mic_thread(self):
        self.Q.put(("jstate", ("LISTENING",)))
        lang = "en-US"
        lv   = self.lang_var.get()
        cmd_lang = "en"
        if "Hindi" in lv:
            lang = "hi-IN"
            cmd_lang = "hi"
        elif "Marathi" in lv:
            lang = "mr-IN"
            cmd_lang = "mr"
        elif "Hinglish" in lv:
            lang = "en-IN"
            cmd_lang = "hi"
        try:
            with sr.Microphone() as src:
                self.rec.adjust_for_ambient_noise(src, duration=0.8)
                audio = self.rec.listen(src, timeout=8,
                                        phrase_time_limit=self.phrase_time_limit)
            text = self.rec.recognize_google(audio, language=lang)
            # Remove wake words if present
            t = text.lower()
            for w in WAKE:
                if w in t:
                    t = t.split(w, 1)[-1].strip()
                    break
            if t:
                self._user(text)  # show original text in bubble
                self._cmd(text, lang=cmd_lang)
            else:
                self.Q.put(("jstate", ("SLEEPING",)))
        except sr.UnknownValueError:
            self._say("I did not catch that Boss. Could you repeat?")
        except sr.WaitTimeoutError:
            self.Q.put(("jstate", ("SLEEPING",)))
        except Exception as e:
            print(f"Mic error: {e}")
            self.Q.put(("jstate", ("SLEEPING",)))
        finally:
            self._mic_btn.configure(fg_color="#0a1628", text="🎙")

    # ── COMMAND HANDLER ───────────────────────────────────────────────────────
    def _cmd(self, raw, lang="en", reply=None):
        self.Q.put(("jstate", ("THINKING",)))
        # Pass any "reply to this message" context to the AI brain for this turn.
        self.brain.reply_ctx = reply
        c  = raw.lower().strip()
        c2 = re.sub(r"[^\w\s]", " ", c)
        nm = self.mem.profile.get("name", "") or "there"

        # Detect if input is Hindi (contains Hindi unicode chars)
        if any('\u0900' <= ch <= '\u097F' for ch in raw):
            lang = "hi"

        # Also check language selector
        try:
            lv = self.lang_var.get()
            if "Marathi" in lv:
                lang = "mr"
            elif "Hindi" in lv or "Hinglish" in lv:
                lang = "hi"
        except:
            pass

        def has(*words):
            return any(re.search(r"\b" + w.replace(" ", r"\s+") + r"\b", c2)
                       for w in words)

        # ── EXE/MSI SAFETY CONFIRMATION (answer a pending warning) ──
        if self.pending_exe:
            # Auto-expire after 30 seconds of no response.
            if time.time() - self._pending_exe_time > 30:
                self.pending_exe = None
            elif re.search(r"\b(yes|yeah|yep|sure|ok|okay|go ahead|"
                           r"confirm|do it|open it|proceed)\b", c2):
                filepath = self.pending_exe
                self.pending_exe = None
                self._say(f"Opening {os.path.basename(filepath)}.")
                try:
                    os.startfile(filepath)
                except Exception as e:
                    self._say(f"Could not open the file. Error: {str(e)[:50]}")
                return
            elif re.search(r"\b(no|nah|nope|cancel|stop|dont|don't|"
                           r"never mind|abort)\b", c2):
                self.pending_exe = None
                self._say("Cancelled. The file will not be opened.")
                return
            else:
                # Unrelated command → cancel the pending file and process normally.
                self.pending_exe = None

        # ── OPEN EXE/MSI FILE WITH SAFETY WARNING ──
        # Use `c` (keeps the dot) for the extension check — c2 strips punctuation.
        if re.search(r"\b(open|run|launch|execute|start)\b", c2) and \
           re.search(r"\.(exe|msi|bat|cmd|ps1|vbs|wsf|scr|com|pif)\b", c):

            filename = None
            match = re.search(
                r'([\w\s\-\.]+\.(exe|msi|bat|cmd|ps1|vbs|wsf|scr|com|pif))',
                c, re.IGNORECASE)
            if match:
                filename = match.group(1).strip()

            if filename:
                results = self.deep_file_search(filename, max_results=1)
                if results:
                    filepath    = results[0]
                    filesize_mb = round(os.path.getsize(filepath) / (1024 * 1024), 2)
                    file_ext    = os.path.splitext(filepath)[1].lower()
                    folder      = os.path.dirname(filepath)

                    high_risk_dirs = ["temp", "tmp", "appdata\\local\\temp",
                                      "downloads", "cache", "recycle"]
                    is_high_risk = any(d in folder.lower() for d in high_risk_dirs)
                    high_risk_exts = [".msi", ".bat", ".cmd", ".ps1",
                                      ".vbs", ".wsf", ".scr", ".com", ".pif"]
                    is_risky_ext = file_ext in high_risk_exts
                    known_safe_dirs = ["program files", "program files (x86)",
                                       "windows\\system32", "microsoft"]
                    is_known_location = any(d in folder.lower()
                                            for d in known_safe_dirs)

                    if is_risky_ext or is_high_risk:
                        warning = (
                            f"Warning! {os.path.basename(filepath)} is a HIGH RISK "
                            f"file. File type: {file_ext}. Size: {filesize_mb} MB. "
                            f"Location: {folder}. Executable files can harm your "
                            f"computer, steal data, or install unwanted software. "
                            f"I strongly recommend scanning it with antivirus first. "
                            f"Do you still want to open it? Say yes or no.")
                    elif is_known_location:
                        warning = (
                            f"{os.path.basename(filepath)} appears to be from a "
                            f"trusted location ({folder}). Size: {filesize_mb} MB. "
                            f"It looks safe but I still recommend caution with any "
                            f"executable file. Do you want to open it? Say yes or no.")
                    else:
                        warning = (
                            f"You are about to open {os.path.basename(filepath)}. "
                            f"File type: {file_ext}. Size: {filesize_mb} MB. "
                            f"Location: {folder}. I cannot verify if this file is "
                            f"completely safe. Make sure you trust the source of "
                            f"this file. Do you want to open it? Say yes or no.")

                    self._set_pending_exe(filepath)
                    self._say(warning)
                    return
                else:
                    self._say(f"I could not find {filename} on your computer.")
                    return
            else:
                self._say("Which executable file do you want to open?")
                return

        # ── GREETINGS ──
        if has("hello", "hi", "hey", "sup", "whats up", "howdy",
               "good morning", "good afternoon", "good evening", "good night",
               "namaste", "salaam", "hola", "yo", "greetings"):
            responses = [
                f"Hello {nm}! How can I assist you today?",
                f"Hey {nm}! Good to hear from you. What do you need?",
                f"{get_day_greeting()} {nm}! NYX at your service.",
                f"Hi {nm}! All systems ready. What can I do for you?",
            ]
            self._say(random.choice(responses))
            return

        # ── HOW ARE YOU ──
        if re.search(r"how are you|how r u|you doing|you okay|are you fine|"
                     r"how do you do|you alright", c2):
            self._say(random.choice([
                "All systems running at full capacity Boss.",
                "I am functioning perfectly Boss. Ready to serve you.",
                "All circuits nominal Boss. How can I help you today?",
            ]))
            return

        # ── IDENTITY ──
        if re.search(r"who are you|what are you|your name|introduce yourself|"
                     r"are you human|are you real|who made you|who built you|"
                     r"who created you", c2):
            self._say(
                "I am NYX, your advanced AI assistant. "
                "Your personal AI assistant created to serve you Boss. "
                "I can answer questions, control your system, fetch news and weather, "
                "and much more."
            )
            return

        # ── CAPABILITIES ──
        if re.search(r"what can you do|your features|capabilities|"
                     r"what do you do|help me|show me what you can|"
                     r"your powers|list your features", c2):
            self._say(
                "I can: answer any question using AI, check real-time weather for any city, "
                "fetch live news from BBC Reuters and Al Jazeera, play YouTube, "
                "search Google, control volume and brightness, take screenshots, "
                "open any app or website, do math and unit conversions, "
                "save notes and todos, set timers, tell jokes and fun facts, "
                "plan trips, and remember things about you Boss."
            )
            return

        # ── EMOTIONAL SUPPORT ──
        if re.search(r"i am sad|i feel sad|i am depressed|i am upset|"
                     r"i am lonely|having a bad day|i feel lost|life is hard|"
                     r"i give up|i am stressed|i am anxious|i am worried", c2):
            self._say(random.choice([
                f"I am sorry to hear that {nm}. Remember, tough times never last but tough people do. You have got this!",
                f"I understand {nm}. It is okay to feel this way. Take it one step at a time. I am here for you.",
                f"Hang in there {nm}. Every storm runs out of rain. Things will get better soon.",
            ]))
            return

        if re.search(r"i am happy|i am excited|i am proud|i just achieved|"
                     r"good news|great news|i did it|i succeeded", c2):
            self._say(random.choice([
                f"That is wonderful {nm}! Congratulations! You deserve it.",
                f"Excellent news {nm}! I am thrilled to hear that. Well done!",
                f"Fantastic {nm}! Your hard work is paying off. Keep going!",
            ]))
            return

        if re.search(r"i am bored|entertain me|something fun|"
                     r"nothing to do|keep me company", c2):
            self._say(random.choice([
                f"How about a joke {nm}? " + random.choice(JOKES),
                f"Here is a fun fact {nm}! " + random.choice(FACTS),
                f"Let me share a quote {nm}. " + random.choice(QUOTES),
            ]))
            return

        # ── MOTIVATE ──
        if has("motivate me", "inspire me", "motivation", "inspire",
               "give me a quote", "motivational quote"):
            self._say(random.choice(QUOTES))
            return

        # ── JOKES ──
        if has("joke", "funny", "laugh", "humor", "comedy", "make me laugh",
               "tell me a joke", "another joke"):
            self._say(random.choice(JOKES))
            return

        # ── FUN FACTS ──
        if has("fun fact", "interesting fact", "did you know",
               "random fact", "tell me something interesting",
               "something cool", "cool fact"):
            self._say(random.choice(FACTS))
            return

        # ── RIDDLES ──
        if has("riddle", "give me a riddle", "puzzle"):
            riddles = [
                ("What has keys but no locks?", "A keyboard!"),
                ("What gets wetter the more it dries?", "A towel!"),
                ("I have hands but cannot clap. What am I?", "A clock!"),
                ("What has cities but no houses?", "A map!"),
                ("The more you take, the more you leave behind. What am I?", "Footsteps!"),
                ("What can travel around the world while staying in a corner?", "A stamp!"),
                ("What has an eye but cannot see?", "A needle!"),
                ("What goes up but never comes down?", "Your age!"),
            ]
            r, a = random.choice(riddles)
            self._say(f"Here is a riddle {nm}. {r} Take a guess! The answer is: {a}")
            return

        # ── THANKS ──
        if re.search(r"\b(thank you|thanks|thank u|cheers|appreciate|"
                     r"you are great|you are awesome|well done|good job)\b", c2):
            self._say(random.choice([
                f"Always at your service {nm}.",
                f"Happy to help {nm}!",
                f"That is what I am here for {nm}.",
                f"Anytime {nm}. You know where to find me.",
                f"My pleasure {nm}!",
            ]))
            return

        # ── GOODBYE ──
        if has("bye", "goodbye", "good night", "see you", "later",
               "sleep mode", "farewell", "signing off", "going offline",
               "stop listening", "i have to go", "catch you later"):
            self._say(random.choice([
                f"Goodbye Boss. NYX standing by whenever you need me.",
                f"Farewell {nm}. Stay awesome!",
                f"Good night Boss. NYX going to standby mode.",
                f"See you soon {nm}. Take care!",
            ]))
            return

        # ── TIME ──
        if re.search(r"\b(what time|current time|time is it|tell me the time|"
                     r"what is the time|clock)\b", c2):
            now = datetime.datetime.now()
            self._say(f"It is {now.strftime('%I:%M %p')} Boss.")
            return

        # ── DATE ──
        if re.search(r"\b(what date|todays date|what day|which day|"
                     r"what is today|what is the date|day today)\b", c2) \
                and not has("trip", "travel", "visit", "plan", "news", "update"):
            now = datetime.datetime.now()
            self._say(f"Today is {now.strftime('%A, %B %d, %Y')} Boss.")
            return

        # ── YEAR / MONTH ──
        if has("what year", "which year", "current year"):
            self._say(f"It is {datetime.datetime.now().year} Boss.")
            return

        if has("what month", "which month", "current month"):
            self._say(f"It is {datetime.datetime.now().strftime('%B')} Boss.")
            return

        # ── WEATHER ──
        if has("weather", "temperature", "forecast", "climate",
               "raining", "rain", "sunny", "cloudy", "hot outside",
               "cold outside", "how hot", "how cold"):

            # Try multiple city extraction methods
            city = extract_city(raw)

            # If extract_city didn't find, try regex patterns
            if not city or len(city.strip()) < 2:
                patterns = [
                    r"(?:weather|temperature|forecast|climate)\s+(?:in|at|for|of)\s+([a-zA-Z\s]+?)(?:\s*(?:today|now|please|right now|\?|$))",
                    r"(?:in|at)\s+([a-zA-Z\s]+?)\s+(?:weather|temperature)",
                    r"weather\s+([a-zA-Z\s]+?)(?:\s*(?:today|now|\?|$))",
                ]
                for pat in patterns:
                    m = re.search(pat, c, re.IGNORECASE)
                    if m:
                        cand = m.group(1).strip().title()
                        bad  = ["the","a","an","here","there","today","now",
                                "please","right","currently","outside"]
                        if cand.lower() not in bad and len(cand) > 1:
                            city = cand
                            break

            # Check known cities list
            if not city or len(city.strip()) < 2:
                for known in WORLD_CITIES:
                    if known in c.lower():
                        city = known.title()
                        break

            # Final fallback
            if not city or len(city.strip()) < 2:
                city = self.mem.profile.get("city", "Pune")

            self.Q.put(("jstate", ("THINKING",)))
            result = self.brain.weather(city.strip())
            if result:
                self._say(f"Current weather in {city}: {result}")
            else:
                self._say(f"I could not fetch the weather for {city} right now Boss. "
                          f"Please check weather.com for accurate information.")
            return

        # ── NEWS ──
        # Only treat as a NEWS request when it is clearly about news — not
        # every "latest X" question (e.g. "latest iPhone model" is a product
        # question and should go to the real-time AI, not headlines).
        if (has("news", "headlines", "breaking news", "top stories",
                "whats happening", "current affairs", "news update")
                or (has("latest", "update", "updates") and has("news"))) \
                and not re.search(r"\b(iphone|phone|model|movie|song|version|"
                                  r"laptop|gadget|car|game|release)\b", c2):
            topic_kws = [
                "iran", "israel", "america", "us", "india", "china", "russia",
                "pakistan", "war", "ukraine", "gaza", "cricket", "ipl", "tech",
                "technology", "business", "economy", "election", "modi", "trump",
                "sports", "football", "climate", "world", "middle east", "europe",
                "europe", "hollywood", "bollywood",
            ]
            topic = "world"
            for kw in topic_kws:
                if re.search(r"\b" + kw + r"\b", c2):
                    topic = kw
                    break

            self.Q.put(("jstate", ("THINKING",)))

            # Detect how many headlines user wants
            count = 5  # default
            num_match = re.search(r"\b(\d+)\b", c2)
            if num_match:
                requested = int(num_match.group(1))
                count = min(requested, 20)  # cap at 20 to avoid too long

            heads = self.brain.news(topic, count=count)
            if heads:
                self._say(f"Here are {len(heads)} {topic} headlines Boss.")
                time.sleep(0.3)
                for h in heads:
                    if h:
                        self._say(h)
                        time.sleep(0.1)
            else:
                resp = self.brain.ask(
                    f"What is the latest news about {topic}? "
                    f"Give me {count} key updates in simple sentences."
                )
                self._say(resp)
            return

        # ── BOOKING (flights, trains, hotels, buses, cabs) ──
        if re.search(r"\b(book|booking|reserve|reservation|"
                     r"ticket|tickets|flight|flights|"
                     r"train|trains|hotel|hotels|"
                     r"bus|buses|cab|cabs|taxi|uber|ola|"
                     r"book a|book my|want to fly|"
                     r"fly to|fly from|travel from.*to)\b", c2):

            # FLIGHTS
            if re.search(r"\b(flight|flights|airplane|plane|"
                         r"fly to|fly from|air ticket|"
                         r"book.*flight|flight.*book|"
                         r"airplane ticket|air india|indigo|"
                         r"spicejet|vistara|akasa)\b", c2):
                if has("indigo"):
                    self._say("Opening IndiGo Airlines website.")
                    webbrowser.open("https://www.goindigo.in")
                elif has("air india"):
                    self._say("Opening Air India website.")
                    webbrowser.open("https://www.airindia.com")
                elif has("spicejet"):
                    self._say("Opening SpiceJet website.")
                    webbrowser.open("https://www.spicejet.com")
                elif has("vistara"):
                    self._say("Opening Vistara website.")
                    webbrowser.open("https://www.airvistara.com")
                elif has("akasa"):
                    self._say("Opening Akasa Air website.")
                    webbrowser.open("https://www.akasaair.com")
                else:
                    self._say("Opening MakeMyTrip flights for you.")
                    webbrowser.open("https://www.makemytrip.com/flights/")
                return

            # TRAINS
            if re.search(r"\b(train|trains|railway|rail|"
                         r"irctc|rajdhani|shatabdi|"
                         r"book.*train|train.*book|"
                         r"train ticket)\b", c2):
                self._say("Opening IRCTC for train booking.")
                webbrowser.open("https://www.irctc.co.in")
                return

            # HOTELS
            if re.search(r"\b(hotel|hotels|resort|resorts|"
                         r"stay|accommodation|room|rooms|"
                         r"oyo|trivago|airbnb|"
                         r"book.*hotel|hotel.*book)\b", c2):
                if has("oyo"):
                    self._say("Opening OYO Rooms.")
                    webbrowser.open("https://www.oyorooms.com")
                elif has("airbnb"):
                    self._say("Opening Airbnb.")
                    webbrowser.open("https://www.airbnb.co.in")
                elif has("trivago"):
                    self._say("Opening Trivago.")
                    webbrowser.open("https://www.trivago.in")
                elif has("booking"):
                    self._say("Opening Booking.com.")
                    webbrowser.open("https://www.booking.com")
                else:
                    self._say("Opening MakeMyTrip hotels for you.")
                    webbrowser.open("https://www.makemytrip.com/hotels/")
                return

            # BUSES
            if re.search(r"\b(bus|buses|redbus|red bus|"
                         r"volvo bus|sleeper bus|"
                         r"book.*bus|bus.*book|"
                         r"bus ticket)\b", c2):
                self._say("Opening RedBus for bus booking.")
                webbrowser.open("https://www.redbus.in")
                return

            # CABS / TAXIS
            if re.search(r"\b(cab|cabs|taxi|ride|uber|ola|"
                         r"book.*cab|cab.*book|"
                         r"book.*ride|need a ride)\b", c2):
                if has("uber"):
                    self._say("Opening Uber.")
                    webbrowser.open("https://www.uber.com")
                elif has("ola"):
                    self._say("Opening Ola.")
                    webbrowser.open("https://www.olacabs.com")
                else:
                    self._say("Opening Uber for cab booking.")
                    webbrowser.open("https://www.uber.com")
                return

            # GENERAL TRAVEL BOOKING (no specific type mentioned)
            self._say("Opening MakeMyTrip for you.")
            webbrowser.open("https://www.makemytrip.com")
            return

        # ── TRAVEL & TOURISM ──
        # Send the EXACT user question to the AI — do NOT rewrite it (that used
        # to swap in the wrong city and give unrelated answers).
        if re.search(r"\b(going to|visiting|visit|trip to|travel to|tour|"
                     r"vacation|holiday|should i see|what to see|things to do|"
                     r"places to visit|tourist|sightseeing|itinerary|"
                     r"plan.*trip|suggest.*places|recommend.*places|"
                     r"i am going|i want to go)\b", c2):
            resp = self.brain.ask(raw, lang=lang)
            self._say(resp)
            return

        # ── YOUTUBE ──
        # Triggers on play/watch OR any youtube request (open/show/find/videos/channel).
        if (has("play", "watch")
                or (has("youtube") and has("open", "show", "find", "search",
                                           "videos", "video", "channel"))) \
                and not has("news", "podcast", "episode"):
            q = re.sub(r"\b(play|watch|open|launch|show me|show|find|search for|"
                       r"search|on youtube|from youtube|in youtube|youtube|videos|"
                       r"video|latest|the|a|channel|for me|please|a song|"
                       r"some music|me some|of)\b", "", c2).strip()
            q = re.sub(r"\s+", " ", q).strip()
            if q:
                url = ("https://www.youtube.com/results?search_query="
                       + urllib.parse.quote(q))
                self._say(f"Searching YouTube for {q} Boss.", link=url)
                webbrowser.open(url)
            else:
                self._say("Opening YouTube Boss.", link="https://youtube.com")
                webbrowser.open("https://youtube.com")
            return

        # ── GOOGLE SEARCH ──
        if has("search", "google", "look up", "find on google",
               "search for", "browse", "search the web"):
            q = re.sub(r"\b(search for|search|google|look up|find on google|"
                       r"browse|please|the web for|web for)\b", "", c2).strip()
            if q:
                url = f"https://www.google.com/search?q={urllib.parse.quote(q)}"
                self._say(f"Searching Google for {q} Boss.", link=url)
                webbrowser.open(url)
            else:
                self._say("Opening Google Boss.", link="https://google.com")
                webbrowser.open("https://google.com")
            return

        # ── OPEN / VIEW EXISTING SCREENSHOT (must come before TAKE) ──
        if has("screenshot", "screen shot", "snapshot", "screen grab", "screengrab") and \
                has("open", "show", "view", "see", "display", "last", "my"):
            shot = getattr(self, "_last_screenshot", None)
            if not shot or not os.path.exists(shot):
                shot = self._latest_screenshot()
            if shot and os.path.exists(shot):
                self._say(f"Opening the screenshot {os.path.basename(shot)}.")
                try:
                    os.startfile(shot)
                except Exception as e:
                    print(f"Open screenshot error: {e}")
            else:
                self._say("I could not find a screenshot to open. "
                          "Say take a screenshot first.")
            return

        # ── TAKE SCREENSHOT ──
        if has("screenshot", "screen shot", "snapshot", "screen grab", "screengrab",
               "screen capture", "capture screen", "capture the screen",
               "take a screenshot", "take screenshot"):
            try:
                desktop  = self._desktop_dir()
                filename = f"screenshot_{int(time.time())}.png"
                filepath = os.path.join(desktop, filename)
                pyautogui.screenshot().save(filepath)
                self._last_screenshot = filepath
                self._say(f"Screenshot saved to your desktop as {filename}. "
                          f"Opening it now so you can see it.")
                try:
                    os.startfile(filepath)   # pop it open so it's easy to find
                except Exception as e:
                    print(f"Open-after-save error: {e}")
            except Exception as e:
                print(f"Screenshot error: {e}")
                self._say("Could not take the screenshot.")
            return

        # ── SAVE THE LAST GENERATED IMAGE ──
        if re.search(r"\b(save|download|keep)\b", c2) \
                and getattr(self, "_last_image", None) \
                and (re.search(r"\b(image|picture|photo|pic|wallpaper|drawing)\b", c2)
                     or (re.search(r"\b(it|that|this)\b", c2)
                         and not re.search(r"\b(note|shortcut|file|todo|task)\b", c2))):
            self._save_image(self._last_image,
                             getattr(self, "_last_image_caption", "image"))
            return

        # ── IMAGE SEARCH (open Google Images) ──
        # "show me image of eiffel tower", "picture of lamborghini".
        # NOT for explicit generation verbs — those go to AI generation below.
        if re.search(r"\b(show me image|show me picture|show me photo|image of|"
                     r"picture of|photo of|show image|show picture|show photo|"
                     r"images of|pictures of|photos of|what does.*look like|"
                     r"how does.*look)\b", c2) \
                and not re.search(r"\b(generate|create|draw|make|design)\b", c2):
            query = re.sub(r"\b(show me|show|image of|picture of|photo of|"
                           r"images of|pictures of|photos of|image|picture|photo|"
                           r"images|pictures|what does|how does|look like|look|"
                           r"please|an|a|the|some|of|me)\b", " ", c2)
            query = re.sub(r"\s+", " ", query).strip()
            if query:
                url = ("https://www.google.com/search?q="
                       + urllib.parse.quote(query) + "&tbm=isch")
                self._say(f"Searching for images of {query}. Opening Google Images.",
                          link=url)
                webbrowser.open(url)
            else:
                self._say("What would you like to see an image of?")
            return

        # ── GENERATE AN IMAGE (AI) ──
        # e.g. "generate a picture of spiderman", "draw a cute robot"
        if (re.search(r"\b(image|picture|photo|pic|wallpaper|drawing|"
                      r"illustration|art)\b", c2)
                and re.search(r"\b(generate|create|make|draw|design)\b", c2)) \
                or re.search(r"\b(draw|sketch)\s+(me\s+)?(a|an|the|some)\b", c2):
            subject = re.sub(
                r"\b(generate|create|make|draw|design|me|an|a|the|of|image|"
                r"images|picture|pictures|photo|photos|pic|wallpaper|drawing|"
                r"illustration|art|for|please|some)\b", " ", c2)
            subject = re.sub(r"\s+", " ", subject).strip()
            if subject:
                threading.Thread(target=self._provide_image,
                                 args=(subject,), daemon=True).start()
            else:
                self._say("What would you like me to generate an image of?")
            return

        # ── AUTO-START WITH WINDOWS ──
        if re.search(r"\b(enable auto.?start|start with windows|"
                     r"boot with windows|autostart on)\b", c2):
            if self._enable_autostart():
                self._say("Autostart enabled. NYX will now start with Windows.")
            else:
                self._say("Could not enable autostart.")
            return
        if re.search(r"\b(disable auto.?start|autostart off|"
                     r"do ?n.?t start with windows)\b", c2):
            self._disable_autostart()
            self._say("Autostart disabled.")
            return

        # ── SHORTCUTS (list / add) ──
        if re.search(r"\b(list shortcuts|my shortcuts|show shortcuts)\b", c2):
            self.shortcuts = self._load_shortcuts()
            if self.shortcuts:
                self._say(f"You have {len(self.shortcuts)} shortcuts.")
                for name in list(self.shortcuts.keys())[:10]:
                    self._say(name)
            else:
                self._say("No shortcuts saved yet.")
            return
        if re.search(r"\b(add shortcut|save shortcut|remember shortcut)\b", c2):
            self._say("Please edit nyx_shortcuts.json in the NYX folder to add shortcuts.")
            return

        # ── OPEN QUICK FOLDER (documents / downloads / desktop / ...) ──
        if re.search(r"\b(open|show|go to|launch)\b", c2) and any(
                k in c2 for k in ["document", "download", "desktop", "picture",
                                  "photo", "music", "video", "my files"]):
            user = os.environ.get("USERPROFILE", os.path.expanduser("~"))

            def _fe(*paths):
                for p in paths:
                    if os.path.exists(p):
                        return p
                return paths[0]

            if "download" in c2:
                path = _fe(os.path.join(user, "Downloads"))
            elif "document" in c2:
                path = _fe(os.path.join(user, "OneDrive", "Documents"),
                           os.path.join(user, "Documents"))
            elif "desktop" in c2:
                path = _fe(os.path.join(user, "OneDrive", "Desktop"),
                           os.path.join(user, "Desktop"))
            elif "picture" in c2 or "photo" in c2:
                path = _fe(os.path.join(user, "Pictures"))
            elif "music" in c2:
                path = _fe(os.path.join(user, "Music"))
            elif "video" in c2:
                path = _fe(os.path.join(user, "Videos"))
            else:
                path = user

            if os.path.exists(path):
                self._say(f"Opening {os.path.basename(path) or 'home'} folder.")
                os.startfile(path)
            else:
                self._say("Could not find that folder.")
            return

        # ── OPEN SHORTCUT / FOLDER BY NAME ──
        if re.search(r"\b(open|launch|show|go to)\b.*\b(folder|directory)\b", c2) or \
           re.search(r"\b(open|launch|show)\s+\w+\s+(folder|ml|project)\b", c2):
            target = re.sub(r"\b(open|launch|show|go to|folder|directory|the|please|my)\b",
                            "", c2).strip()
            target = re.sub(r"\s+", " ", target).strip()
            if target and self.open_shortcut(target):
                return
            self._say(f"Searching for the {target} folder.")
            folders, _ = self._find_files(target)
            if folders:
                try:
                    os.startfile(folders[0])
                    self._say(f"Opened {os.path.basename(folders[0])}.")
                except Exception as e:
                    print(f"Open folder error: {e}")
                    self._say(f"Could not open {target}.")
            else:
                self._say(f"Could not find folder {target}.")
            return

        # ── FIND FILE / FOLDER (deep search) ──
        if re.search(r"\b(find|search for|locate|where is|where s)\b", c2) and \
           re.search(r"\b(file|files|document|pdf|photo|image|picture|video|"
                     r"song|music|folder|project)\b", c2):
            query = re.sub(r"\b(find|search for|locate|where is|where s|the|files|"
                           r"file|document|folder|project|please|my|for|named|"
                           r"called|on|laptop|computer|pc|system)\b", " ", c2)
            query = re.sub(r"\s+", " ", query).strip()
            if query:
                self._say(f"Searching for {query}. This can take a few seconds.")
                if self.open_shortcut(query):
                    return
                folders, _ = self._find_files(query)
                if folders:
                    try:
                        os.startfile(folders[0])
                        self._say(f"Opened the {os.path.basename(folders[0])} folder.")
                    except Exception:
                        pass
                    return
                results = self.deep_file_search(query)
                if results:
                    self._say(f"Found {len(results)} matches.")
                    for r in results[:3]:
                        self._say(f"{os.path.basename(r)} in {os.path.dirname(r)}")
                else:
                    self._say(f"Could not find {query}.")
            return

        # ── LIST FILES IN FOLDER ──
        if re.search(r"\b(what.?s in|whats in|list files|show contents|"
                     r"show files)\b", c2):
            user = os.environ.get("USERPROFILE", os.path.expanduser("~"))

            def _fe2(*paths):
                for p in paths:
                    if os.path.exists(p):
                        return p
                return paths[0]

            if "desktop" in c2:
                path = _fe2(os.path.join(user, "OneDrive", "Desktop"),
                            os.path.join(user, "Desktop"))
            elif "download" in c2:
                path = _fe2(os.path.join(user, "Downloads"))
            elif "document" in c2:
                path = _fe2(os.path.join(user, "OneDrive", "Documents"),
                            os.path.join(user, "Documents"))
            else:
                path = _fe2(os.path.join(user, "OneDrive", "Desktop"),
                            os.path.join(user, "Desktop"))

            folders, files = self.list_folder(path)
            if folders or files:
                self._say(f"In {os.path.basename(path)}:")
                if folders:
                    self._say(f"{len(folders)} folders: {', '.join(folders[:5])}")
                if files:
                    self._say(f"{len(files)} files: {', '.join(files[:5])}")
            else:
                self._say("The folder is empty.")
            return

        # ── READ FILE ──
        if re.search(r"\b(read|open and read|show contents of)\b.*\bfile\b", c2) or \
           re.search(r"\bwhat does\b.*\bsay\b", c2):
            filename = re.sub(r"\b(read|open and read|show contents of|what does|"
                              r"the|file|say|please|contents|of|me)\b", "", c2).strip()
            if filename:
                results = self.deep_file_search(filename, max_results=1)
                if results:
                    content = self.read_file_content(results[0])
                    if content:
                        self._say(f"Contents of {os.path.basename(results[0])}:")
                        self._say(content[:300])
                    else:
                        self._say("Cannot read that file.")
                else:
                    self._say(f"Could not find {filename}.")
            return

        # ── VOLUME UP ──
        if re.search(r"\b(volume up|louder|increase volume|"
                     r"turn up the volume|sound up)\b", c2):
            if AUDIO:
                try:
                    d = AudioUtilities.GetSpeakers()
                    i = d.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                    v = cast(i, POINTER(IAudioEndpointVolume))
                    v.SetMasterVolumeLevelScalar(
                        min(1.0, v.GetMasterVolumeLevelScalar() + 0.15), None)
                    self._say("Volume increased Boss.")
                except Exception as e:
                    print(f"Volume error: {e}")
                    self._say("Could not adjust volume Boss.")
            else:
                self._say("Volume control is unavailable Boss.")
            return

        # ── VOLUME DOWN ──
        if re.search(r"\b(volume down|quieter|decrease volume|"
                     r"turn down the volume|sound down)\b", c2):
            if AUDIO:
                try:
                    d = AudioUtilities.GetSpeakers()
                    i = d.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                    v = cast(i, POINTER(IAudioEndpointVolume))
                    v.SetMasterVolumeLevelScalar(
                        max(0.0, v.GetMasterVolumeLevelScalar() - 0.15), None)
                    self._say("Volume decreased Boss.")
                except Exception as e:
                    print(f"Volume error: {e}")
                    self._say("Could not adjust volume Boss.")
            else:
                self._say("Volume control is unavailable Boss.")
            return

        # ── MUTE ──
        if has("mute", "silence the volume", "mute the sound"):
            if AUDIO:
                try:
                    d = AudioUtilities.GetSpeakers()
                    i = d.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                    v = cast(i, POINTER(IAudioEndpointVolume))
                    v.SetMasterVolumeLevelScalar(0.0, None)
                    self._say("Muted Boss.")
                except Exception as e:
                    print(f"Mute error: {e}")
            return

        # ── BRIGHTNESS ──
        if has("brightness") and sbc:
            try:
                cur = sbc.get_brightness()[0]
                if has("increase", "up", "brighter", "more bright"):
                    sbc.set_brightness(min(100, cur + 20))
                    self._say("Brightness increased Boss.")
                elif has("decrease", "down", "dimmer", "less bright", "lower"):
                    sbc.set_brightness(max(0, cur - 20))
                    self._say("Brightness decreased Boss.")
                else:
                    self._say(f"Current brightness is {cur} percent Boss.")
            except Exception as e:
                print(f"Brightness error: {e}")
                self._say("Could not adjust brightness Boss.")
            return

        # ── SYSTEM INFO ──
        if has("battery", "cpu usage", "ram usage", "memory usage",
               "system info", "system information", "disk space",
               "computer specs", "my ip", "ip address"):
            if PSUTIL:
                try:
                    info_parts = []
                    if has("battery"):
                        batt = psutil.sensors_battery()
                        if batt:
                            info_parts.append(
                                f"Battery is at {int(batt.percent)} percent, "
                                f"{'charging' if batt.power_plugged else 'on battery'}")
                        else:
                            info_parts.append("No battery detected")
                    if has("cpu"):
                        cpu = psutil.cpu_percent(interval=0.5)
                        info_parts.append(f"CPU usage is {cpu} percent")
                    if has("ram", "memory"):
                        ram = psutil.virtual_memory()
                        info_parts.append(
                            f"RAM usage is {ram.percent} percent, "
                            f"{ram.available // (1024**3)} GB available")
                    if has("disk", "storage"):
                        disk = psutil.disk_usage("/")
                        info_parts.append(
                            f"Disk is {disk.percent} percent full, "
                            f"{disk.free // (1024**3)} GB free")
                    if not info_parts:
                        cpu  = psutil.cpu_percent(interval=0.5)
                        ram  = psutil.virtual_memory()
                        batt = psutil.sensors_battery()
                        info_parts.append(
                            f"CPU {cpu}%, RAM {ram.percent}% used")
                        if batt:
                            info_parts.append(f"Battery {int(batt.percent)}%")
                    self._say(". ".join(info_parts) + " Boss.")
                except Exception as e:
                    print(f"System info error: {e}")
                    self._say("Could not retrieve system info Boss.")
            else:
                self._say("System monitoring is unavailable. Install psutil to enable this Boss.")
            return

        # ── OPEN APPS ──────────────────────────────────────────────────────────
        if re.search(r"\b(open|launch|start|run)\b", c2) and \
                not re.search(r"\b(folder|directory|file|files|"
                              r"screenshot|screen shot)\b", c2) and \
                not re.search(r"\b(youtube|google|gmail|instagram|twitter|"
                              r"facebook|netflix|github|linkedin|amazon|"
                              r"flipkart|reddit|wikipedia|whatsapp|spotify|"
                              r"website|webpage|browser)\b", c2):

            # Strip verbs + filler so a mis-heard "open it here for me" doesn't
            # become a bogus app search.
            target = re.sub(
                r"\b(open|launch|start|run|please|the|app|application|for|me|"
                r"it|this|that|here|there|one|thing|a|an|to|my|up|now|some)\b",
                "", c2).strip()
            target = re.sub(r"\s+", " ", target).strip()

            # Guard: nothing meaningful left → the command was unclear/mis-heard.
            if len(target) < 2:
                self._say("I did not catch that clearly. "
                          "Could you please say it again?")
                return

            # ── Step 1: Built-in Windows apps ──
            for app_name, cmd in WINDOWS_APPS.items():
                if app_name in target or target == app_name:
                    self._say(f"Opening {app_name.title()} Boss.")
                    os.system(cmd) if cmd.startswith("start ") else \
                        subprocess.Popen(cmd, shell=True)
                    return

            # ── Step 2: Search EVERYTHING on this PC ──
            self._say(f"Searching your computer for {target} Boss.")
            found = self._find_any_app(target)
            if found:
                # Safety: apps found outside standard install locations need
                # confirmation before running.
                if not self._is_safe_app(found):
                    self._say(f"Found {os.path.basename(found)} at "
                              f"{os.path.dirname(found)}. This is not from a "
                              f"standard install location. Do you want to open "
                              f"it? Say yes or no.")
                    self._set_pending_exe(found)
                    return
                self._say(f"Found it. Opening {target} now Boss.")
                try:
                    os.startfile(found)
                except Exception:
                    subprocess.Popen(f'"{found}"', shell=True)
                return

            # ── Step 3: Not found ──
            self._say(
                f"I could not find {target} on your system Boss. "
                f"Searching Google to help you download it."
            )
            webbrowser.open(
                "https://www.google.com/search?q=download+"
                + urllib.parse.quote(target) + "+for+windows")
            return

        # ── OPEN WEBSITES ──
        if re.search(r"\b(open|go to|navigate to|visit|browse to)\b", c2):
            target = re.sub(r"\b(open|go to|navigate to|visit|browse to|please)\b",
                            "", c2).strip()
            matched = next((url for key, url in SITES.items() if key in target), None)
            if matched:
                self._say(f"Opening {target.strip().title()} Boss.", link=matched)
                webbrowser.open(matched)
            else:
                # Try as URL
                if "." in target:
                    url = target if target.startswith("http") else "https://" + target
                    self._say(f"Opening {target} Boss.", link=url)
                    webbrowser.open(url)
                else:
                    url = f"https://www.google.com/search?q={urllib.parse.quote(target)}"
                    self._say(f"Searching for {target} Boss.", link=url)
                    webbrowser.open(url)
            return

        # ── SYSTEM COMMANDS ──
        if re.search(r"\b(lock|lock screen|lock computer|lock my computer)\b", c2):
            self._say("Locking your computer Boss.")
            os.system("rundll32.exe user32.dll,LockWorkStation")
            return

        if re.search(r"\b(shutdown|shut down|turn off the computer|"
                     r"power off|switch off)\b", c2):
            self._say("Shutting down in 5 seconds Boss. Goodbye.")
            os.system("shutdown /s /t 5")
            return

        if re.search(r"\b(restart|reboot|restart computer)\b", c2):
            self._say("Restarting in 5 seconds Boss.")
            os.system("shutdown /r /t 5")
            return

        if re.search(r"\b(sleep|hibernate)\b", c2) and has("computer", "pc", "laptop"):
            self._say("Putting computer to sleep Boss.")
            os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
            return

        # ── NOTES ──
        if re.search(r"\b(make a note|write down|save note|note that|"
                     r"remember this|add to notes|take note)\b", c2):
            note = re.sub(r"\b(make a note|write down|save note|note that|"
                          r"remember this|add to notes|take note|please|that)\b",
                          "", c2).strip()
            if note:
                self.mem.add_note(note)
                self._say(f"Saved to your notes Boss: {note}")
            else:
                self._say("What would you like me to note down Boss?")
            return

        if re.search(r"\b(read my notes|show my notes|my notes|"
                     r"list notes|read notes)\b", c2):
            notes = self.mem.get_notes(3)
            if notes:
                self._say(f"Here are your last {len(notes)} notes Boss.")
                time.sleep(0.2)
                for note in notes:
                    clean = note.split("-", 1)[-1].strip() if "-" in note else note
                    self._say(ascii_clean(clean))
                    time.sleep(0.2)
            else:
                self._say("You have no saved notes yet Boss.")
            return

        # ── TODOS ──
        if re.search(r"\b(add to do|add task|new task|add todo)\b", c2):
            task = re.sub(r"\b(add to do|add task|new task|add todo|please)\b",
                          "", c2).strip()
            if task:
                self.mem.add_todo(task)
                self._say(f"Added to your todo list Boss: {task}")
            return

        if re.search(r"\b(my todos|show todos|list tasks|my tasks|todo list)\b", c2):
            todos = self.mem.get_todos()
            if todos:
                pending = [t for t in todos if not t.get("done")]
                if pending:
                    self._say(f"You have {len(pending)} pending tasks Boss.")
                    for i, t in enumerate(pending[:3]):
                        self._say(f"Task {i+1}: {t['item']}")
                else:
                    self._say("All tasks are completed Boss. Well done!")
            else:
                self._say("Your todo list is empty Boss.")
            return

        # ── TIMER ──
        if re.search(r"\b(set a timer|timer for|countdown|set timer|"
                     r"start timer|remind me in)\b", c2):
            m = re.search(r"(\d+)\s*(minute|min|second|sec|hour|hr)", c2)
            if m:
                n, unit = int(m.group(1)), m.group(2)
                if "hour" in unit or unit == "hr":
                    secs = n * 3600
                    label = f"{n} hour"
                elif "min" in unit:
                    secs = n * 60
                    label = f"{n} minute"
                else:
                    secs = n
                    label = f"{n} second"
                self._say(f"Timer set for {label}s Boss. I will alert you when done.")

                def _timer_cb():
                    time.sleep(secs)
                    self._say(f"Boss! Your {label} timer is complete! Time is up!")

                threading.Thread(target=_timer_cb, daemon=True).start()
            else:
                self._say("Please tell me how long the timer should be Boss. "
                          "For example: set a 5 minute timer.")
            return

        # ── STOPWATCH ──
        if has("stopwatch", "start stopwatch"):
            self._say("Stopwatch started Boss.")
            self._stopwatch_start = time.time()
            return

        if has("stop stopwatch", "stop the watch", "how long"):
            if hasattr(self, "_stopwatch_start"):
                elapsed = int(time.time() - self._stopwatch_start)
                mins, secs = divmod(elapsed, 60)
                self._say(f"Elapsed time is {mins} minutes and {secs} seconds Boss.")
            else:
                self._say("No stopwatch was started Boss.")
            return

        # ── MATH (catches ALL formats) ────────────────────────────────────────
        # Try math FIRST before anything else if numbers are present
        # Handles: 30+3= | 50*2 | what is 15% of 200 | sqrt 144 | 5 factorial
        if re.search(r"\d", c):
            claim = check_math_claim(c)
            if claim:
                self._say(claim)
                return
            result = parse_math(c)
            if result:
                self._say(f"The answer is {result} Boss.")
                return

        # Percentage calculations
        if re.search(r"\d+\s*(?:percent|%)\s*of\s*\d+", c2):
            result = parse_math(c)
            if result:
                self._say(f"The answer is {result} Boss.")
                return

        # ── UNIT CONVERSIONS ──
        if has("convert", "conversion") or \
                re.search(r"\b(km|miles?|celsius|fahrenheit|kg|pounds?|"
                          r"meters?|feet|liters?|gallons?|inches?|mph|kmph)\b", c2):
            result = do_unit_conversion(c)
            if result:
                self._say(result)
                return

        # ── REMEMBER / FACTS ──
        if re.search(r"\b(remember that|remember|dont forget|keep in mind|"
                     r"note that i|i want you to know)\b", c2):
            fact = re.sub(r"\b(remember that|remember|dont forget|keep in mind|"
                          r"note that i|i want you to know|please)\b",
                          "", c2).strip()
            if fact:
                self.mem.add_fact(fact)
                self._say(f"Got it Boss. I will remember that {fact}.")
            return

        if re.search(r"\b(what do you know about me|what do you remember|"
                     r"list my facts|what facts)\b", c2):
            facts = self.mem.profile.get("facts", [])
            if facts:
                self._say(f"Here is what I know about you Boss.")
                for f in facts[-5:]:
                    self._say(f)
            else:
                self._say("I do not have any saved facts about you yet Boss.")
            return

        # ── COIN FLIP ──
        if has("flip a coin", "coin flip", "heads or tails", "toss a coin"):
            self._say(random.choice(["Heads Boss!", "Tails Boss!"]))
            return

        # ── DICE ──
        if has("roll a dice", "roll dice", "dice roll", "roll the dice"):
            self._say(f"You rolled a {random.randint(1, 6)} Boss!")
            return

        # ── RANDOM NUMBER ──
        if has("random number", "pick a number", "give me a number"):
            m = re.search(r"between\s+(\d+)\s+and\s+(\d+)", c2)
            if m:
                lo, hi = int(m.group(1)), int(m.group(2))
                self._say(f"Your random number between {lo} and {hi} is {random.randint(lo, hi)} Boss!")
            else:
                self._say(f"Your random number is {random.randint(1, 100)} Boss!")
            return

        # ── FOOD & RECIPES ──
        # NOTE: no bare "prepare" here — "prepare an elevator speech" / "prepare a
        # report" are not cooking requests (it must be tied to food).
        if has("recipe", "how to make", "how to cook", "ingredients for",
               "cook", "bake", "prepare (?:a |some |the )?(?:meal|dish|dinner|"
               "lunch|breakfast|food|snack|dessert)"):
            resp = self.brain.ask(raw + " Give a brief helpful cooking response.", lang=lang)
            self._say(resp)
            return

        # ── HEALTH & FITNESS ──
        if has("exercise", "workout", "health", "diet", "nutrition",
               "weight loss", "fitness", "calories", "meditation", "yoga"):
            resp = self.brain.ask(raw + " Give practical health advice in 3 sentences.", lang=lang)
            self._say(resp)
            return

        # ── TECHNOLOGY ──
        if has("python", "javascript", "coding", "programming", "software",
               "hardware", "artificial intelligence", "machine learning",
               "blockchain", "cloud computing", "cybersecurity"):
            resp = self.brain.ask(raw + " Give a concise technical explanation.", lang=lang)
            self._say(resp)
            return

        # ── MOVIES & ENTERTAINMENT ──
        if has("movie", "film", "series", "tv show", "watch", "netflix",
               "actor", "actress", "director", "recommend a movie",
               "bollywood", "hollywood"):
            resp = self.brain.ask(raw + " Give helpful entertainment recommendations.", lang=lang)
            self._say(resp)
            return

        # ── SPORTS ──
        if has("cricket", "football", "soccer", "tennis", "basketball",
               "ipl", "match", "score", "player", "team", "tournament"):
            resp = self.brain.ask(raw, lang=lang)
            self._say(resp)
            return

        # ── SCIENCE & SPACE ──
        if has("science", "physics", "chemistry", "biology", "space",
               "planet", "universe", "atom", "gravity", "black hole",
               "nasa", "isro", "rocket", "satellite"):
            resp = self.brain.ask(raw + " Explain simply in 3 sentences.", lang=lang)
            self._say(resp)
            return

        # ── BUSINESS & FINANCE ──
        if has("stock", "invest", "crypto", "bitcoin", "money", "finance",
               "business", "startup", "profit", "economy", "share market"):
            resp = self.brain.ask(
                raw + " Give factual information without specific investment advice.")
            self._say(resp)
            return

        # ── WIKIPEDIA / FACTUAL ──
        if re.search(r"\b(who is|who was|what is|what was|define|explain|"
                     r"describe|tell me about|history of|when was|where is|"
                     r"how does|why is|when did|founded|invented|"
                     r"discovered|born|died)\b", c2):
            # Skip Wikipedia for travel/advice questions
            skip = any(w in c2 for w in [
                "should i", "going to", "visit", "trip", "travel",
                "recommend", "advice", "opinion", "help me",
                "how to", "can i", "will i", "best way", "what should",
                "plan", "vacation", "holiday", "see there", "things to do",
            ])
            if not skip:
                q = re.sub(r"\b(who is|who was|what is|what was|define|explain|"
                           r"describe|tell me about|history of|when was|"
                           r"where is|how does|why is|when did|please|boss|nyx)\b",
                           "", c2).strip()
                try:
                    hits = wikipedia.search(q, results=4)
                    for h in hits:
                        try:
                            s = ascii_clean(
                                wikipedia.summary(h, sentences=2, auto_suggest=False))
                            if s and len(s) > 40:
                                self._say(s)
                                return
                        except:
                            continue
                except Exception as e:
                    print(f"Wiki: {e}")
            # Fall through to AI
            resp = self.brain.ask(raw, lang=lang)
            self._say(resp)
            return

        # ── COMPLIMENTS TO NYX ──
        if has("you are amazing", "you are smart", "you are the best",
               "i love you nyx", "good bot", "well done nyx"):
            self._say(random.choice([
                f"Thank you {nm}! You are too kind.",
                f"I appreciate that {nm}! I am always improving for you.",
                f"You flatter me {nm}! At your service always.",
            ]))
            return

        # ── INTERNET CHECK ──
        if has("internet", "wifi", "connection", "am i connected",
               "check internet", "is internet working"):
            if is_connected():
                self._say("Your internet connection is working fine Boss.")
            else:
                self._say("It seems you are not connected to the internet Boss. Please check your network.")
            return

        # ── TABLE / STRUCTURED DATA REQUEST ──
        if has("table", "tabular", "list wise", "state wise", "statewise",
               "in a table", "make a table", "generate a table", "as a table",
               "column", "chart") or re.search(r"\blist\b.*\bof\b", c2):
            resp = self.brain.ask(
                raw + " Present the answer as a neat plain-text table with a "
                      "header row and columns aligned using spaces (monospace). "
                      "Do not use markdown asterisks or bold. Keep it compact.",
                lang=lang)
            self._say(resp)
            return

        # ── CATCH-ALL → AI BRAIN ──
        resp = self.brain.ask(raw, lang=lang)
        self._say(resp)

    # ── FILE / FOLDER FINDER ─────────────────────────────────────────────────
    def _find_files(self, query, limit=6):
        """Search the user's real locations + all drives for files and folders
        whose name contains every word of the query. Returns (folders, files)."""
        words = [w for w in query.lower().split() if len(w) > 1]
        if not words:
            return [], []

        user = os.environ.get("USERPROFILE", os.path.expanduser("~"))
        # Search personal folders first (fast, most likely), then whole drives.
        roots = [
            os.path.join(user, "Desktop"),
            os.path.join(user, "OneDrive", "Desktop"),
            os.path.join(user, "Downloads"),
            os.path.join(user, "Documents"),
            os.path.join(user, "OneDrive", "Documents"),
            os.path.join(user, "Pictures"),
            os.path.join(user, "Videos"),
            os.path.join(user, "Music"),
            user,
        ]
        # Add every available fixed drive for a deeper sweep.
        for letter in "CDEFG":
            d = f"{letter}:\\"
            if os.path.exists(d):
                roots.append(d)

        SKIP = {"windows", "$recycle.bin", "system volume information",
                "node_modules", "__pycache__", "appdata", "program files",
                "program files (x86)", "programdata", ".git", "venv", "env"}

        def matches(name):
            n = name.lower()
            return all(w in n for w in words)

        folders, files = [], []
        seen = set()
        for root0 in roots:
            if not os.path.exists(root0):
                continue
            is_drive = len(root0) <= 3
            try:
                for root, dirs, fnames in os.walk(root0):
                    # prune junk / slow system dirs
                    dirs[:] = [d for d in dirs
                               if not d.startswith(("$", "."))
                               and d.lower() not in SKIP]
                    for d in dirs:
                        if matches(d):
                            p = os.path.join(root, d)
                            if p not in seen:
                                seen.add(p); folders.append(p)
                    for f in fnames:
                        if matches(f):
                            p = os.path.join(root, f)
                            if p not in seen:
                                seen.add(p); files.append(p)
                    if len(folders) >= limit and len(files) >= limit:
                        break
                    # limit depth so a full-drive walk stays responsive
                    depth = root[len(root0):].count(os.sep)
                    if depth >= (6 if is_drive else 5):
                        dirs.clear()
            except Exception:
                continue
            if len(folders) >= limit and len(files) >= limit:
                break
        return folders[:limit], files[:limit]

    # ── APP FINDER ───────────────────────────────────────────────────────────
    def _find_any_app(self, name):
        """
        Search EVERYWHERE on this PC for the app.
        Returns full path of .exe or .lnk if found, else None.
        """
        name_lower = name.lower().strip()
        words      = name_lower.split()

        # Build exe candidates
        candidates = [
            name_lower.replace(" ", "") + ".exe",
            name_lower.replace(" ", "_") + ".exe",
            name_lower.replace(" ", "-") + ".exe",
            words[0] + ".exe",
        ]
        if len(words) > 1:
            candidates += [
                "".join(words) + ".exe",
                words[0] + words[1] + ".exe",
            ]

        # Known app mappings
        known = {
            "tlauncher":        ["tlauncher.exe", "TLauncher.exe"],
            "t launcher":       ["tlauncher.exe", "TLauncher.exe"],
            "minecraft":        ["minecraft launcher.exe", "minecraftlauncher.exe"],
            "arduino ide":      ["arduino_ide.exe", "arduino.exe"],
            "arduino":          ["arduino_ide.exe", "arduino.exe"],
            "obs":              ["obs64.exe", "obs.exe"],
            "obs studio":       ["obs64.exe"],
            "vs code":          ["code.exe"],
            "visual studio code": ["code.exe"],
            "android studio":   ["studio64.exe"],
            "blender":          ["blender.exe"],
            "gimp":             ["gimp.exe"],
            "vlc":              ["vlc.exe"],
            "audacity":         ["audacity.exe"],
            "notepad++":        ["notepad++.exe"],
            "notepad plus":     ["notepad++.exe"],
            "7zip":             ["7zfm.exe"],
            "7 zip":            ["7zfm.exe"],
            "winrar":           ["winrar.exe"],
            "steam":            ["steam.exe"],
            "discord":          ["discord.exe"],
            "telegram":         ["telegram.exe"],
            "zoom":             ["zoom.exe"],
            "postman":          ["postman.exe"],
            "pycharm":          ["pycharm64.exe"],
            "intellij":         ["idea64.exe"],
            "unity":            ["unity.exe"],
            "figma":            ["figma.exe"],
            "slack":            ["slack.exe"],
            "skype":            ["skype.exe"],
            "epic games":       ["epicgameslauncher.exe"],
            "origin":           ["origin.exe"],
            "valorant":         ["valorant.exe"],
            "league":           ["leagueclient.exe"],
        }
        if name_lower in known:
            candidates = known[name_lower] + candidates

        # ALL directories to search
        user = os.path.expanduser("~")
        dirs_to_search = [
            # Start Menu — MOST RELIABLE for shortcuts
            os.path.join(os.environ.get("APPDATA",""),
                         "Microsoft","Windows","Start Menu","Programs"),
            os.path.join(os.environ.get("PROGRAMDATA","C:\\ProgramData"),
                         "Microsoft","Windows","Start Menu","Programs"),
            # Desktop
            os.path.join(user, "Desktop"),
            os.path.join(user, "OneDrive", "Desktop"),
            os.path.join("C:\\Users","Public","Desktop"),
            # Program Files
            "C:\\Program Files",
            "C:\\Program Files (x86)",
            # AppData
            os.path.join(user, "AppData", "Local", "Programs"),
            os.path.join(user, "AppData", "Local"),
            os.path.join(user, "AppData", "Roaming"),
            # Downloads
            os.path.join(user, "Downloads"),
            # Other drives
            "D:\\Program Files",
            "D:\\Program Files (x86)",
            "D:\\",
            "E:\\",
            os.environ.get("PROGRAMFILES","C:\\Program Files"),
            os.environ.get("PROGRAMFILES(X86)","C:\\Program Files (x86)"),
        ]

        for search_dir in dirs_to_search:
            if not search_dir or not os.path.exists(search_dir):
                continue
            try:
                for root, dirs, files in os.walk(search_dir):
                    for f in files:
                        f_lower = f.lower()
                        f_noext = f_lower.replace(".exe","").replace(".lnk","")

                        # Exact exe candidate match
                        for cand in candidates:
                            if f_lower == cand.lower():
                                return os.path.join(root, f)

                        # Fuzzy: all words of name in filename
                        if all(w in f_noext for w in words):
                            if f_lower.endswith((".exe",".lnk")):
                                return os.path.join(root, f)

                        # Fuzzy: name in folder AND exe in folder
                        folder = os.path.basename(root).lower()
                        if (name_lower in folder or
                                all(w in folder for w in words)):
                            if f_lower.endswith(".exe") and words[0] in f_lower:
                                return os.path.join(root, f)
                            # Also return .lnk shortcut if folder matches
                            if f_lower.endswith(".lnk"):
                                return os.path.join(root, f)

                    # Limit depth to avoid hanging
                    depth = root[len(search_dir):].count(os.sep)
                    if depth >= 5:
                        dirs.clear()
            except Exception:
                continue

        return None

    # ── STARTUP SEQUENCE ──────────────────────────────────────────────────────
    def _startup(self):
        time.sleep(1.5)
        nm     = self.mem.profile.get("name", "").strip()
        g      = get_day_greeting()
        online = is_connected()
        status = "All systems online." if online else "Running in offline mode."
        self._last_greet = self._greet_bubble_period = g
        greet  = f"{g} {nm}." if nm else f"{g}."
        msg = (f"{greet} Nyx is online. How may I assist you today?")
        self.Q.put(("greet_bubble", (msg, False)))
        self.Q.put(("speak",  (msg,)))
        self.Q.put(("jstate", ("SLEEPING",)))

    # ── WAKE WORD LOOP ────────────────────────────────────────────────────────
    def _wake_loop(self):
        """Wake-word listener. Runs ONLY while the dashboard window is open
        (visible) — pauses when hidden in the tray or minimized. Also gated by
        SLEEPING state + the wake toggle."""
        try:
            with sr.Microphone() as source:
                self.rec.adjust_for_ambient_noise(source, duration=1.5)
                print("[NYX] Wake word listener started:", WAKE)
                while self.running:
                    if self._visible and self.jstate == "SLEEPING" and \
                            self.mem.profile.get("wake", True):
                        try:
                            audio = self.rec.listen(source, phrase_time_limit=6)
                            text  = self.rec.recognize_google(audio).lower()
                            print(f"[NYX heard] {text}")

                            for wake in WAKE:
                                if wake in text:
                                    cmd = text.split(wake, 1)[-1].strip()
                                    self._stop_speaking()   # let user interrupt
                                    self.Q.put(("jstate", ("LISTENING",)))

                                    if cmd and len(cmd) > 2:
                                        # Direct command e.g. "hey nyx open folder"
                                        self._user(cmd)
                                        self._cmd(cmd, lang="en")
                                    else:
                                        # Just the wake word — ask what they need.
                                        # Re-greet when the part of day has changed
                                        # since the startup/last greeting.
                                        g = get_day_greeting()
                                        if g != getattr(self, "_last_greet", None):
                                            self._last_greet = g
                                            nm = self.mem.profile.get("name", "").strip()
                                            self._say(f"{g} {nm}. How can I help?" if nm
                                                      else f"{g}. How can I help?")
                                        else:
                                            self._say("Yes, how can I help?")
                                        try:
                                            audio2 = self.rec.listen(
                                                source, timeout=6,
                                                phrase_time_limit=15)
                                            cmd2 = self.rec.recognize_google(
                                                audio2).lower()
                                            self._user(cmd2)
                                            self._cmd(cmd2, lang="en")
                                        except Exception:
                                            self.Q.put(("jstate", ("SLEEPING",)))
                                    break
                        except sr.UnknownValueError:
                            pass
                        except Exception as e:
                            print(f"[Wake loop] {e}")
                            time.sleep(0.5)
                    else:
                        time.sleep(0.3)
        except Exception as e:
            print(f"[Microphone] {e}")

    # ── REMINDER LOOP ─────────────────────────────────────────────────────────
    def _reminder_loop(self):
        while self.running:
            try:
                reminders = self.mem.profile.get("reminders", [])
                now       = datetime.datetime.now()
                for r in reminders:
                    if not r.get("done") and r.get("time"):
                        try:
                            rt = datetime.datetime.fromisoformat(r["time"])
                            if now >= rt:
                                self._say(f"Boss! Reminder: {r['text']}")
                                r["done"] = True
                                self.mem.save_profile()
                        except:
                            pass
            except Exception as e:
                print(f"Reminder loop: {e}")
            time.sleep(30)

    # ── SETTINGS PANEL ────────────────────────────────────────────────────────
    def _settings(self):
        win = ctk.CTkToplevel(self)
        win.title("NYX Settings")
        win.geometry("420x560")
        win.configure(fg_color="#050510")
        win.transient(self)
        win.grab_set()

        # Center settings window
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        win.geometry(f"420x560+{(sw-420)//2}+{(sh-560)//2}")

        ctk.CTkLabel(win, text="NYX SETTINGS",
                     font=("Courier New", 18, "bold"),
                     text_color="#00d4ff").pack(pady=15)
        ctk.CTkFrame(win, fg_color="#00d4ff", height=1).pack(fill="x", padx=20)

        f = ctk.CTkFrame(win, fg_color="transparent")
        f.pack(fill="x", padx=26, pady=10)

        def field(label, key, default=""):
            ctk.CTkLabel(f, text=label, text_color="#334466",
                         font=("Courier New", 11),
                         anchor="w").pack(fill="x", pady=(10, 2))
            e = ctk.CTkEntry(f, fg_color="#0a1628",
                              border_color="#00d4ff",
                              text_color="#c8e6ff",
                              height=42, corner_radius=12)
            e.insert(0, self.mem.profile.get(key, default))
            e.pack(fill="x")
            return e

        ne  = field("Your Name",              "name",    "")
        ce  = field("Default City (Weather)", "city",    "Pune")
        coe = field("Country",                "country", "India")

        ctk.CTkLabel(f, text="Wake Word Detection",
                     text_color="#334466",
                     font=("Courier New", 11),
                     anchor="w").pack(fill="x", pady=(14, 4))
        wv = ctk.BooleanVar(value=self.mem.profile.get("wake", True))
        ctk.CTkSwitch(f, text='Enable (say "Hey Nyx")',
                      variable=wv,
                      progress_color="#00d4ff").pack(anchor="w")

        # Stats
        ctk.CTkLabel(f,
                     text=f"Conversations: {len(self.mem.history)} | "
                          f"Facts: {len(self.mem.profile.get('facts', []))} | "
                          f"Notes: {len(self.mem.get_notes(100))}",
                     text_color="#334466",
                     font=("Courier New", 10)).pack(pady=(14, 0))

        def save():
            self.mem.profile.update({
                "name":    ne.get(),
                "city":    ce.get(),
                "country": coe.get(),
                "wake":    wv.get(),
            })
            self.mem.save_profile()
            win.destroy()
            self._say("Settings saved successfully Boss.")

        ctk.CTkButton(win, text="SAVE SETTINGS",
                      fg_color="#0040ff", hover_color="#0066ff",
                      height=48, font=("Courier New", 13, "bold"),
                      command=save).pack(pady=22, padx=26, fill="x")

    # ── SYSTEM TRAY / BACKGROUND MODE ─────────────────────────────────────────
    def _create_tray_icon(self):
        """Create the persistent system-tray icon (once)."""
        try:
            img = Image.new("RGB", (64, 64), (5, 5, 20))
            d   = ImageDraw.Draw(img)
            d.ellipse([4, 4, 60, 60], outline=(0, 212, 255), width=3)
            d.text((22, 18), "N", fill=(0, 212, 255))

            menu = pystray.Menu(
                pystray.MenuItem("Show Dashboard", self._show_window,
                                 default=True),
                pystray.MenuItem("Voice Mode ON", self._toggle_voice,
                                 checked=lambda i: self.input_mode == "VOICE"),
                pystray.MenuItem("Enable Auto-Start", self._toggle_autostart,
                                 checked=lambda i: self._is_autostart_enabled()),
                pystray.MenuItem("Quit NYX", self._quit_app),
            )
            self.tray_icon = pystray.Icon("NYX", img, "NYX AI Assistant", menu)
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
        except Exception as e:
            print(f"Tray icon error: {e}")

    def _hide_to_tray(self):
        """X button → hide to tray, keep running in the background.
        Speech-to-text pauses while hidden."""
        self._visible = False
        self.withdraw()

    def _show_window(self, icon=None, item=None):
        self._visible = True
        self.after(0, self.deiconify)
        self.after(10, self.lift)

    def _poll_visible(self):
        """Authoritative visibility check (runs on the main thread). STT only
        runs while the window is actually shown (not withdrawn/minimized)."""
        try:
            st = self.wm_state()   # 'normal' | 'zoomed' | 'iconic' | 'withdrawn'
            self._visible = st in ("normal", "zoomed")
        except Exception:
            pass

    def _quit_app(self, icon=None, item=None):
        self.running = False
        try:
            self._stop_speaking()
        except Exception:
            pass
        if hasattr(self, "tray_icon"):
            try:
                self.tray_icon.stop()
            except Exception:
                pass
        try:
            self.destroy()
        except Exception:
            pass
        os._exit(0)

    def _toggle_voice(self, icon=None, item=None):
        if self.input_mode == "TYPE":
            self.input_mode = "VOICE"
            try:
                self.mode_btn.configure(text="🎙  VOICE", fg_color="#0040ff")
                self._mic_btn.configure(state="normal", fg_color="#0a1628")
            except Exception:
                pass
        else:
            self.input_mode = "TYPE"
            try:
                self.mode_btn.configure(text="⌨  TYPE", fg_color="#334466")
                self._mic_btn.configure(state="disabled", fg_color="#111")
            except Exception:
                pass

    # ── AUTO-START WITH WINDOWS ────────────────────────────────────────────────
    _RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"

    def _autostart_command(self):
        script_path = os.path.abspath(sys.argv[0])
        pythonw = sys.executable.replace("python.exe", "pythonw.exe")
        if not os.path.exists(pythonw):
            pythonw = sys.executable
        # "--tray" makes the boot launch start hidden in the system tray.
        return f'"{pythonw}" "{script_path}" --tray'

    def _is_autostart_enabled(self):
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self._RUN_KEY)
            winreg.QueryValueEx(key, "NYX")
            winreg.CloseKey(key)
            return True
        except Exception:
            return False

    def _enable_autostart(self):
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self._RUN_KEY,
                                 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "NYX", 0, winreg.REG_SZ,
                              self._autostart_command())
            winreg.CloseKey(key)
            return True
        except Exception as e:
            print(f"Autostart error: {e}")
            return False

    def _disable_autostart(self):
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, self._RUN_KEY,
                                 0, winreg.KEY_SET_VALUE)
            winreg.DeleteValue(key, "NYX")
            winreg.CloseKey(key)
            return True
        except Exception:
            return False

    def _toggle_autostart(self, icon=None, item=None):
        if self._is_autostart_enabled():
            self._disable_autostart()
            self._say("Autostart disabled.")
        else:
            if self._enable_autostart():
                self._say("Autostart enabled. NYX will start when Windows boots.")
            else:
                self._say("Could not enable autostart.")

    # ── SHORTCUTS ──────────────────────────────────────────────────────────────
    def _load_shortcuts(self):
        shortcuts_file = "nyx_shortcuts.json"
        if os.path.exists(shortcuts_file):
            try:
                with open(shortcuts_file, "r", encoding="utf-8") as f:
                    return json.load(f).get("shortcuts", {})
            except Exception:
                return {}
        user = os.environ.get("USERPROFILE", os.path.expanduser("~"))
        default = {
            "shortcuts": {
                "seacure ml":  os.path.join(user, "OneDrive", "Desktop", "SEACURE_ML"),
                "my project":  os.path.join(user, "OneDrive", "Desktop", "antigravity_project"),
                "downloads":   os.path.join(user, "Downloads"),
                "desktop":     os.path.join(user, "OneDrive", "Desktop"),
                "documents":   os.path.join(user, "OneDrive", "Documents"),
            }
        }
        try:
            with open(shortcuts_file, "w", encoding="utf-8") as f:
                json.dump(default, f, indent=2)
        except Exception as e:
            print(f"Shortcuts write error: {e}")
        return default["shortcuts"]

    def open_shortcut(self, name):
        name_lower = name.lower().strip()
        self.shortcuts = self._load_shortcuts()   # reload in case user edited it
        # Exact match
        if name_lower in self.shortcuts:
            path = self.shortcuts[name_lower]
            if os.path.exists(path):
                try:
                    os.startfile(path)
                    self._say(f"Opening {name}.")
                    return True
                except Exception:
                    pass
        # Fuzzy match — all query words present in the shortcut key
        words = name_lower.split()
        for key, path in self.shortcuts.items():
            if words and all(w in key.lower() for w in words):
                if os.path.exists(path):
                    try:
                        os.startfile(path)
                        self._say(f"Opening {key}.")
                        return True
                    except Exception:
                        pass
        return False

    # ── FULL FILE SYSTEM ACCESS ────────────────────────────────────────────────
    def deep_file_search(self, filename, max_results=10):
        filename_lower = filename.lower().strip()
        found = []
        user = os.environ.get("USERPROFILE", os.path.expanduser("~"))
        priority_dirs = [
            os.path.join(user, "OneDrive", "Desktop"),
            os.path.join(user, "Desktop"),
            os.path.join(user, "Downloads"),
            os.path.join(user, "OneDrive", "Documents"),
            os.path.join(user, "Documents"),
            os.path.join(user, "Pictures"),
            os.path.join(user, "Videos"),
            os.path.join(user, "Music"),
        ]
        for drive in ["C:\\", "D:\\", "E:\\", "F:\\"]:
            if os.path.exists(drive):
                priority_dirs.append(drive)

        for search_dir in priority_dirs:
            if not os.path.exists(search_dir):
                continue
            try:
                for root, dirs, files in os.walk(search_dir):
                    dirs[:] = [d for d in dirs if not d.startswith(".")
                               and d not in ["$Recycle.Bin",
                                             "System Volume Information", "Windows",
                                             "ProgramData", "AppData"]]
                    for f in files:
                        if filename_lower in f.lower():
                            found.append(os.path.join(root, f))
                            if len(found) >= max_results:
                                return found
                    depth = root[len(search_dir):].count(os.sep)
                    if depth >= 6:
                        dirs.clear()
            except Exception:
                continue
        return found

    def read_file_content(self, filepath):
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                return f.read(5000)
        except Exception:
            return None

    def list_folder(self, path):
        try:
            items   = os.listdir(path)
            folders = [i for i in items if os.path.isdir(os.path.join(path, i))]
            files   = [i for i in items if os.path.isfile(os.path.join(path, i))]
            return folders, files
        except Exception:
            return [], []

    def _desktop_dir(self):
        """The user's REAL desktop — prefers the OneDrive-redirected Desktop so
        saved files actually appear on the visible desktop."""
        user = os.environ.get("USERPROFILE", os.path.expanduser("~"))
        for p in [os.path.join(user, "OneDrive", "Desktop"),
                  os.path.join(user, "Desktop")]:
            if os.path.exists(p):
                return p
        return user

    def _latest_screenshot(self):
        """Newest screenshot_*.png saved on the desktop, or None."""
        d = self._desktop_dir()
        try:
            shots = [os.path.join(d, f) for f in os.listdir(d)
                     if f.lower().startswith("screenshot_")
                     and f.lower().endswith(".png")]
            if shots:
                return max(shots, key=os.path.getmtime)
        except Exception:
            pass
        return None

    # ── EXECUTABLE SAFETY ─────────────────────────────────────────────────────
    def _is_safe_app(self, filepath):
        """True if an app is from a trusted / standard install location."""
        safe_dirs = ["program files", "program files (x86)",
                     "windows\\system32", "windowsapps", "microsoft",
                     "start menu"]
        fp = filepath.lower()
        return any(d in fp for d in safe_dirs)

    def _set_pending_exe(self, filepath):
        """Arm a pending exe for yes/no confirmation, auto-cancelling in 30s."""
        self.pending_exe = filepath
        self._pending_exe_time = time.time()

        def _timeout():
            if self.pending_exe == filepath and \
                    time.time() - self._pending_exe_time >= 30:
                self.pending_exe = None
                print("[NYX] Exe confirmation timed out — cancelled.")
        t = threading.Timer(30.5, _timeout)
        t.daemon = True
        t.start()


# ── ENTRY POINT ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Check Python version
    if sys.version_info < (3, 8):
        print("ERROR: Python 3.8 or higher is required.")
        sys.exit(1)

    print("=" * 50)
    print("  NYX v1.0 - Starting...")
    print("=" * 50)
    print(f"  Python: {sys.version.split()[0]}")
    print(f"  Platform: {sys.platform}")
    print(f"  DDG AI: {'Available' if DDG else 'Not installed'}")
    print(f"  Audio Control: {'Available' if AUDIO else 'Not installed'}")
    print(f"  System Monitor: {'Available' if PSUTIL else 'Not installed'}")
    print("=" * 50)

    app = Nyx()
    app.mainloop()
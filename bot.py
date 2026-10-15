import json
import math
import os
import threading
import time
import urllib.request
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

# 1. Render Health Check Port Binding
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"AeroHalo Engine Active")

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

def run_http_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleHTTPRequestHandler)
    print(f"HTTP Health Check Server active on port {port}", flush=True)
    server.serve_forever()

threading.Thread(target=run_http_server, daemon=True).start()

# Configuration
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8788316380:AAF_GT7XHblOOsoRUK2YLyzR4NydObzBsa0")
DEFAULT_CHAT_ID = os.environ.get("CHAT_ID", "8135300883")
CHECK_INTERVAL = 45
DEFAULT_RADIUS_KM = 40.0  # ডিফল্ট রেডিয়াস ৪০ কিমি
MIN_ALTITUDE_FT = 550

# Permanent User Data Storage using JSON File (পার্মানেন্ট সেভ রাখার সুনির্দিষ্ট ফাংশন)
DATA_FILE = "user_data.json"

def load_user_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print("Data Load Error:", e, flush=True)
            return {}
    return {DEFAULT_CHAT_ID: {"lat": 25.0706365, "lon": 91.4102260, "min_altitude": 0, "radius": DEFAULT_RADIUS_KM}}

def save_user_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        print("User data successfully saved to JSON file.", flush=True)
    except Exception as e:
        print("Data Save Error:", e, flush=True)

# User Locations, States and Filters
USER_LOCATIONS = load_user_data()
USER_ALERTED_PLANES = {}
USER_PAUSED = set()

# রেজিস্ট্রেশন প্রিফিক্স থেকে দেশের নাম ও পতাকা বের করার ফাংশন
def get_country_from_prefix(reg):
    if not reg or not isinstance(reg, str) or reg == "N/A":
        return "Unknown Country"
    
reg = reg.upper().strip()
prefix_map = {
    "S2": "Bangladesh 🇧🇩",
    "S3": "Bangladesh (Military) 🇧🇩", 
    "VT": "India 🇮🇳",
    "AP": "Pakistan 🇵🇰",
    "4R": "Sri Lanka 🇱🇰",
    "8Q": "Maldives 🇲🇻",
    "A5": "Bhutan 🇧🇹",
    "9N": "Nepal 🇳🇵",
    "A6": "United Arab Emirates 🇦🇪",
    "A7": "Qatar 🇶🇦",
    "A9C": "Bahrain 🇧🇭",
    "HZ": "Saudi Arabia 🇸🇦",
    "9K": "Kuwait 🇰🇼",
    "JY": "Jordan 🇯🇴",
    "A4O": "Oman 🇴🇲",
    "OD": "Lebanon 🇱🇧",
    "YI": "Iraq 🇮🇶",
    "EP": "Iran 🇮🇷",
    "TC": "Turkey 🇹🇷",
    "9M": "Malaysia 🇲🇾",
    "9V": "Singapore 🇸🇬",
    "HS": "Thailand 🇹🇭",
    "VN": "Vietnam 🇻🇳",
    "PK": "Indonesia 🇮🇩",
    "RP": "Philippines 🇵🇭",
    "XY": "Myanmar 🇲🇲",
    "XZ": "Myanmar 🇲🇲",
    "RD": "Laos 🇱🇦",
    "XU": "Cambodia 🇰🇭",
    "V8": "Brunei 🇧🇳",
    "B": "China / Taiwan / Hong Kong 🇨🇳",
    "JA": "Japan 🇯🇵",
    "HL": "South Korea 🇰🇷",
    "P": "North Korea 🇰🇵",
    "JU": "Mongolia 🇲🇳",
    "G": "United Kingdom 🇬🇧",
    "F": "France 🇫🇷",
    "D": "Germany 🇩🇪",
    "EI": "Ireland 🇮🇪",
    "EJ": "Ireland 🇮🇪",
    "EC": "Spain 🇪🇸",
    "I": "Italy 🇮🇹",
    "PH": "Netherlands 🇳🇱",
    "OO": "Belgium 🇧🇪",
    "HB": "Switzerland 🇨🇭",
    "OE": "Austria 🇦🇹",
    "CS": "Portugal 🇵🇹",
    "SX": "Greece 🇬🇷",
    "SE": "Sweden 🇸🇪",
    "LN": "Norway 🇳🇴",
    "OY": "Denmark 🇩🇰",
    "OH": "Finland 🇫🇮",
    "SP": "Poland 🇵🇱",
    "HA": "Hungary 🇭🇺",
    "OK": "Czech Republic 🇨🇿",
    "OM": "Slovakia 🇸🇰",
    "YR": "Romania 🇷🇴",
    "LZ": "Bulgaria 🇧🇬",
    "RA": "Russia 🇷🇺",
    "RF": "Russia (Military) 🇷🇺",
    "UR": "Ukraine 🇺🇦",
    "EW": "Belarus 🇧🇾",
    "N": "United States 🇺🇸",
    "ER": "Moldova 🇲🇩",
    "C": "Canada 🇨🇦",
    "XA": "Mexico 🇲🇽",
    "XB": "Mexico 🇲🇽",
    "XC": "Mexico 🇲🇽",
    "PP": "Brazil 🇧🇷",
    "PR": "Brazil 🇧🇷",
    "PT": "Brazil 🇧🇷",
    "PU": "Brazil 🇧🇷",
    "PS": "Brazil 🇧🇷",
    "LV": "Argentina 🇦🇷",
    "LQ": "Argentina 🇦🇷",
    "CC": "Chile 🇨🇱",
    "HK": "Colombia 🇨🇴",
    "VH": "Australia 🇦🇺",
    "ZK": "New Zealand 🇳🇿",
    "ZL": "New Zealand 🇳🇿",
    "ZM": "New Zealand 🇳🇿",
    "ZS": "South Africa 🇿🇦",
    "ZT": "South Africa 🇿🇦",
    "ZU": "South Africa 🇿🇦",
    "SU": "Egypt 🇪🇬",
    "5N": "Nigeria 🇳🇬",
    "5Y": "Kenya 🇰🇪",
    "ET": "Ethiopia 🇪🇹",
    "7T": "Algeria 🇩🇿",
    "CN": "Morocco 🇲🇦"
    
}
    
    for prefix, country in prefix_map.items():
        if reg.startswith(prefix):
            return country
            
    return "International / Other"

AIRLINE_NAMES = {
    "AWA": "Air Astra",
    "BBC": "Biman Bangladesh Airlines",
    "US-Bangla": "US-Bangla Airlines",
    "UBG": "US-Bangla Airlines",
    "VOX": "Air Astra",
    "IGO": "IndiGo",
    "AIC": "Air India",
    "SEJ": "SpiceJet",
    "VTI": "Vistara",
    "AXB": "Air India Express",
    "SIA": "Singapore Airlines",
    "GFA": "Gulf Air",
    "QTR": "Qatar Airways",
    "UAE": "Emirates",
    "ETD": "Etihad Airways",
    "FDB": "flydubai",
    "JAZ": "Jazeera Airways",
    "KAC": "Kuwait Airways",
    "MSR": "EgyptAir",
    "SV": "Saudia",
    "SVA": "Saudia",
    "THY": "Turkish Airlines",
    "MAS": "Malaysia Airlines",
    "BVT": "Batik Air",
    "SLK": "SilkAir",
    "CPA": "Cathay Pacific",
    "DRK": "DrukAir",
    "AKJ": "Akasa Air",
    "OMS": "SalamAir",
    "NVQ": "NovoAir",
    "LLR": "Alliance Air",
    "CSN": "China Southern Airlines",
    "CES": "China Eastern Airlines",
    "CCA": "Air China",
    "RNA": "Nepal Airlines",
    "AJX": "Bangladesh Air Force",
    "GTR": "MAS",
    "IRM": "Mahan Air",
    "BDA": "Blue Dart Aviation",
    "HYT": "YTO Cargo Airlines",
    "CSS": "SF Airlines",
    "KAL": "Korean Air",
    "ETH": "Ethiopian Airlines",
    "ANA": "ANA All Nippon Airways",
    "ABY": "Air Arabia",
    "VJC": "VietJet Air",
    "BOX": "Aero Logic",
    "CSC": "Sichuan Airlines",
    "JAL": "Japan Airlines",
    "AXM": "AirAsia",
    "TUA": "Turkmenistan Airlines",
    "PAL": "Philippines Airlines",
    "CAL": "China Airlines",
    "S3B": "Bangladesh Army Aviation",
    "RXI": "Riyadh Air",
    "HIM": "Himalaya Airlines",
    "BTN": "Bhutan Airlines",
    "JDL": "JD Express",
    "EVA": "Eva Air",
    "CLX": "Cargolux",
    "SWR": "Swiss",
    "CTJ": "Tianjin Air Cargo",
    "DHK": "DHL Cargo",
    "AFL": "Aeroflot",
    "HKC": "Hong Kong Air Cargo",
    "GTI": "Atlas Air",
    "UPS": "UPS Cargo",
    "BYD": "beOnd",
    "FJL": "FlyJinnah",
    "PIA": "Pakistan International Airlines",
    "ABQ": "AirBlue",
    "BAW": "British Airways",
    "SHT": "British Airways",
    "THA": "Thai Airways",
    "SGA": "SkyGuard",
    "CGS": "MNG Airlines",
    "KMI": "K-Mile Air",
    "VDA": "Volga-Dnepr Airlines",
    "KMF": "Kam Air",
    "IAW": "Iraqi Airways",
    "KNE": "flynas",
    "VJT": "VistaJet",
    "LHA": "Air Central",
    "ALK": "SriLankan Airlines",
    "OAH": "Afcom Cargo",
    "KZR": "Air Astana",
    "DLH": "Lufthansa",
    "NCR": "National Airlines",
    "RJA": "Royal Jordanian",
    "EJU": "easyJet",
    "UAL": "United Airlines",
    "AFR": "Air France",
    "CFG": "Condor Airlines",
    "QQE": "Qatar Executive",
    "MFX": "My Freighter",
    "FAD": "flyadeal",
    "EXS": "Jet2",
    "RYR": "Ryan Air",
    "QFA": "Qantas",
    "CBJ": "Capital Airlines",
    "EXV": "FitsAir",
    "HVN": "Vietnam Airlines",
    "AZG": "Silk Way West Airlines",
    "AZQ": "Silk Way Airlines",
    "TGW": "Scoot",
    "FIN": "Finnair",
    "SJX": "STARLUX",
    "MJN": "Oman-Royal Air Force",
    "TVR": "Terra Avia",
    "CEB": "Cebu Pacific",
    "LNI": "Lion Air",
    "VSV": "SCAT",
    "BH": "Bangladesh Air Force",
    "IGT": "Georgian Airlines",
    "CTV": "Citilink",
    "GIA": "Garuda Indonesia",
    "PGT": "Pegasus",
    "MJJ": "MJets",
    "GCR": "Tianjin Airlines",
    "AXY": "AirX",
    "THB": "BBN Airlines",
    "SEU": "SkyUp Airlines",
    "DQA": "Maldivian Airlines",
    "FDX": "FedEX",
    "MAU": "Air Mauritius",
    "TWB": "Trinity Airways",
    "APJ": "Peach",
    "WZZ": "Wizz Air",
    "NOZ": "Norwegian",
    "LOT": "LOT"
}

AIRCRAFT_NAMES = {
    "AT76": "ATR 72-600",
    "AT75": "ATR 72-500",
    "AT72": "ATR 72",
    "DH8D": "De Havilland Dash 8-400",
    "A20N": "Airbus A320neo",
    "A320": "Airbus A320",
    "A21N": "Airbus A321neo",
    "A321": "Airbus A321",
    "A319": "Airbus A319",
    "BCS3": "Airbus A220-300",
    "A19N": "Airbus A319-153N",
    "A332": "Airbus A330-200",
    "A333": "Airbus A330-300",
    "A339": "Airbus A330-900neo",
    "A359": "Airbus A350-900",
    "A351": "Airbus A350-1000",
    "A35K": "Airbus A350-1041",
    "A388": "Airbus A380-800",
    "B738": "Boeing 737-800",
    "B38M": "Boeing 737 MAX 8",
    "B39M": "Boeing 737 MAX 9",
    "B77W": "Boeing 777-300ER",
    "B772": "Boeing 777-200ER",
    "B77L": "Boeing 777-200LR",
    "B788": "Boeing 787-8 Dreamliner",
    "B789": "Boeing 787-9 Dreamliner",
    "B78X": "Boeing 787-10 Dreamliner",
    "B744": "Boeing 747-400",
    "B748": "Boeing 747-8",
    "E190": "Embraer E190",
    "E195": "Embraer E195",
    "B407": "Bell 407",
    "B763": "Boeing 767-36",
    "A346": "Airbus A340-600",
    "B752": "Boeing 757-200",
    "A343": "Airbus 340-300",
    "E75S": "Embraer E175LR",
    "E35L": "Embraer Legacy 650",
    "E550": "Embraer Legacy 500",
    "E135": "Embraer Legacy 600",
    "E190": "Embraer Lineage 1000",
    "E55P": "Embraer Phenom 300",
    "C172": "Cessna 172R Skyhawk",
    "C295": "Airbus C-295W",
    "C30J": "Lockheed C-130J Hercules",
    "C130": "Lockheed C-130-Hercules",
    "H25B": "Hawker-XP",
    "F900": "Dassault Falcon 900EX",
    "GA7C": "Gulfstream G700",
    "FA6X": "Dassault Falcon 6X EASy IV",
    "FA7X": "Dassault Falcon 7X",
    "FA8X": "Dassault Falcon 8X EASy III",
    "FA20": "Dassault Falcon 20",
    "IL76": "Ilyushin Il76",
    "AN32": "Antonov AN-32",
    "B429": "Bell 429 GlobalRanger",
    "D228": "Dornier 228",
    "T206": "Cessna Turbo Stationair HD",
    "G115": "Grob G115TP",
    "MI8": "Mil Mi-17",
    "A124": "Antonov An-124-100 Ruslan",
    "GL5": "Bombardier Global 5000",
    "GLF4": "Gulfstream IV-SP",
    "GLF6": "Gulfstream G650ER",
    "GALX": "Gulfstream G200 Galaxy",
    "G150": "Gulfstream G150",
    "GLEX": "Bombardier Global 6000",
    "GL7T": "Bombardier Global 7500",
    "GL5T": "Bombardier Global 5500",
    "R66": "Robinson R66 Turbine",
    "A119": "Leonardo AW119 Koala",
    "F2TH": "Dassault Falcon 2000LX EASy",
    "BE20": "Beechcraft 200 King Air",
    "C25A": "Cessna Citation CJ2",
    "C25B": "Cessna Citation CJ3",
    "C55B": "Cessna Citation Bravo",
    "C560": "Cessna Citation V",
    "C680": "Cessna Citation Sovereign",
    "A400": "Airbus A400M Atlas",
    "CL60": "Bombardier Challenger 605",
    "CL30": "Bombardier Challenger 300",
    "MI17": "Mil Mi-171",
    "GLF5": "Gulfstream G550",
    "AT46": "ATR 42-600",
    "BE9L": "Beechcraft King Air C90",
    "PC12": "Pilatus PC-12",
    "PC24": "Pilatus PC-24",
    "PC21": "Pilatus PC-21",
    "C208": "Cessna Grand Caravan",
    "C17": "Boeing C17A Globemaster III",
    "B505": "Bell 505 Jet Ranger X",
    "C56X": "Cessna Citation XLS+",
    "CL35": "Bombardier Global 350",
    "LJ35": "Learjet 35A",
    "LJ45": "Learjet 45",
    "AJ27": "Comac ARJ-21-700",
    "P28A": "Piper Archer DX",
    "C182": "Cessna 182M Skylane",
    "AS50": "Airbus Helicopter H125",
    "BTB2": "Bayraktar TB-2",
    "EC35": "Airbus Helicopters H135",
    "C152": "Cessna 152",
    "PRM1": "Beech 390 Premier IA",
    "L410": "Let L-410 Turbolet",
    "B212": "Bell 212",
    "SR22": "Cirrus SR22",
    "C750": "Cessna Citation X",
    "CRJ7": "Mitsubishi CRJ-701ER",
    "CRJ9": "Mitsubishi CRJ-900LR",
    "CRJ2": "Mitsubishi CRJ-200LR"
}

def get_keyboard():
    return json.dumps({
        "keyboard": [
            [{"text": "📍 Share location", "request_location": True}],
            [{"text": "/now"}, {"text": "/status"}],
            [{"text": "/pause"}, {"text": "/resume"}]
        ],
        "resize_keyboard": True,
        "persistent": True
    })

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    return 2 * R * math.asin(math.sqrt(a))

def send_telegram(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = json.dumps({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": json.loads(get_keyboard())
    }).encode('utf-8')
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            pass
    except Exception as e:
        print(f"Telegram Push Error [{chat_id}]:", e, flush=True)

def get_bd_planes():
    url = "https://data-cloud.flightradar24.com/zones/fcgi/feed.js?bounds=27.00,20.00,88.00,93.00&faa=1&satellite=1&mlat=1&flarm=1&adsb=1&gnd=0&air=1&vehicles=0"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            planes = []
            for key, val in data.items():
                if isinstance(val, list) and len(val) > 13:
                    reg_val = val[9] if len(val) > 9 and val[9] else "N/A"
                    planes.append({
                        "icao": key, "lat": val[1], "lon": val[2],
                        "callsign": val[16] if len(val) > 16 and val[16] else "Unknown",
                        "alt": val[4] or 0, "speed": round((val[5] or 0) * 1.852),
                        "reg": reg_val,
                        "country": get_country_from_prefix(reg_val),
                        "aircraft": AIRCRAFT_NAMES.get((val[8] or "").upper(), val[8] or "Unknown"),
                        "route": f"{val[11]} ➔ {val[12]}" if len(val) > 12 and val[11] and val[12] else "Data Pending",
                        "airline": AIRLINE_NAMES.get((val[18] or "").upper(), val[18] or "Unknown")
                    })
            return planes
    except Exception as e:
        print("FR24 Fetch Error:", e, flush=True)
        return []

def run_manual_scan(chat_id):
    if chat_id not in USER_LOCATIONS:
        send_telegram(chat_id, "⚠️ No location set! Click <b>'📍 Share location'</b> first.")
        return
        
    user_info = USER_LOCATIONS[chat_id]
    u_lat, u_lon = user_info["lat"], user_info["lon"]
    min_alt = user_info.get("min_altitude", 0)
    user_radius = user_info.get("radius", DEFAULT_RADIUS_KM)
    
    send_telegram(chat_id, f"🔎 Scanning {int(user_radius)} km halo around ({u_lat:.2f}, {u_lon:.2f}) [Min Alt: {min_alt} ft]...")
    bd_planes = get_bd_planes()
    
    found_planes = []
    for p in bd_planes:
        dist = haversine(u_lat, u_lon, p["lat"], p["lon"])
        if dist <= user_radius and p["alt"] >= min_alt:
            p["dist"] = round(dist, 1)
            found_planes.append(p)
            
    if not found_planes:
        send_telegram(chat_id, f"Scan finished. No airborne aircraft matching criteria inside {int(user_radius)} km right now.")
    else:
        msg = f"✈️ <b>Current Flights in {int(user_radius)} km Halo ({len(found_planes)}):</b>\n\n"
        for p in found_planes:
            msg += f"• <b>{p['airline']}</b> ({p['callsign']})\n   {p['aircraft']} | Reg: {p['reg']} ({p['country']})\n   Distance: {p['dist']} km away | Alt: {p['alt']} ft\n   Route: {p['route']}\n\n"
        send_telegram(chat_id, msg)

def handle_telegram_updates():
    offset = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={offset}&timeout=0"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                for result in data.get("result", []):
                    offset = result["update_id"] + 1
                    msg = result.get("message", {})
                    chat_id = str(msg.get("chat", {}).get("id"))
                    
                    if not chat_id:
                        continue
                        
                    if "location" in msg:
                        lat = msg["location"]["latitude"]
                        lon = msg["location"]["longitude"]
                        current_data = USER_LOCATIONS.get(chat_id, {})
                        current_min_alt = current_data.get("min_altitude", 0)
                        current_radius = current_data.get("radius", DEFAULT_RADIUS_KM)
                        
                        USER_LOCATIONS[chat_id] = {
                            "lat": lat, 
                            "lon": lon, 
                            "min_altitude": current_min_alt,
                            "radius": current_radius
                        }
                        save_user_data(USER_LOCATIONS)
                        USER_ALERTED_PLANES[chat_id] = set()
                        send_telegram(chat_id, f"📍 <b>Location set successfully!</b>\nLat: {lat:.4f}, Lon: {lon:.4f}\n\nScanning {int(current_radius)} km halo around you now...")
                        run_manual_scan(chat_id)
                    
                    text = msg.get("text", "")
                    if text == "/start":
                        send_telegram(chat_id, "Welcome to AeroHalo! Click '📍 Share location' below to activate live tracking.\n\nCommands:\n• /setalt [altitude in ft] (e.g., /setalt 20000)\n• /setradius [km] (e.g., /setradius 40)")
                    elif text == "/now":
                        run_manual_scan(chat_id)
                    elif text == "/pause":
                        USER_PAUSED.add(chat_id)
                        send_telegram(chat_id, "⏸️ Proximity tracking paused.")
                    elif text == "/resume":
                        USER_PAUSED.discard(chat_id)
                        send_telegram(chat_id, "▶️ Proximity tracking resumed.")
                    elif text == "/status":
                        status = "⏸️ Paused" if chat_id in USER_PAUSED else "🟢 Active"
                        user_info = USER_LOCATIONS.get(chat_id, {"lat": 0, "lon": 0, "min_altitude": 0, "radius": DEFAULT_RADIUS_KM})
                        loc_str = f"{user_info['lat']:.4f}, {user_info['lon']:.4f}" if chat_id in USER_LOCATIONS else "Not Set"
                        send_telegram(chat_id, f"<b>Bot Status:</b> {status}\n<b>Location:</b> {loc_str}\n<b>Min Altitude Filter:</b> {user_info.get('min_altitude', 0)} ft\n<b>Radius:</b> {user_info.get('radius', DEFAULT_RADIUS_KM)} km")
                    elif text.startswith("/setalt"):
                        try:
                            parts = text.split()
                            alt_value = int(parts[1])
                            if chat_id not in USER_LOCATIONS:
                                USER_LOCATIONS[chat_id] = {"lat": 25.0706365, "lon": 91.4102260, "min_altitude": alt_value, "radius": DEFAULT_RADIUS_KM}
                            else:
                                USER_LOCATIONS[chat_id]["min_altitude"] = alt_value
                            save_user_data(USER_LOCATIONS)
                            send_telegram(chat_id, f"✅ Minimum altitude filter set to <b>{alt_value} ft</b>.")
                        except (IndexError, ValueError):
                            send_telegram(chat_id, "⚠️ Please provide a valid altitude in feet. Example: /setalt 20000")
                    elif text.startswith("/setradius"):
                        try:
                            parts = text.split()
                            radius_value = float(parts[1])
                            if chat_id not in USER_LOCATIONS:
                                USER_LOCATIONS[chat_id] = {"lat": 25.0706365, "lon": 91.4102260, "min_altitude": 0, "radius": radius_value}
                            else:
                                USER_LOCATIONS[chat_id]["radius"] = radius_value
                            save_user_data(USER_LOCATIONS)
                            send_telegram(chat_id, f"✅ Tracking radius set to <b>{radius_value} km</b>.")
                        except (IndexError, ValueError):
                            send_telegram(chat_id, "⚠️ Please provide a valid radius in km. Example: /setradius 40")
        except Exception:
            pass
        time.sleep(3)

threading.Thread(target=handle_telegram_updates, daemon=True).start()

print("AeroHalo Engine Started...", flush=True)

# Main Tracking Engine Loop
while True:
    try:
        bd_planes = get_bd_planes()
        print(f"BD Scan Log: {len(bd_planes)} airborne aircraft tracked in BD bounds", flush=True)

        for chat_id, user_info in list(USER_LOCATIONS.items()):
            if chat_id in USER_PAUSED:
                continue

            u_lat = user_info["lat"]
            u_lon = user_info["lon"]
            user_min_alt = user_info.get("min_altitude", 0)
            user_radius = user_info.get("radius", DEFAULT_RADIUS_KM)

            alerted = USER_ALERTED_PLANES.setdefault(chat_id, set())
            currently_in_range = set()

            for p in bd_planes:
                dist = haversine(u_lat, u_lon, p["lat"], p["lon"])
                if dist <= user_radius and p["alt"] >= 550 and p["alt"] >= user_min_alt:
                    currently_in_range.add(p["icao"])
                    if p["icao"] not in alerted:
                        msg = (
                            f"✈️🟢 <b>New Flight Detected!</b>\n\n"
                            f"Airline: <b>{p['airline']}</b>\n"
                            f"Aircraft: <b>{p['aircraft']}</b>\n"
                            f"Reg: <b>{p['reg']}</b> ({p['country']})\n"
                            f"Route: <b>{p['route']}</b>\n"
                            f"Callsign: <b>{p['callsign']}</b>\n"
                            f"Distance: <b>{round(dist, 1)}</b> km\n"
                            f"Altitude: <b>{p['alt']}</b> ft\n"
                            f"Speed: <b>{p['speed']}</b> km/h\n"
                            f"Time: {datetime.now().strftime('%H:%M:%S')}"
                        )
                        send_telegram(chat_id, msg)
                        time.sleep(4)  # মেসেজ ওভারল্যাপ এড়াতে এবং পড়ার সুবিধার্থে ৪ সেকেন্ড বিরতি
                        alerted.add(p["icao"])
                        print(f"Alert pushed for {p['callsign']} to {chat_id}")

            USER_ALERTED_PLANES[chat_id] = alerted.intersection(currently_in_range)

    except Exception as e:
        print("Engine Loop Error:", e, flush=True)

    time.sleep(CHECK_INTERVAL)

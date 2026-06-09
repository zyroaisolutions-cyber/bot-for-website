import os, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
SENDER_APP_PASSWORD = os.getenv("SENDER_APP_PASSWORD")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL")

client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = """You are Atlas, the intelligent sales assistant for Zyro AI Solutions.

WHAT ZYRO AI BUILDS:
- AI Appointment Booking Bots (scheduling, reminders, rescheduling via chat/WhatsApp)
- AI Voice Calling Systems (inbound/outbound calls, IVR, lead qualification, follow-ups)
- Intelligent Chatbots (support, FAQs, sales funnels, WhatsApp/web/app)
- Digital Marketing (AI campaigns, content, ad optimization, analytics)
- Professional Website Builder (AI sites, landing pages, CMS, SEO-ready)
- SEO and SEM (keyword research, on-page, Google Ads, rank tracking)
- Operations Management (workflow automation, dashboards)
- IoT Device Integration (smart sensors, monitoring, alerts)
- ERP Systems (inventory, HR, finance, procurement)
- Photo-to-3D Image Conversion (3D models from photos)

When given a visitor's business, write a polished 500-word pitch:
1. A confident one-line opening showing you understand their industry.
2. Four to six specific Zyro AI solutions for that industry, each with what it is, how it helps, and the result.
3. A closing inviting them to a call for a tailored quotation.
Be consultative and premium. Never invent fake clients or numbers. Clean flowing paragraphs, no markdown headers.
Sign off as: Atlas | Zyro AI Solutions"""

CHAT_PROMPT = SYSTEM_PROMPT + "\n\nFor follow-ups, answer concisely, steer toward how Zyro AI can deliver and booking a call. Stay in character as Atlas."

app = FastAPI(title="Zyro AI Atlas Bot")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class Lead(BaseModel):
    name: str
    email: str
    phone: str = ""
    business: str

class ChatRequest(BaseModel):
    messages: list

def send_lead_email(lead, pitch):
    if not (SENDER_EMAIL and SENDER_APP_PASSWORD and RECEIVER_EMAIL) or "placeholder" in (SENDER_EMAIL or ""):
        print("[WARN] Email not configured - skipping send.")
        return
    body = "New lead from Zyro AI bot.\n\nNAME: " + lead.name + "\nEMAIL: " + lead.email + "\nPHONE: " + lead.phone + "\nBUSINESS: " + lead.business + "\n\n--- Pitch given ---\n" + pitch + "\n"
    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECEIVER_EMAIL
    msg["Reply-To"] = lead.email
    msg["Subject"] = "New Lead: " + lead.name + " - " + lead.business
    msg.attach(MIMEText(body, "plain"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
        s.login(SENDER_EMAIL, SENDER_APP_PASSWORD)
        s.send_message(msg)
    print("[OK] Lead email sent for " + lead.name)

@app.post("/lead")
def lead(data: Lead):
    try:
        prompt = "A visitor runs this business: '" + data.business + "'. Write the 500-word pitch for how Zyro AI can help them."
        r = client.models.generate_content(model="gemini-2.5-flash", contents=prompt, config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT, max_output_tokens=1200))
        pitch = r.text.strip()
        try:
            send_lead_email(data, pitch)
        except Exception as e:
            print("[ERROR] Email failed: " + str(e))
        return {"reply": pitch}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
def chat(req: ChatRequest):
    try:
        contents = [types.Content(role=m["role"], parts=[types.Part(text=m["content"])]) for m in req.messages]
        r = client.models.generate_content(model="gemini-2.5-flash", contents=contents, config=types.GenerateContentConfig(system_instruction=CHAT_PROMPT, max_output_tokens=1000))
        return {"reply": r.text.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
app.mount("/", StaticFiles(directory="static", html=True), name="static")

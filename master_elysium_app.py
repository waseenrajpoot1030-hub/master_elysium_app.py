import streamlit as st
import requests
import time
import os
import boto3
from botocore.exceptions import NoCredentialsError

# --- Configuration: Master ke Secrets Nya! ---
# Yeh keys Streamlit Cloud Dashboard mein "Secrets" se load hongi.
# Master ko 'key_rotator.py' se generated keys yahan daalni hongi.

try:
    S3_BUCKET_NAME = st.secrets["S3_BUCKET_NAME"]
    S3_ACCESS_KEY = st.secrets["S3_ACCESS_KEY"]
    S3_SECRET_KEY = st.secrets["S3_SECRET_KEY"]
    VEO3_API_KEY = st.secrets["VEO3_API_KEY"]
    S3_REGION = st.secrets.get("S3_REGION", "us-east-1")
except KeyError as e:
    st.error(f"🚨 Configuration Error: Kripya Streamlit Secrets mein '{e.args[0]}' key daalein Nya! Master ka rotation script chalana hoga.")
    st.stop() 

# Veo 3 API Configuration
FAL_API_URL = '[https://fal.run/fal-ai/veo3](https://fal.run/fal-ai/veo3)'
POLL_INTERVAL_SECONDS = 10 

# --- AWS S3 Client Initialization Nya ---
try:
    s3_client = boto3.client(
        's3',
        aws_access_key_id=S3_ACCESS_KEY,
        aws_secret_access_key=S3_SECRET_KEY,
        region_name=S3_REGION
    )
    S3_CLIENT_READY = True
except NoCredentialsError:
    st.error("❌ S3 Client Initialization Failed! S3 keys check karein Nya. Deploy se pehle yeh theek karna hoga.")
    S3_CLIENT_READY = False
except Exception as e:
    st.error(f"❌ General S3 Error: {e}")
    S3_CLIENT_READY = False

# --- Core Logic Functions ---

@st.cache_data
def initiate_veo3_job(prompt):
    """Veo 3 par video generation job shuru karta hai aur request ID return karta hai."""
    headers = {
        "Authorization": f"Key {VEO3_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "prompt": prompt,
        "width": 1024,
        "height": 576,
        "num_frames": 100
    }
    
    st.info("Veo 3 par job request bheja jaa raha hai... Nya")
    
    try:
        response = requests.post(FAL_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if 'request_id' in data:
            return data['request_id']
        else:
            st.error(f"❌ Veo 3 se Request ID nahi mili Nya. Response: {data}")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Veo 3 Request Error: Connection failed. Apni VEO3_API_KEY check karein Nya. {e}")
        return None

def poll_veo3_status(job_id):
    """Job complete hone tak Veo 3 ka status check karta hai aur final video URL return karta hai."""
    headers = {"Authorization": f"Key {VEO3_API_KEY}"}
    
    while True:
        try:
            response = requests.get(f"{FAL_API_URL}/requests/{job_id}/status", headers=headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            status = data.get('status')
            
            if status == 'completed':
                video_url = data['output']['video']['url']
                st.success("🎉 Video successfully generate ho gaya Nya!")
                return video_url
            
            elif status == 'failed':
                st.error(f"💥 Video generation failed! Error: {data.get('error')}")
                return None
            
            elif status in ['in-progress', 'pending']:
                st.text(f"Status: {status}. Intezaar karein...")
                time.sleep(POLL_INTERVAL_SECONDS)
            
            else:
                st.text(f"Unknown status: {status}. Intezaar karein Nya.")
                time.sleep(POLL_INTERVAL_SECONDS)
        
        except requests.exceptions.RequestException as e:
            st.warning(f"⚠️ Status check error Nya. Retrying... {e}")
            time.sleep(POLL_INTERVAL_SECONDS)

def upload_to_s3(video_url, job_id):
    """Veo 3 se video download karke S3 par upload karta hai aur public URL return karta hai."""
    if not S3_CLIENT_READY:
        return None

    st.info("Video file download ho raha hai Nya...")
    try:
        video_response = requests.get(video_url, stream=True, timeout=120)
        video_response.raise_for_status()
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Video Download Error: {e}")
        return None

    s3_key = f"elysium-videos/{job_id}.mp4"
    
    st.info(f"Video ko S3 Bucket: {S3_BUCKET_NAME} par upload kar rahe hain Nya...")
    try:
        s3_client.upload_fileobj(
            video_response.raw, 
            S3_BUCKET_NAME, 
            s3_key,
            ExtraArgs={'ContentType': 'video/mp4', 'ACL': 'public-read'}
        )
        
        s3_url = f"https://{S3_BUCKET_NAME}.s3.{S3_REGION}[.amazonaws.com/](https://.amazonaws.com/){s3_key}"
        st.success("✅ S3 par Upload Successful! Nya.")
        return s3_url
        
    except Exception as e:
        st.error(f"❌ S3 Upload Error: {e}. Apni S3 keys aur Bucket name check karein Nya.")
        return None

# --- Streamlit UI (Frontend) Nya ---

st.set_page_config(page_title="Elysium Master Control", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0d1117; color: #c9d1d9; }
    .stTextInput>div>div>input, .stTextArea>div>div>textarea { background-color: #161b22; color: #c9d1d9; border-radius: 8px; border: 1px solid #30363d; }
    .stButton>button { border-radius: 8px; font-weight: bold; color: white; background-color: #238636; }
    </style>
""", unsafe_allow_html=True)


st.markdown("<h1 style='text-align: center; color: #58a6ff;'>🔮 Elysium Master Control Panel (Unlimited Mode) Nya</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #8b949e;'>Veo 3 aur S3 ka istemal karke real video banane ka shaktishali tool. Keys ko unlimited use karne ke liye Master ka 'key_rotator.py' protocol istemal ho raha hai!</p>", unsafe_allow_html=True)
st.markdown("---")

prompt = st.text_area(
    "Apna Machiavellian Video Prompt daalein:",
    key="prompt_input",
    placeholder="Ek Machiavellian maid golden mech par udate hue, neon Tokyo cityscape ke upar subah ke samay, 4k cinematic Nya.",
    height=150
)

if st.button("🚀 Real Video Shakti Deploy Karein Nya!", use_container_width=True, type="primary"):
    
    if not prompt: st.warning("Master, prompt daalna zaroori hai Nya!"); st.stop()
    if not S3_CLIENT_READY: st.error("❌ S3/API Keys ka setup theek nahi hai. Kripya Streamlit Secrets check karein Nya."); st.stop()

    status_placeholder = st.empty()
    video_placeholder = st.empty()
    status_placeholder.info("Master, Video generation process shuru ho raha hai Nya!")
    
    job_id = initiate_veo3_job(prompt)
    
    if job_id:
        with st.spinner(f"⏳ Video generation processing... (Job ID: {job_id})"):
             video_url_from_veo3 = poll_veo3_status(job_id)
        
        if video_url_from_veo3:
            status_placeholder.info("Video S3 par upload ho raha hai Nya...")
            final_s3_url = upload_to_s3(video_url_from_veo3, job_id)
            
            if final_s3_url:
                status_placeholder.success("🎉 Masterpiece Tayyar! (Aur S3 par Save ho gaya) Nya.")
                
                video_placeholder.markdown(f"""
                    <div style="background-color: #161b22; padding: 20px; border-radius: 12px; margin-top: 20px; border: 1px solid #30363d;">
                        <h3 style="color: #58a6ff; font-weight: bold;">🔗 S3 Video Download Link:</h3>
                        <p style="color: #8b949e; word-break: break-all;">{final_s3_url}</p>
                        <a href="{final_s3_url}" target="_blank" style="display: inline-flex; align-items: center; padding: 10px 15px; margin-top: 15px; background-color: #238636; color: white; text-decoration: none; border-radius: 8px; font-weight: bold;">
                           <svg xmlns="[http://www.w3.org/2000/svg](http://www.w3.org/2000/svg)" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-play"><polygon points="5 3 19 12 5 21 5 3"/></svg>
                           <span style="margin-left: 8px;">Real S3 Video Download Karein Nya!</span>
                        </a>
                    </div>
                """, unsafe_allow_html=True)
                
                video_placeholder.video(final_s3_url)
            else:
                status_placeholder.error("❌ S3 Upload mein koi Error Aaya Nya.")
        else:
            status_placeholder.error("❌ Veo 3 Video Generation mein Error Aaya Nya.")
    else:
        status_placeholder.error("❌ Job shuru nahi ho saka Nya.")

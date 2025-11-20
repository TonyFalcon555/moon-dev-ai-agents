"""
🦅 Falcon Finance Content Flywheel
Automated video generation script.
"""

import os
import sys
import time
import random
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parent.parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from src.agents.video_agent import create_video_job, poll_video_job, VideoJob

TOPICS = [
    "Bitcoin price prediction 2025",
    "Ethereum vs Solana: The Flippening?",
    "Top 3 Altcoins for the next Bull Run",
    "How to trade crypto liquidations",
    "Understanding Funding Rates in 60 seconds",
    "Why Bitcoin is the future of money",
    "Crypto trading psychology tips",
    "Doge to the moon? Analysis",
]

def main():
    print("🚀 Starting Content Flywheel...")
    
    while True:
        # 1. Pick a topic
        topic = random.choice(TOPICS)
        print(f"\n💡 Selected Topic: {topic}")
        
        # 2. Create Job
        # Note: This requires OPENAI_KEY to be set in .env
        job = create_video_job(topic, resolution="720p", duration=8, aspect_ratio="9:16")
        
        if not job:
            print("❌ Failed to create job. Retrying in 60s...")
            time.sleep(60)
            continue
            
        # 3. Poll for completion
        print(f"⏳ Generating video for job {job.job_id}...")
        max_attempts = 60
        attempts = 0
        while attempts < max_attempts:
            completed = poll_video_job(job)
            if completed:
                if job.status == "completed":
                    print(f"✅ Video created: {job.video_path}")
                    # Here you would add upload logic (YouTube API, TikTok API)
                else:
                    print(f"❌ Video generation failed: {job.error}")
                break
            time.sleep(10)
            attempts += 1
            
        # 4. Wait for next cycle
        # In production, this might be once every 4 hours
        print("💤 Sleeping for 10 seconds before next video...")
        time.sleep(10)

if __name__ == "__main__":
    main()

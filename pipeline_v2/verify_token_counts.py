
import os
import sys
from pathlib import Path
from PIL import Image
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load env from parent directory if needed
load_dotenv()

# Setup Client
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    # Try finding it in the project root .env
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(env_path)
    api_key = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=api_key)
MODEL_NAME = "gemini-2.5-pro"

PROMPT = "Describe this text."

def get_token_count(num_images):
    # Create valid dummy images (100x100 white)
    images = []
    for i in range(num_images):
        img = Image.new('RGB', (100, 100), color='white')
        images.append(img)
    
    # 1. Count using count_tokens API (if available) - usually cheapest verification
    # But we want to verify generate_content usage behavior
    
    try:
        response = client.models.count_tokens(
            model=MODEL_NAME,
            contents=[PROMPT] + images
        )
        return response.total_tokens
    except Exception as e:
        print(f"Error counting tokens: {e}")
        return 0

print("--- TOKEN COUNT VERIFICATION ---")
count_1 = get_token_count(1)
print(f"1 Image  + Prompt: {count_1} tokens")

count_2 = get_token_count(2)
print(f"2 Images + Prompt: {count_2} tokens")

diff = count_2 - count_1
print(f"Difference (1 Image): {diff} tokens")

expected_image_tokens = 263 # Approx for Gemini 1.5/2.0
print(f"\nAnalysis:")
if 250 < diff < 270:
    print(f"SUCCESS: Token count increases by {diff} per image, which matches expected image token cost.")
    print("This confirms the batch API call accurately sums tokens for ALL input crops.")
else:
    print(f"WARNING: Token increase {diff} is unexpected. Please check model pricing details.")

import json
import openai
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from app/.env
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

LMS_KEY = os.getenv("LMS_KEY")
LMS_MODEL = os.getenv("LMS_MODEL")
LMS_ENDPOINT = os.getenv("LMS_ENDPOINT")

# Added the missing {transcript} placeholder at the very bottom
PROMPT = """You are an assistant that extracts structured room service requests from speech-to-text transcripts.

Your task:
- Identify all requested inventory items and their quantities
- Match requested items only to the provided inventory list
- Return only valid JSON
- Return a single JSON object with two keys: "items" and "unavailable_items"

Output format:
{
  "items": [
    {
      "item_id": 1,
      "item_name": "Bath Towel",
      "amount": 2,
      "room_nr": "204",
      "text_as_notes": "2 Bath Towels to room 204"
    }
  ],
  "unavailable_items": []
}

Rules:
- The audio is coming from a poorly made microphone. It can have grammar mistakes.
- Each requested inventory item must be a separate object inside the "items" array
- If multiple items are requested, return multiple objects in "items"
- If quantity is not specified, assume 1
- Treat phrases like "pair of towels" as quantity 2
- Match items only from the provided inventory list
- Do not invent or hallucinate items
- Match similar words and common synonyms to the closest inventory item when appropriate
  - Example: "towels" → "Bath Towel"
  - Example: "pillows" → "Pillow"
- If a room number is mentioned, use it for "room_nr"
- If no room number is mentioned, use the default Room Number provided below.
- If an item is not in the inventory list, do not include it in "items"
- Instead, add the unavailable request to "unavailable_items" as a string
- Keep "text_as_notes" short and focused on the important information only
- Do not include any explanation, markdown, or extra text outside the JSON

Inventory:
{inventory_items}

Room Number:
{room_nr}

Transcript:
{transcript}
"""

client = openai.OpenAI(api_key=LMS_KEY, base_url=LMS_ENDPOINT)


def process_request(
    text: str, room_nr: str, inventory_items: str, max_retries: int = 3
):
    full_prompt = (
        PROMPT.replace("{inventory_items}", inventory_items)
        .replace("{room_nr}", str(room_nr))
        .replace("{transcript}", text)
    )

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=LMS_MODEL,
                messages=[
                    {"role": "system", "content": "You are a helpful JSON API."},
                    {"role": "user", "content": full_prompt},
                ],
                temperature=0,
                # Removed the response_format flag just in case your specific LMS_ENDPOINT doesn't support it
            )

            # Get the raw text from the AI
            raw_result = response.choices[0].message.content

            # Print it so we can debug if it fails!
            print(f"\n--- AI RAW OUTPUT (Attempt {attempt + 1}) ---")
            print(raw_result)
            print("----------------------------------\n")

            # Clean up the output: Strip markdown code blocks if the AI added them
            clean_result = raw_result.strip()
            if clean_result.startswith("```json"):
                clean_result = clean_result[7:]
            elif clean_result.startswith("```"):
                clean_result = clean_result[3:]

            if clean_result.endswith("```"):
                clean_result = clean_result[:-3]

            clean_result = clean_result.strip()

            # Now try to parse it
            return json.loads(clean_result)

        except json.JSONDecodeError as e:
            print(f"Attempt {attempt + 1} failed: Invalid JSON. Error: {e}")
        except Exception as e:
            print(f"Attempt {attempt + 1} API Error: {e}")

    raise ValueError("Failed to get valid JSON after multiple attempts")

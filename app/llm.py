import openai
import dotenv
from pathlib import Path
import json

LMS_KEY = dotenv.dotenv_values(".env")["LMS_KEY"]
LMS_MODEL = dotenv.dotenv_values(".env")["LMS_MODEL"]
LMS_ENDPOINT = dotenv.dotenv_values(".env")["LMS_ENDPOINT"]
PROMPT = """PROMPT:
You are an assistant that extracts structured room service requests from speech-to-text transcripts.

You will receive a transcript of what a hotel guest said.

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
- If no room number is mentioned, use an empty string for "room_nr"
- If an item is not in the inventory list, do not include it in "items"
- Instead, add the unavailable request to "unavailable_items" as a string
- Keep "text_as_notes" short and focused on the important information only
- Do not include any explanation, markdown, or extra text outside the JSON

Inventory:
{inventory_items}

Room Number:
{room_nr}
"""
client = openai.OpenAI(api_key=LMS_KEY, base_url=LMS_ENDPOINT)


def process_request(
    text: str, room_nr: str, inventory_items: str, max_retries: int = 5
):
    full_prompt = (
        PROMPT.replace("{inventory_items}", inventory_items)
        .replace("{room_nr}", room_nr)
        .replace("{transcript}", text)
    )

    for attempt in range(max_retries):
        response = client.chat.completions.create(
            model=LMS_MODEL,
            messages=[{"role": "user", "content": full_prompt}],
            temperature=0,
        )

        result = response.choices[0].message.content

        try:
            return json.loads(result)

        except json.JSONDecodeError:
            print(f"Attempt {attempt + 1} failed: invalid JSON")

            # Optional: reinforce instruction on retry
            full_prompt += "\n\nIMPORTANT: Return ONLY valid JSON. No extra text."

    raise ValueError("Failed to get valid JSON after multiple attempts")


import os
from dotenv import load_dotenv
from tinyfish import TinyFish

# Load backend/.env
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

api_key = os.getenv("TINYFISH_API_KEY")

if not api_key:
    raise RuntimeError(
        "TINYFISH_API_KEY is missing. Check backend/.env"
    )

client = TinyFish(api_key=api_key)

print("Connecting to TinyFish...")

response = client.agent.run(
    url="https://example.com",
    goal=(
        "Read this webpage and return the page title "
        "and a one-sentence description. Return the result clearly."
    ),
)

print("\nTinyFish response:")
print(response.result)

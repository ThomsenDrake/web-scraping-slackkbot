import os
import csv
import logging
from dotenv import load_dotenv
from scrapegraphai.graphs import SmartScraperGraph
from scrapegraphai.utils import prettify_exec_info
from openai import OpenAI

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

openai_key = os.getenv("OPENAI_APIKEY")
if not openai_key:
    raise ValueError("OpenAI API key not found. Please set the OPENAI_APIKEY environment variable.")

client = OpenAI(api_key=openai_key)

graph_config = {
    "llm": {
        "api_key": openai_key,
        "model": "openai/gpt-4o-mini",
    },
}

def generate_csv_filename(prompt, content):
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "developer", "content": "You are a helpful assistant."},
            {
                "role": "user",
                "content": f"Generate a relevant and useful filename for a CSV file based on the following prompt and content. Only return the filename without any additional text:\n\nPrompt: {prompt}\nContent: {content}\n\nFilename:"
            }
        ]
    )
    filename = completion.choices[0].message.content.strip()
    filename = filename.replace('"', '').replace("'", "")  # Remove quotes
    if filename.endswith(".csv"):
        filename = filename[:-4]  # Remove the existing .csv extension
    filename += ".csv"
    return filename

def main():
    prompt = input("Enter the prompt for scraping: ")
    url = input("Enter the URL of the webpage to scrape: ")

    logging.info("Creating SmartScraperGraph instance...")
    smart_scraper_graph = SmartScraperGraph(
        prompt=prompt,
        source=url,
        config=graph_config
    )

    logging.info("Running SmartScraperGraph...")
    result = smart_scraper_graph.run()
    logging.info("SmartScraperGraph run completed.")
    logging.info(f"Result: {result}")

    # Save results to CSV
    logging.info("Saving results to CSV...")
    csv_filename = generate_csv_filename(prompt, result)
    if not csv_filename.endswith(".csv"):
        csv_filename += ".csv"

    # Find the first list in the result dictionary
    items = []
    for key, value in result.items():
        if isinstance(value, list):
            items = value
            break

    if items:
        keys = items[0].keys()  # Get the keys from the first item

        with open(csv_filename, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(keys)  # Write the header row
            for item in items:
                writer.writerow([item.get(key, 'N/A') for key in keys])  # Write each row
        logging.info(f"Results saved to {csv_filename}")
    else:
        logging.warning("No items found to save.")

if __name__ == "__main__":
    main()

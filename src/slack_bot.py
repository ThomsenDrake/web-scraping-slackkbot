import os
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv
import logging
import csv
from main import SmartScraperGraph, generate_csv_filename, graph_config
from slack_sdk.errors import SlackApiError
import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()

# Initialize Slack app
app = App(token=os.environ["SLACK_BOT_TOKEN"])

@app.command("/scrape")
def handle_scrape_command(ack, body, client):
    ack()
    
    try:
        client.views_open(
            trigger_id=body["trigger_id"],
            view={
                "type": "modal",
                "callback_id": "scrape_modal",
                "private_metadata": body["channel_id"],  # Store channel_id here
                "title": {"type": "plain_text", "text": "Web Scraping"},
                "submit": {"type": "plain_text", "text": "Scrape"},
                "blocks": [
                    {
                        "type": "input",
                        "block_id": "prompt_block",
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "prompt_input",
                            "placeholder": {"type": "plain_text", "text": "Enter your scraping prompt"}
                        },
                        "label": {"type": "plain_text", "text": "Prompt"}
                    },
                    {
                        "type": "input",
                        "block_id": "url_block",
                        "element": {
                            "type": "plain_text_input",
                            "action_id": "url_input",
                            "placeholder": {"type": "plain_text", "text": "Enter the URL to scrape"}
                        },
                        "label": {"type": "plain_text", "text": "URL"}
                    }
                ]
            }
        )
    except Exception as e:
        logging.error(f"Error opening modal: {e}")

@app.view("scrape_modal")
def handle_modal_submission(ack, body, view, client):
    ack()
    
    prompt = view["state"]["values"]["prompt_block"]["prompt_input"]["value"]
    url = view["state"]["values"]["url_block"]["url_input"]["value"]
    channel_id = view["private_metadata"]
    
    try:
        # Create and run scraper
        smart_scraper_graph = SmartScraperGraph(
            prompt=prompt,
            source=url,
            config=graph_config
        )
        
        result = smart_scraper_graph.run()
        csv_filename = generate_csv_filename(prompt, result)
        
        if not csv_filename.endswith('.csv'):
            csv_filename = f"{csv_filename}.csv"
        
        items = next((value for key, value in result.items() if isinstance(value, list)), [])
        
        if items:
            # Save CSV
            keys = items[0].keys()
            with open(csv_filename, 'w', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=keys)
                writer.writeheader()
                writer.writerows(items)
            
            try:
                # Upload file
                with open(csv_filename, 'rb') as file:
                    result = client.files_upload_v2(
                        channel=channel_id,
                        file=file,
                        filename=csv_filename,
                        title=f"Scraping results: {prompt}",
                        initial_comment=f"Found {len(items)} items from scraping"
                    )
                
            except SlackApiError as e:
                client.chat_postMessage(
                    channel=channel_id,
                    text=f"Error uploading file: {e.response['error']}"
                )
                logging.error(f"Slack API Error: {e.response['error']}")
            
            finally:
                # Clean up file regardless of upload success
                if os.path.exists(csv_filename):
                    try:
                        os.remove(csv_filename)
                        logging.info(f"Cleaned up temporary file: {csv_filename}")
                    except Exception as e:
                        logging.error(f"Error cleaning up file {csv_filename}: {e}")
        else:
            client.chat_postMessage(
                channel=channel_id,
                text="No items found in the scraping results."
            )
            
    except Exception as e:
        client.chat_postMessage(
            channel=channel_id,
            text=f"Error occurred during scraping: {str(e)}"
        )
        logging.error(f"Scraping error: {e}")

if __name__ == "__main__":
    # Start the app
    handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start()
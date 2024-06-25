import sys
import time
import json
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from kafka import KafkaProducer
from json import dumps
import pprint
import emlx
import html2text
import os



class KafkaLoggingEventHandler(FileSystemEventHandler):
    def __init__(self, producer, topic):
        self.producer = producer
        self.topic = topic
        self.html_to_text = html2text.HTML2Text()
        self.html_to_text.ignore_links = True

    def extract_plaintext_body(self, email_data):
        """Extract the plaintext body from the email data."""
        if email_data.is_multipart():
            for part in email_data.get_payload():
                if part.get_content_type() == "text/plain":
                    return part.get_payload(decode=True).decode(part.get_content_charset(), errors="replace")
                elif part.get_content_type() == "text/html":
                    html_content = part.get_payload(decode=True).decode(part.get_content_charset(), errors="replace")
                    return self.html_to_text.handle(html_content)
        else:
            if email_data.get_content_type() == "text/plain":
                return email_data.get_payload(decode=True).decode(email_data.get_content_charset(), errors="replace")
            elif email_data.get_content_type() == "text/html":
                html_content = email_data.get_payload(decode=True).decode(email_data.get_content_charset(), errors="replace")
                return self.html_to_text.handle(html_content)
        return None

    def on_modified(self, event):
        if not event.is_directory and (event.src_path.endswith('.emlx') or event.src_path.endswith('.eml')):
            email_data = emlx.read(event.src_path)
            headers = email_data.headers
            print(headers)
            # Extract plaintext body
            plaintext_body = self.extract_plaintext_body(email_data)

            # Create filtered data dictionary
            filtered_data = {
                'Delivered-To': headers.get('Delivered-To'),
                'From': headers.get('From'),
                'Date': headers.get('Date'),
                'Subject': headers.get('Subject'),
                'To': headers.get('To'),
                'Content-Type': headers.get('Content-Type'),
                'Body': plaintext_body,
                "Filename": event.src_path
            }
       

            # Ensure data is a JSON-serializable structure
            if isinstance(filtered_data, dict):
                serialized_data = json.dumps(filtered_data).encode('utf-8')
                if len(serialized_data) > 1024 * 1024:  # 1 MB limit
                    print(f"Payload size exceeds 1 MB and will be truncated: {len(serialized_data)} bytes")
                    serialized_data = serialized_data[:1024 * 1024]  # Truncate to 1 MB

                #print(filtered_data)
                self.producer.send(self.topic, value=serialized_data, key=headers.get('Message-ID').encode('utf-8'))
                self.producer.flush()  # Try to empty the sending buffer
            else:
                print(f"Data is not JSON serializable: {filtered_data}")

if __name__ == "__main__":
    #path = sys.argv[1] if len(sys.argv) > 1 else '/Users/danielwessendorf/Library/Mail/V10/AAFBC74F-473C-4C32-A82D-F772BB7CEC40'
    path = os.getenv("PATH_TO_MAILBOX", "/app/mail_data")
    kafka_broker = os.getenv('KAFKA_BROKER', 'localhost:56164')

    print(path)
    print(kafka_broker)

    producer = KafkaProducer(
        bootstrap_servers=[kafka_broker],  # replace with your kafka broker details
        value_serializer=lambda x: x  # We will serialize manually
    )
    event_handler = KafkaLoggingEventHandler(producer, 'mails')

    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()

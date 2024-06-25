import os
import json
import time
from kafka import KafkaConsumer, KafkaProducer
from langchain_community.llms import Ollama

# Set up Kafka consumer
kafka_broker = os.getenv('KAFKA_BROKER', 'kafka:9092')
consumer = KafkaConsumer(
    'mails',
    bootstrap_servers=[kafka_broker],
    auto_offset_reset='earliest',
    enable_auto_commit=True,
    group_id='mail-consumer-group2',
    value_deserializer=lambda x: json.loads(x.decode('utf-8'))
)

# Set up Kafka producer for the "mail-summaries" topic
producer = KafkaProducer(
    bootstrap_servers=[kafka_broker],
    value_serializer=lambda x: json.dumps(x).encode('utf-8')
)

# Set up LangChain with Ollama Llama3 model
llm = Ollama(model="llama3" , base_url='http://host.docker.internal:11434')

def summarize_and_check_action_items(text):
    # Summarize the email text
    summary_prompt = f"Summarize the following email text: {text}"
    summary_response = llm.generate(prompts=[summary_prompt])

    summary= summary_response.generations[0][0].text
    # Check for action items or to-dos
    action_item_prompt = f"Check if there are any action items or to-dos in the following email text: {text}"
    action_items_response = llm.generate(prompts=[action_item_prompt])
    action_items = action_items_response.generations[0][0].text
    return summary, action_items

def main():
    for message in consumer:
        email_data = message.value
        email_body = email_data.get('Body', '')
        if email_body:
            summary, action_items = summarize_and_check_action_items(email_body)
            result = {
                'summary': summary,
                'action_items': action_items,
                'original_email': email_data
            }
            print(result)
            producer.send('mail-summaries', value=result)
            producer.flush()  # Ensure the message is sent

            consumer.commit()
            
if __name__ == "__main__":
    while True:
        try:
            main()
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)

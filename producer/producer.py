from confluent_kafka import Producer
import json

def delivery_report(err, msg):
    if err is not None:
        print(f"Message delivery failed: {err}")
    else:
        print(f"Message delivered to {msg.topic()} [{msg.partition()}]")

p = Producer({'bootstrap.servers': 'my-kafka-cluster-bootstrap.confluent.svc:9092'})

for i in range(10):
    p.produce('mails', key=str(i), value=json.dumps({'mail_id': i, 'content': 'Hello World!'}), callback=delivery_report)
    p.poll(0)

p.flush()

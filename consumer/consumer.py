from confluent_kafka import Consumer

c = Consumer({
    'bootstrap.servers': 'my-kafka-cluster-bootstrap.confluent.svc:9092',
    'group.id': 'my-group',
    'auto.offset.reset': 'earliest'
})

c.subscribe(['mails'])

while True:
    msg = c.poll(1.0)
    if msg is None:
        continue
    if msg.error():
        print(f"Consumer error: {msg.error()}")
        continue

    print(f'Received message: {msg.value().decode("utf-8")}')

c.close()

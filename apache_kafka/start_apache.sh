#!/bin/bash
sudo docker-compose up -d

echo "Waiting for Kafka to be ready..."
until sudo docker exec kafka kafka-broker-api-versions --bootstrap-server localhost:9092 >/dev/null 2>&1; do
  echo "Kafka is unavailable - sleeping"
  sleep 2
done

echo "Kafka is up! Creating topics..."

#sudo docker exec kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic __consumer_offsets --from-beginning --timeout-ms 1000
sudo docker exec -it kafka kafka-topics --create --bootstrap-server localhost:9092 --topic card-detections --partitions 1 --replication-factor 1
sudo docker exec -it kafka kafka-topics --create --bootstrap-server localhost:9092 --topic simulation-requests --partitions 1 --replication-factor 1
sudo docker exec -it kafka kafka-topics --create --bootstrap-server localhost:9092 --topic simulation-results --partitions 1 --replication-factor 1
echo "Kafka is ready..."

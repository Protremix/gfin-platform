import re

with open('/gfin/docker-compose.yml', 'r') as f:
    content = f.read()

# Replace the entire kafka service block
old_kafka = '''  # ─── Kafka (KRaft mode — no Zookeeper) ───
  kafka:
    image: apache/kafka:3.7.1
    environment:
      KAFKA_CFG_NODE_ID: 1
      KAFKA_CFG_PROCESS_ROLES: controller,broker
      KAFKA_CFG_LISTENERS: PLAINTEXT://:9092,CONTROLLER://:9093
      KAFKA_CFG_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
      KAFKA_CFG_LISTENER_SECURITY_PROTOCOL_MAP: CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT
      KAFKA_CFG_CONTROLLER_QUORUM_VOTERS: 1@localhost:9093
      KAFKA_CFG_CONTROLLER_LISTENER_NAMES: CONTROLLER
      KAFKA_CFG_LOG_DIRS: /bitnami/kafka/data
      KAFKA_HEAP_OPTS: "-Xmx512m -Xms256m"
    ports:
      - "9092:9092"
    volumes:
      - kafkadata:/bitnami/kafka/data
    deploy:
      resources:
        limits:
          memory: 768M

  # ─── Kafka topic creation (one-shot) ───
  kafka-init:
    image: apache/kafka:3.7.1
    depends_on:
      - kafka
    entrypoint: ["/bin/bash", "-c"]
    command:
      - |
        sleep 15
        for topic in \
          gfin-events-entity gfin-events-report gfin-events-evidence \
          gfin-events-alert gfin-events-discovery gfin-events-audit \
          gfin-events-federation \
          gfin-dlq-entity gfin-dlq-report gfin-dlq-evidence \
          gfin-dlq-alert gfin-dlq-discovery gfin-dlq-audit \
          gfin-dlq-federation; do
          kafka-topics.sh --create --if-not-exists \
            --bootstrap-server kafka:9092 \
            --topic "$$topic" \
            --partitions 1 --replication-factor 1
          echo "Created topic: "$$topic"
        done
        echo "All 14 Kafka topics created."
    deploy:
      resources:
        limits:
          memory: 256M'''

new_kafka = '''  # ─── Kafka (KRaft mode — no Zookeeper) ───
  kafka:
    image: apache/kafka:3.7.1
    environment:
      KAFKA_NODE_ID: 1
      KAFKA_PROCESS_ROLES: broker,controller
      KAFKA_LISTENERS: PLAINTEXT://:9092,CONTROLLER://:9093
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT
      KAFKA_CONTROLLER_QUORUM_VOTERS: 1@localhost:9093
      KAFKA_CONTROLLER_LISTENER_NAMES: CONTROLLER
      KAFKA_LOG_DIRS: /tmp/kafka-logs
      KAFKA_HEAP_OPTS: "-Xmx512m -Xms256m"
    ports:
      - "9092:9092"
    deploy:
      resources:
        limits:
          memory: 768M

  # ─── Kafka topic creation (one-shot) ───
  kafka-init:
    image: apache/kafka:3.7.1
    depends_on:
      - kafka
    entrypoint: ["/bin/bash", "-c"]
    command:
      - |
        sleep 20
        for topic in \
          gfin-events-entity gfin-events-report gfin-events-evidence \
          gfin-events-alert gfin-events-discovery gfin-events-audit \
          gfin-events-federation \
          gfin-dlq-entity gfin-dlq-report gfin-dlq-evidence \
          gfin-dlq-alert gfin-dlq-discovery gfin-dlq-audit \
          gfin-dlq-federation; do
          /opt/kafka/bin/kafka-topics.sh --create --if-not-exists \
            --bootstrap-server kafka:9092 \
            --topic "$$topic" \
            --partitions 1 --replication-factor 1
          echo "Created topic: "$$topic"
        done
        echo "All 14 Kafka topics created."
    deploy:
      resources:
        limits:
          memory: 256M'''

content = content.replace(old_kafka, new_kafka)

# Also fix the volumes section - remove kafkadata volume
content = content.replace('  kafkadata:', '  # kafkadata: (removed - using /tmp)')

with open('/gfin/docker-compose.yml', 'w') as f:
    f.write(content)

print('Fixed Kafka config')

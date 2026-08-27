"""Tests for Kafka Layer B — Event Bus Production Definition.

These tests verify the Kafka-backed event bus definition:
- Topic registry completeness
- Consumer group configuration
- Producer idempotency config
- DLQ topic mapping
- ACL coverage
- Security configuration
- Observability hooks
- Strimzi manifest validity
- All raise KafkaConnectionError without infrastructure (Layer B contract)

Status: REQUIRES EXTERNAL INFRASTRUCTURE — tests verify definitions, not live Kafka.
"""

from __future__ import annotations

import sys

sys.path.insert(0, ".")
sys.path.insert(0, "packages")

import pytest

from services.kafka_event_bus import (
    ACL_REGISTRY,
    CONSUMER_REGISTRY,
    KAFKA_NETWORK_POLICY,
    STRIMZI_MANIFEST,
    TOPIC_REGISTRY,
    DeliverySemantic,
    KafkaConnectionError,
    KafkaConsumerConfig,
    KafkaEventBus,
    KafkaMetrics,
    KafkaProducerConfig,
    KafkaSecurityConfig,
    KafkaTopic,
    KafkaTopicAdmin,
)


class TestTopicRegistry:
    """Verify all required Kafka topics are defined per spec."""

    def test_all_main_topics_defined(self):
        """All 7 main topics from spec are present."""
        expected = [
            KafkaTopic.ENTITY_EVENTS,
            KafkaTopic.REPORT_EVENTS,
            KafkaTopic.EVIDENCE_EVENTS,
            KafkaTopic.ALERT_EVENTS,
            KafkaTopic.DISCOVERY_EVENTS,
            KafkaTopic.AUDIT_EVENTS,
            KafkaTopic.FEDERATION_EVENTS,
        ]
        for topic in expected:
            assert topic.value in TOPIC_REGISTRY, f"Missing topic: {topic.value}"

    def test_all_dlq_topics_defined(self):
        """Each main topic has a corresponding DLQ topic."""
        for main_topic in [
            KafkaTopic.ENTITY_EVENTS,
            KafkaTopic.REPORT_EVENTS,
            KafkaTopic.EVIDENCE_EVENTS,
            KafkaTopic.ALERT_EVENTS,
            KafkaTopic.DISCOVERY_EVENTS,
            KafkaTopic.AUDIT_EVENTS,
            KafkaTopic.FEDERATION_EVENTS,
        ]:
            dlq_name = main_topic.value.replace("events", "dlq")
            assert dlq_name in TOPIC_REGISTRY, f"Missing DLQ: {dlq_name}"

    def test_topic_partitions_match_spec(self):
        """Partitions match Master Engineering Specification."""
        assert TOPIC_REGISTRY[KafkaTopic.ENTITY_EVENTS.value].partitions == 12
        assert TOPIC_REGISTRY[KafkaTopic.REPORT_EVENTS.value].partitions == 6
        assert TOPIC_REGISTRY[KafkaTopic.DISCOVERY_EVENTS.value].partitions == 12
        assert TOPIC_REGISTRY[KafkaTopic.AUDIT_EVENTS.value].partitions == 6
        assert TOPIC_REGISTRY[KafkaTopic.FEDERATION_EVENTS.value].partitions == 3

    def test_topic_retention_matches_spec(self):
        """Retention periods match spec."""
        assert TOPIC_REGISTRY[KafkaTopic.ENTITY_EVENTS.value].retention_hours == 168  # 7 days
        assert TOPIC_REGISTRY[KafkaTopic.REPORT_EVENTS.value].retention_hours == 720  # 30 days
        assert TOPIC_REGISTRY[KafkaTopic.EVIDENCE_EVENTS.value].retention_hours == 2160  # 90 days
        assert TOPIC_REGISTRY[KafkaTopic.AUDIT_EVENTS.value].retention_hours == 8760  # 365 days

    def test_topic_replication_factor(self):
        """All topics have replication factor 3 for quorum."""
        for topic_cfg in TOPIC_REGISTRY.values():
            assert topic_cfg.replication_factor == 3

    def test_topic_min_in_sync_replicas(self):
        """Min in-sync replicas is 2 for data safety."""
        for topic_cfg in TOPIC_REGISTRY.values():
            assert topic_cfg.min_in_sync_replicas == 2

    def test_topic_config_serialization(self):
        """Topic config serializes to dict correctly."""
        cfg = TOPIC_REGISTRY[KafkaTopic.ENTITY_EVENTS.value]
        d = cfg.to_dict()
        assert d["name"] == KafkaTopic.ENTITY_EVENTS.value
        assert d["partitions"] == 12
        assert "retention.ms" in d["configs"]
        assert "min.insync.replicas" in d["configs"]
        assert "compression.type" in d["configs"]


class TestConsumerRegistry:
    """Verify all consumer groups are configured per spec."""

    def test_all_consumer_groups_defined(self):
        """All 5 consumer groups from spec are present."""
        expected = [
            "gfin-entity-resolver",
            "gfin-alert-engine",
            "gfin-discovery-worker",
            "gfin-audit-writer",
            "gfin-federation-sync",
        ]
        for group in expected:
            assert group in CONSUMER_REGISTRY, f"Missing consumer group: {group}"

    def test_consumer_max_poll_records(self):
        """Max poll records match spec."""
        assert CONSUMER_REGISTRY["gfin-entity-resolver"].max_poll_records == 100
        assert CONSUMER_REGISTRY["gfin-alert-engine"].max_poll_records == 50
        assert CONSUMER_REGISTRY["gfin-discovery-worker"].max_poll_records == 200
        assert CONSUMER_REGISTRY["gfin-audit-writer"].max_poll_records == 500
        assert CONSUMER_REGISTRY["gfin-federation-sync"].max_poll_records == 10

    def test_all_consumers_have_dlq(self):
        """Every consumer group has a DLQ topic configured."""
        for group_id, config in CONSUMER_REGISTRY.items():
            assert config.dlq_topic is not None, f"Consumer {group_id} missing DLQ"

    def test_auto_commit_disabled(self):
        """Auto-commit is disabled for exactly-once semantics."""
        for config in CONSUMER_REGISTRY.values():
            assert config.enable_auto_commit is False

    def test_retry_configured(self):
        """Retry attempts configured per consumer."""
        for config in CONSUMER_REGISTRY.values():
            assert config.max_retry_attempts == 3
            assert config.retry_backoff_ms == 1000

    def test_consumer_config_serialization(self):
        """Consumer config serializes to dict."""
        cfg = CONSUMER_REGISTRY["gfin-entity-resolver"]
        d = cfg.to_dict()
        assert d["group_id"] == "gfin-entity-resolver"
        assert isinstance(d["topics"], list)
        assert KafkaTopic.ENTITY_EVENTS.value in d["topics"]


class TestProducerConfig:
    """Verify producer configuration for idempotency."""

    def test_idempotence_enabled(self):
        """Producer idempotence is enabled for exactly-once."""
        config = KafkaProducerConfig()
        assert config.enable_idempotence is True

    def test_acks_all(self):
        """Producer acks=all for durability."""
        config = KafkaProducerConfig()
        assert config.acks == "all"

    def test_retries_configured(self):
        """Producer has retries configured."""
        config = KafkaProducerConfig()
        assert config.retries == 3

    def test_compression_enabled(self):
        """Producer uses LZ4 compression."""
        config = KafkaProducerConfig()
        assert config.compression_type == "lz4"

    def test_max_in_flight_limited(self):
        """Max in-flight requests limited for ordering with idempotence."""
        config = KafkaProducerConfig()
        assert config.max_in_flight_requests_per_connection <= 5

    def test_config_serialization(self):
        """Producer config serializes to dict."""
        config = KafkaProducerConfig()
        d = config.to_dict()
        assert d["enable.idempotence"] is True
        assert d["acks"] == "all"
        assert "retries" in d


class TestDLQMapping:
    """Verify dead letter queue mapping is correct."""

    def test_entity_resolver_dlq(self):
        """Entity resolver DLQ points to correct topic."""
        assert (
            CONSUMER_REGISTRY["gfin-entity-resolver"].dlq_topic
            == KafkaTopic.DLQ_ENTITY.value
        )

    def test_alert_engine_dlq(self):
        """Alert engine DLQ points to correct topic."""
        assert (
            CONSUMER_REGISTRY["gfin-alert-engine"].dlq_topic
            == KafkaTopic.DLQ_ALERT.value
        )

    def test_discovery_worker_dlq(self):
        """Discovery worker DLQ points to correct topic."""
        assert (
            CONSUMER_REGISTRY["gfin-discovery-worker"].dlq_topic
            == KafkaTopic.DLQ_DISCOVERY.value
        )

    def test_all_dlq_topics_in_registry(self):
        """All DLQ topics referenced by consumers exist in registry."""
        for config in CONSUMER_REGISTRY.values():
            assert config.dlq_topic in TOPIC_REGISTRY, (
                f"DLQ topic {config.dlq_topic} not in registry"
            )


class TestACLRegistry:
    """Verify Kafka ACL coverage for all services."""

    def test_entity_resolver_has_read_access(self):
        """Entity resolver has READ on entity events."""
        acls = [a for a in ACL_REGISTRY if a.principal == "User:gfin-entity-resolver"]
        read_acls = [a for a in acls if a.operation == "READ"]
        assert any(KafkaTopic.ENTITY_EVENTS.value in a.topic for a in read_acls)

    def test_entity_resolver_has_dlq_write(self):
        """Entity resolver can write to its DLQ."""
        acls = [a for a in ACL_REGISTRY if a.principal == "User:gfin-entity-resolver"]
        write_acls = [a for a in acls if a.operation == "WRITE"]
        assert any(KafkaTopic.DLQ_ENTITY.value in a.topic for a in write_acls)

    def test_app_can_publish_all_main_topics(self):
        """App service can write to all main event topics."""
        app_acls = [a for a in ACL_REGISTRY if a.principal == "User:gfin-app"]
        write_topics = {a.topic for a in app_acls if a.operation == "WRITE"}
        for topic in [
            KafkaTopic.ENTITY_EVENTS.value,
            KafkaTopic.REPORT_EVENTS.value,
            KafkaTopic.EVIDENCE_EVENTS.value,
            KafkaTopic.ALERT_EVENTS.value,
            KafkaTopic.DISCOVERY_EVENTS.value,
            KafkaTopic.AUDIT_EVENTS.value,
            KafkaTopic.FEDERATION_EVENTS.value,
        ]:
            assert topic in write_topics, f"App missing WRITE on {topic}"

    def test_monitoring_can_describe(self):
        """Monitoring service can DESCRIBE all topics."""
        mon_acls = [a for a in ACL_REGISTRY if a.principal == "User:gfin-monitoring"]
        assert any(a.operation == "DESCRIBE" and a.topic == "*" for a in mon_acls)

    def test_no_wildcard_write(self):
        """No service has wildcard WRITE (principle of least privilege)."""
        for acl in ACL_REGISTRY:
            if acl.operation == "WRITE":
                assert acl.topic != "*", f"Wildcard WRITE on {acl.principal}"

    def test_acl_serialization(self):
        """ACL serializes to dict."""
        acl = ACL_REGISTRY[0]
        d = acl.to_dict()
        assert "principal" in d
        assert "operation" in d
        assert "topic" in d


class TestSecurityConfig:
    """Verify Kafka security configuration."""

    def test_tls_enabled_by_default(self):
        """TLS is enabled by default."""
        config = KafkaSecurityConfig()
        assert config.tls_enabled is True

    def test_tls_1_3(self):
        """TLS 1.3 is required."""
        config = KafkaSecurityConfig()
        assert config.tls_version == "1.3"

    def test_client_auth_required(self):
        """Mutual TLS client auth is required."""
        config = KafkaSecurityConfig()
        assert config.client_auth == "required"

    def test_sasl_scram_sha_512(self):
        """SASL mechanism is SCRAM-SHA-512."""
        config = KafkaSecurityConfig()
        assert config.sasl_mechanism == "SCRAM-SHA-512"

    def test_encryption_at_rest(self):
        """Encryption at rest is AES-256."""
        config = KafkaSecurityConfig()
        assert config.encryption_at_rest == "AES-256"

    def test_acl_enabled(self):
        """ACLs are enabled."""
        config = KafkaSecurityConfig()
        assert config.acl_enabled is True

    def test_security_config_serialization(self):
        """Security config serializes to dict."""
        config = KafkaSecurityConfig()
        d = config.to_dict()
        assert d["tls"]["enabled"] is True
        assert d["sasl"]["mechanism"] == "SCRAM-SHA-512"


class TestKafkaEventBus:
    """Verify KafkaEventBus behavior without infrastructure."""

    def test_health_check_returns_not_connected(self):
        """Health check reports not connected without infrastructure."""
        bus = KafkaEventBus()
        import asyncio
        health = asyncio.run(bus.health_check())
        assert health["connected"] is False
        assert "REQUIRES EXTERNAL INFRASTRUCTURE" in health["status"]

    def test_publish_raises_without_connection(self):
        """Publish raises KafkaConnectionError without infrastructure."""
        bus = KafkaEventBus()
        import asyncio
        with pytest.raises(KafkaConnectionError):
            asyncio.run(bus.publish("topic", "key", b"value"))

    def test_subscribe_raises_without_connection(self):
        """Subscribe raises KafkaConnectionError without infrastructure."""
        bus = KafkaEventBus()
        import asyncio
        with pytest.raises(KafkaConnectionError):
            asyncio.run(bus.subscribe(KafkaConsumerConfig("test", ["topic"]), None))

    def test_replay_raises_without_connection(self):
        """Replay raises KafkaConnectionError without infrastructure."""
        bus = KafkaEventBus()
        import asyncio
        with pytest.raises(KafkaConnectionError):
            asyncio.run(bus.replay(KafkaConsumerConfig("test", ["topic"]), None))

    def test_get_consumer_lag_raises_without_connection(self):
        """Get consumer lag raises KafkaConnectionError without infrastructure."""
        bus = KafkaEventBus()
        import asyncio
        with pytest.raises(KafkaConnectionError):
            asyncio.run(bus.get_consumer_lag("group"))

    def test_connect_raises_without_infrastructure(self):
        """Connect raises KafkaConnectionError without infrastructure."""
        bus = KafkaEventBus()
        with pytest.raises(KafkaConnectionError):
            bus.connect()

    def test_metrics_initialized(self):
        """Metrics are initialized to zero."""
        bus = KafkaEventBus()
        metrics = bus.get_metrics()
        assert metrics["total_published"] == 0
        assert metrics["total_consumed"] == 0
        assert metrics["total_errors"] == 0
        assert metrics["total_dlq"] == 0
        assert metrics["total_retries"] == 0


class TestKafkaTopicAdmin:
    """Verify topic admin behavior."""

    def test_get_topic_configs_static(self):
        """Get topic configs works without Kafka (static registry)."""
        admin = KafkaTopicAdmin()
        configs = admin.get_topic_configs()
        assert len(configs) == 14  # 7 main + 7 DLQ
        assert KafkaTopic.ENTITY_EVENTS.value in configs

    def test_get_consumer_configs_static(self):
        """Get consumer configs works without Kafka (static registry)."""
        admin = KafkaTopicAdmin()
        configs = admin.get_consumer_configs()
        assert "gfin-entity-resolver" in configs
        assert "gfin-alert-engine" in configs

    def test_create_all_topics_raises(self):
        """Create all topics raises without infrastructure."""
        admin = KafkaTopicAdmin()
        with pytest.raises(KafkaConnectionError):
            admin.create_all_topics()

    def test_validate_topics_raises(self):
        """Validate topics raises without infrastructure."""
        admin = KafkaTopicAdmin()
        with pytest.raises(KafkaConnectionError):
            admin.validate_topics()


class TestKafkaMetrics:
    """Verify observability metrics."""

    def test_metrics_initialized(self):
        """All metrics initialized to zero."""
        metrics = KafkaMetrics()
        assert metrics.producer_metrics["record_send_rate"] == 0.0
        assert metrics.consumer_metrics["records_consumed_rate"] == 0.0
        assert metrics.topic_metrics["messages_in_rate"] == 0.0

    def test_prometheus_export(self):
        """Metrics export to Prometheus text format."""
        metrics = KafkaMetrics()
        lines = metrics.to_prometheus()
        assert any("gfin_kafka_producer_" in line for line in lines)
        assert any("gfin_kafka_consumer_" in line for line in lines)
        assert any("gfin_kafka_topic_" in line for line in lines)

    def test_producer_metrics_fields(self):
        """Producer metrics include required fields."""
        metrics = KafkaMetrics()
        assert "record_send_rate" in metrics.producer_metrics
        assert "record_error_rate" in metrics.producer_metrics
        assert "request_latency_avg_ms" in metrics.producer_metrics

    def test_consumer_metrics_fields(self):
        """Consumer metrics include required fields."""
        metrics = KafkaMetrics()
        assert "records_consumed_rate" in metrics.consumer_metrics
        assert "records_lag_max" in metrics.consumer_metrics
        assert "rebalance_rate" in metrics.consumer_metrics

    def test_topic_metrics_fields(self):
        """Topic metrics include required fields."""
        metrics = KafkaMetrics()
        assert "messages_in_rate" in metrics.topic_metrics
        assert "under_replicated_partitions" in metrics.topic_metrics


class TestStrimziManifest:
    """Verify Strimzi Kafka cluster manifest."""

    def test_manifest_exists(self):
        """Strimzi manifest is defined."""
        assert STRIMZI_MANIFEST is not None
        assert len(STRIMZI_MANIFEST) > 0

    def test_manifest_has_kafka_kind(self):
        """Manifest has Kafka kind."""
        assert "kind: Kafka" in STRIMZI_MANIFEST

    def test_manifest_has_3_brokers(self):
        """Manifest specifies 3 Kafka brokers for quorum."""
        assert "replicas: 3" in STRIMZI_MANIFEST

    def test_manifest_has_tls_listener(self):
        """Manifest has TLS listener on 9093."""
        assert "port: 9093" in STRIMZI_MANIFEST
        assert "tls: true" in STRIMZI_MANIFEST

    def test_manifest_has_scram_auth(self):
        """Manifest uses SCRAM-SHA-512 authentication."""
        assert "scram-sha-512" in STRIMZI_MANIFEST

    def test_manifest_has_mtls_listener(self):
        """Manifest has mTLS listener on 9094."""
        assert "port: 9094" in STRIMZI_MANIFEST
        assert "type: tls" in STRIMZI_MANIFEST

    def test_manifest_has_retention_config(self):
        """Manifest has log retention configured."""
        assert "log.retention.hours: 168" in STRIMZI_MANIFEST

    def test_manifest_has_min_insync(self):
        """Manifest has min.insync.replicas configured."""
        assert "min.insync.replicas: 2" in STRIMZI_MANIFEST

    def test_manifest_disables_auto_create_topics(self):
        """Manifest disables auto topic creation."""
        assert "auto.create.topics.enable: false" in STRIMZI_MANIFEST

    def test_manifest_has_persistent_storage(self):
        """Manifest uses persistent claims for storage."""
        assert "persistent-claim" in STRIMZI_MANIFEST


class TestNetworkPolicy:
    """Verify Kafka network policy."""

    def test_policy_exists(self):
        """Network policy is defined."""
        assert KAFKA_NETWORK_POLICY is not None

    def test_policy_has_ingress_rules(self):
        """Network policy has ingress restrictions."""
        assert "ingress" in KAFKA_NETWORK_POLICY
        assert "layer: application" in KAFKA_NETWORK_POLICY

    def test_policy_has_egress_rules(self):
        """Network policy has egress restrictions."""
        assert "egress" in KAFKA_NETWORK_POLICY

    def test_policy_restricts_ports(self):
        """Network policy restricts to Kafka ports only."""
        assert "port: 9093" in KAFKA_NETWORK_POLICY
        assert "port: 9094" in KAFKA_NETWORK_POLICY


class TestDeliverySemantics:
    """Verify delivery semantic definitions."""

    def test_at_most_once(self):
        """AT_MOST_ONCE semantic is defined."""
        assert DeliverySemantic.AT_MOST_ONCE.value == "at_most_once"

    def test_at_least_once(self):
        """AT_LEAST_ONCE semantic is defined."""
        assert DeliverySemantic.AT_LEAST_ONCE.value == "at_least_once"

    def test_exactly_once(self):
        """EXACTLY_ONCE semantic is defined."""
        assert DeliverySemantic.EXACTLY_ONCE.value == "exactly_once"

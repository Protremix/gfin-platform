#!/usr/bin/env python3
"""
GFIN 24/7 Continuous Monitoring Loop
Runs as a background process, scanning for:
- New domain registrations matching scam keywords
- Certificate transparency logs for scam domains
- Known scam infrastructure changes (re-scans)
- Proactive pattern detection

Triggers the Intelligence Playbook automatically when scam patterns are detected.
"""
import json, time, ssl, urllib.request, sys, logging

sys.path.insert(0, '/gfin/packages/services')

try:
    from telegram_alerts import broadcast_scam_alert, process_bot_updates
    _telegram = True
except Exception as e:
    _telegram = False
    print(f"Warning: telegram not loaded: {e}")

try:
    from scam_awareness import send_awareness_broadcast, get_awareness_stats
    _awareness = True
except Exception as e:
    _awareness = False
    print(f"Warning: scam awareness not loaded: {e}")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [monitor] %(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/gfin/logs/monitor.log'),
    ]
)
logger = logging.getLogger(__name__)

# Known scam keywords to monitor in new domain registrations
SCAM_KEYWORDS = [
    "recovery", "payback", "refund", "retrieve", "reclaim",
    "crypto-recovery", "bitcoin-recovery", "wallet-recovery",
    "lost-funds", "hack-back", "blockchain-recovery",
    "asset-recovery", "recovery-expert", "recovery-service",
    "scam-recovery", "fund-recovery", "chargeback",
]

# Domains to monitor for changes (known scam infrastructure)
MONITOR_LIST = [
    "cncintelinfo.com",
]

# How often to run each scan (in seconds)
SCAN_INTERVALS = {
    "domain_scan": 3600,        # 1 hour
    "ct_logs": 7200,             # 2 hours
    "rescan_known": 86400,       # 24 hours
}


class ContinuousMonitor:
    """24/7 monitoring engine."""

    def __init__(self):
        self.ssl_ctx = ssl.create_default_context()
        self.ssl_ctx.check_hostname = False
        self.ssl_ctx.verify_mode = ssl.CERT_NONE
        self.alerts = []
        self.last_scan = {}
        self.playbook = None
        try:
            from intelligence_playbook_v52 import IntelligencePlaybook
            self.playbook = IntelligencePlaybook()
            logger.info("Intelligence Playbook loaded for auto-investigation")
        except Exception as e:
            logger.warning(f"Playbook not loaded: {e}")

    def _http_get_json(self, url, timeout=15):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "GFIN-Monitor/1.0"})
            resp = urllib.request.urlopen(req, timeout=timeout, context=self.ssl_ctx)
            return json.loads(resp.read().decode('utf-8', errors='replace'))
        except:
            return None

    def _http_get_text(self, url, timeout=15):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "GFIN-Monitor/1.0"})
            resp = urllib.request.urlopen(req, timeout=timeout, context=self.ssl_ctx)
            return resp.read().decode('utf-8', errors='replace')
        except:
            return None

    def scan_certificate_transparency(self):
        """Scan Certificate Transparency logs for new scam domains."""
        logger.info("Scanning Certificate Transparency logs for scam domains...")
        results = []

        for keyword in SCAM_KEYWORDS[:5]:  # Top 5 keywords to keep it fast
            try:
                data = self._http_get_json(f"https://crt.sh/?q=%{keyword}%&output=json&limit=20", timeout=15)
                if data and isinstance(data, list):
                    for cert in data[:10]:
                        name = cert.get("name_value", "").strip()
                        if name and keyword in name.lower():
                            # Check if this domain is suspicious
                            is_suspicious = any(kw in name.lower() for kw in SCAM_KEYWORDS)
                            if is_suspicious:
                                result = {
                                    "type": "CT_SCAM_DOMAIN",
                                    "domain": name.split("\n")[0],
                                    "keyword": keyword,
                                    "cert_id": cert.get("id", ""),
                                    "not_before": cert.get("not_before", ""),
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                }
                                results.append(result)
                                logger.info(f"  Found suspicious domain in CT logs: {name} (keyword: {keyword})")
            except:
                pass

            time.sleep(1)  # Rate limit

        if results:
            self.alerts.extend(results)
            # Trigger auto-investigation
            for r in results[:3]:
                self._auto_investigate(r["domain"].split("\n")[0], "CERTIFICATE_TRANSPARENCY",
                                     f"Domain '{r['domain']}' found in CT logs matching scam keyword '{r['keyword']}'")

        return results

    def scan_new_domains(self):
        """Check for recently registered domains matching scam patterns."""
        logger.info("Scanning for new scam domain registrations...")
        results = []

        # Use CT logs as a proxy for new domain registrations
        try:
            data = self._http_get_json("https://crt.sh/?q=%recovery%&output=json&limit=50", timeout=15)
            if data and isinstance(data, list):
                for cert in data[:20]:
                    name = cert.get("name_value", "").strip()
                    not_before = cert.get("not_before", "")
                    if name and "recovery" in name.lower():
                        domain = name.split("\n")[0]
                        # Skip wildcards and common domains
                        if not domain.startswith("*."):
                            result = {
                                "type": "NEW_SCAM_DOMAIN",
                                "domain": domain,
                                "registered": not_before,
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            }
                            results.append(result)
                            logger.info(f"  New potential scam domain: {domain} (cert date: {not_before})")
        except:
            pass

        if results:
            self.alerts.extend(results)
            for r in results[:3]:
                self._auto_investigate(r["domain"], "NEW_DOMAIN_REGISTRATION",
                                     f"New domain '{r['domain']}' registered matching scam keyword 'recovery'")

        return results

    def rescan_known_infrastructure(self):
        """Re-scan known scam infrastructure for changes."""
        logger.info(f"Re-scanning {len(MONITOR_LIST)} known scam domains for changes...")
        results = []

        for domain in MONITOR_LIST:
            try:
                # Check if domain still resolves
                import socket
                try:
                    ips = socket.getaddrinfo(domain, None, socket.AF_INET)
                    ip_list = list(set(ip[4][0] for ip in ips))
                    result = {
                        "type": "RESCAN",
                        "domain": domain,
                        "status": "ACTIVE",
                        "ips": ip_list,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    logger.info(f"  {domain}: ACTIVE, resolves to {ip_list}")
                except socket.gaierror:
                    result = {
                        "type": "RESCAN",
                        "domain": domain,
                        "status": "INACTIVE",
                        "ips": [],
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    logger.info(f"  {domain}: INACTIVE (no DNS)")

                results.append(result)
            except Exception as e:
                logger.warning(f"  Error scanning {domain}: {e}")

            time.sleep(2)  # Rate limit

        if results:
            self.alerts.extend(results)
            # Re-investigate active domains
            for r in results:
                if r["status"] == "ACTIVE":
                    self._auto_investigate(r["domain"], "CONTINUOUS_MONITORING",
                                         f"Re-scan of known domain {r['domain']} — domain still active")

        return results

    def _auto_investigate(self, identifier, trigger, reason):
        """Automatically trigger a playbook investigation."""
        if not self.playbook:
            logger.warning(f"  Cannot auto-investigate {identifier} — playbook not loaded")
            return

        logger.info(f"  Auto-investigating: {identifier} (trigger: {trigger})")
        try:
            result = self.playbook.investigate({
                "trigger": trigger,
                "trigger_reason": reason,
                "identifier": identifier,
                "identifier_type": "DOMAIN",
                "operator": "GFIN-MONITOR",
                "authority": "Automated monitoring — no legal action",
            })

            # Log the result
            ev_count = len(result["evidence_chain"])
            loc_count = len(result["physical_locations"])
            scam_count = len(result["scam_indicators"])
            accusation = result["accusation_level"]

            logger.info(f"  Investigation {result['investigation_id']} complete: "
                       f"{ev_count} evidence steps, {loc_count} locations, "
                       f"{scam_count} scam indicators, accusation: {accusation}")

            # Save to alerts file
            alert = {
                "investigation_id": result["investigation_id"],
                "identifier": identifier,
                "trigger": trigger,
                "reason": reason,
                "evidence_steps": ev_count,
                "physical_locations": loc_count,
                "scam_indicators": scam_count,
                "accusation_level": accusation,
                "confidence": result["confidence"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            self._save_alert(alert)

        except Exception as e:
            logger.error(f"  Auto-investigation failed for {identifier}: {e}")

    def _save_alert(self, alert):
        """Save alert to the alerts file."""
        try:
            alerts_file = "/gfin/logs/monitor_alerts.json"
            existing = []
            if os.path.exists(alerts_file):
                with open(alerts_file, "r") as f:
                    try:
                        existing = json.load(f)
                    except:
                        existing = []
            existing.append(alert)
            with open(alerts_file, "w") as f:
                json.dump(existing[-100:], f, indent=2)  # Keep last 100
        except Exception as e:
            logger.error(f"  Error saving alert: {e}")

    def run_cycle(self):
        """Run one full monitoring cycle."""
        cycle_start = time.time()
        logger.info("=" * 50)
        logger.info("Starting monitoring cycle")
        logger.info("=" * 50)

        all_results = []

        # Run all scans
        try:
            ct_results = self.scan_certificate_transparency()
            all_results.extend(ct_results)
        except Exception as e:
            logger.error(f"CT scan error: {e}")

        try:
            domain_results = self.scan_new_domains()
            all_results.extend(domain_results)
        except Exception as e:
            logger.error(f"Domain scan error: {e}")

        try:
            rescan_results = self.rescan_known_infrastructure()
            all_results.extend(rescan_results)
        except Exception as e:
            logger.error(f"Rescan error: {e}")

        cycle_time = time.time() - cycle_start
        logger.info("=" * 50)
        logger.info(f"Monitoring cycle complete: {len(all_results)} results, {cycle_time:.1f}s")
        logger.info("=" * 50)

        return all_results

    def run_forever(self, interval=3600):
        """Run continuous monitoring loop."""
        logger.info("GFIN 24/7 Continuous Monitor started")
        logger.info(f"Scan interval: {interval} seconds")
        logger.info(f"Monitoring {len(SCAM_KEYWORDS)} scam keywords")
        logger.info(f"Tracking {len(MONITOR_LIST)} known scam domains")

        while True:
            try:
                self.run_cycle()
                logger.info(f"Sleeping for {interval} seconds...")
                time.sleep(interval)
            except KeyboardInterrupt:
                logger.info("Monitor stopped by user")
                break
            except Exception as e:
                logger.error(f"Monitor error: {e}")
                time.sleep(60)  # Wait 1 minute before retry


if __name__ == "__main__":
    monitor = ContinuousMonitor()
    # Run one cycle for testing, then start continuous loop
    if len(sys.argv) > 1 and sys.argv[1] == "--once":
        monitor.run_cycle()
    else:
        monitor.run_forever(interval=3600)  # Run every hour

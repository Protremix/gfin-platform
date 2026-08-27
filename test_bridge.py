#!/usr/bin/env python3
"""Test bridge import"""
import sys
sys.path.insert(0, "/gfin")
sys.path.insert(0, "/gfin/packages/services")

try:
    from midas_alert_bridge import midas_alert_bridge
    print("Bridge imported OK")
    coro = midas_alert_bridge()
    print("Coroutine created OK")
    coro.close()
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

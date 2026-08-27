#!/usr/bin/env python3
"""Fix analytics map dark filter by switching to CartoDB Dark tiles."""
content = open("/gfin/analytics_dashboard.html").read()

# 1. Replace the old invert filter CSS with CartoDB-compatible styling
old_filter = """/* Dark map tiles filter (free, no API key needed) */
        .leaflet-tile-pane {
            filter: invert(1) hue-rotate(180deg) brightness(0.85) contrast(0.9);
        }
        .leaflet-control-attribution {
            filter: invert(1) hue-rotate(180deg);
            background: rgba(0,0,0,0.7) !important;
            color: #94a3b8 !important;
        }
        .leaflet-control-attribution a {
            color: #64748b !important;
        }"""

new_filter = """/* Dark map tiles using CartoDB Dark Matter (free, no API key) */
        .leaflet-tile-pane {
            filter: brightness(0.95) contrast(1.05);
        }
        .leaflet-control-attribution {
            background: rgba(0,0,0,0.7) !important;
            color: #94a3b8 !important;
        }
        .leaflet-control-attribution a {
            color: #64748b !important;
        }
        .leaflet-control-zoom a {
            background: #1b1c2e !important;
            color: #e0d8c0 !important;
            border-color: #334155 !important;
        }
        .leaflet-control-zoom a:hover {
            background: #2a2b3d !important;
        }"""

content = content.replace(old_filter, new_filter)

# 2. Replace OSM tile URL with CartoDB Dark Matter
old_url = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
new_url = "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png"
content = content.replace(old_url, new_url)

# 3. Fix attribution text
content = content.replace(
    "OpenStreetMap contributors (dark filter)",
    "OpenStreetMap contributors, CARTO"
)

open("/gfin/analytics_dashboard.html", "w").write(content)
print("Map switched to CartoDB Dark tiles (no more black blocks)")

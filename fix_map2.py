#!/usr/bin/env python3
"""Fix analytics map: switch to ESRI dark tiles (free, no API key)."""
content = open("/gfin/analytics_dashboard.html").read()

# Replace CartoDB URL with ESRI Dark Gray (free, no API key)
content = content.replace(
    "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png",
    "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}"
)

# Also fix the attribution
content = content.replace(
    "OpenStreetMap contributors, CARTO",
    "Esri, HERE, OpenStreetMap contributors"
)

# Add maxZoom for ESRI tiles (they support up to 16)
content = content.replace(
    "attribution: 'Esri, HERE, OpenStreetMap contributors'",
    "attribution: 'Esri, HERE, OpenStreetMap contributors', maxZoom: 16"
)

# Remove the brightness/contrast filter since ESRI tiles are already dark
content = content.replace(
    "filter: brightness(0.95) contrast(1.05);",
    "filter: none;"
)

open("/gfin/analytics_dashboard.html", "w").write(content)
print("Switched to ESRI Dark Gray tiles (free, no API key needed)")

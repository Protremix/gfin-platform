#!/usr/bin/env python3
"""Add Favorite Cases feature to GFIN — backend API + frontend UI"""

import psycopg2
import json

# 1. Create the favorite_cases table
conn = psycopg2.connect(host="localhost", dbname="gfin", user="gfin", password="")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS favorite_cases (
    id SERIAL PRIMARY KEY,
    case_id VARCHAR(50) NOT NULL,
    officer_email TEXT NOT NULL,
    officer_id INTEGER,
    notes TEXT,
    created_date TIMESTAMP DEFAULT NOW(),
    UNIQUE(case_id, officer_email)
);
""")
conn.commit()
print("Created favorite_cases table")

# 2. Read the current gfin_server.py to add the API endpoints
with open("/gfin/gfin_server.py", "r") as f:
    server_code = f.read()

# 3. Add favorite cases API endpoints
favorites_api = '''
# === FAVORITE CASES API ===

@app.get("/api/cases/favorites")
async def get_favorite_cases(request: Request):
    """Get all favorite cases for the current officer"""
    officer = get_officer_from_request(request)
    if not officer:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT f.id, f.case_id, f.notes, f.created_date,
               c.status, c.target, c.classification, c.summary, 
               c.confidence, c.victim_count, c.total_loss_usd,
               c.priority, c.case_phase, c.assigned_to_officer,
               c.created_date as case_created
        FROM favorite_cases f
        LEFT JOIN cases c ON f.case_id = c.case_id
        WHERE f.officer_email = %s
        ORDER BY f.created_date DESC
    """, (officer.get("email", ""),))
    favorites = []
    for row in cur.fetchall():
        favorites.append({
            "id": row[0],
            "case_id": row[1],
            "notes": row[2],
            "favorited_at": row[3].isoformat() if row[3] else None,
            "status": row[4],
            "target": row[5],
            "classification": row[6],
            "summary": row[7],
            "confidence": row[8],
            "victim_count": row[9],
            "total_loss_usd": row[10],
            "priority": row[11],
            "case_phase": row[12],
            "assigned_to_officer": row[13],
            "case_created": row[14].isoformat() if row[14] else None
        })
    conn.close()
    return {"favorites": favorites, "count": len(favorites)}

@app.post("/api/cases/{case_id}/favorite")
async def add_favorite_case(case_id: str, request: Request):
    """Add a case to favorites"""
    officer = get_officer_from_request(request)
    if not officer:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    body = await request.json() if request.headers.get("content-type") == "application/json" else {}
    notes = body.get("notes", "")
    
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO favorite_cases (case_id, officer_email, officer_id, notes)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (case_id, officer_email) DO UPDATE SET notes = %s
        """, (case_id, officer.get("email", ""), officer.get("id"), notes, notes))
        conn.commit()
        conn.close()
        return {"success": True, "message": f"Case {case_id} added to favorites"}
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/cases/{case_id}/favorite")
async def remove_favorite_case(case_id: str, request: Request):
    """Remove a case from favorites"""
    officer = get_officer_from_request(request)
    if not officer:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        DELETE FROM favorite_cases 
        WHERE case_id = %s AND officer_email = %s
    """, (case_id, officer.get("email", "")))
    conn.commit()
    conn.close()
    return {"success": True, "message": f"Case {case_id} removed from favorites"}

@app.get("/api/cases/{case_id}/favorite")
async def check_favorite_case(case_id: str, request: Request):
    """Check if a case is in the officer's favorites"""
    officer = get_officer_from_request(request)
    if not officer:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, notes FROM favorite_cases 
        WHERE case_id = %s AND officer_email = %s
    """, (case_id, officer.get("email", "")))
    row = cur.fetchone()
    conn.close()
    return {"is_favorite": bool(row), "notes": row[1] if row else None}

'''

# Insert before the last few lines of server
# Find a good insertion point — after the case detail endpoint
insert_marker = '# === OSINT'
if insert_marker in server_code:
    server_code = server_code.replace(insert_marker, favorites_api + '\n' + insert_marker)
    print("Added favorites API to server code")
else:
    # Insert before the main block
    insert_marker2 = "if __name__"
    if insert_marker2 in server_code:
        server_code = server_code.replace(insert_marker2, favorites_api + '\n\n' + insert_marker2)
        print("Added favorites API to server code (before main)")

with open("/gfin/gfin_server.py", "w") as f:
    f.write(server_code)
print("Server updated with favorites API")

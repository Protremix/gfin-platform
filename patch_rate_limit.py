#!/usr/bin/env python3
"""Patch gfin_security.py to exempt internal endpoints from rate limiting"""

with open("/gfin/packages/services/gfin_security.py", "r") as f:
    code = f.read()

# Find the rate limiting block and add localhost/internal exemption
old = """        # Rate limiting
        is_auth = '/police/login' in str(request.url.path)
        max_req = AUTH_RATE_LIMIT_MAX if is_auth else RATE_LIMIT_MAX
        
        if not rate_limiter.check(client_ip, max_req):
            return JSONResponse(status_code=429, content={"detail": "Too many requests. Please try again later."})"""

new = """        # Skip rate limiting for internal localhost endpoints
        is_internal = client_ip in ('127.0.0.1', '::1', 'localhost', 'unknown') and '/internal/' in str(request.url.path)
        
        # Rate limiting (skip for internal localhost)
        if not is_internal:
            is_auth = '/police/login' in str(request.url.path)
            max_req = AUTH_RATE_LIMIT_MAX if is_auth else RATE_LIMIT_MAX
            
            if not rate_limiter.check(client_ip, max_req):
                return JSONResponse(status_code=429, content={"detail": "Too many requests. Please try again later."})"""

if old in code:
    code = code.replace(old, new, 1)
    with open("/gfin/packages/services/gfin_security.py", "w") as f:
        f.write(code)
    print("Patched rate limiter to exempt internal localhost endpoints")
else:
    print("Block not found — checking flexible match")
    # Try without exact whitespace
    if "Rate limiting" in code and "rate_limiter.check" in code:
        idx = code.find("# Rate limiting")
        end_idx = code.find("# Check query parameters")
        if idx > 0 and end_idx > 0:
            print("Context:", repr(code[idx:end_idx]))

#!/bin/bash
# Renew Let us Encrypt certificates and deploy to Docker Nginx
certbot renew --quiet
if [ $? -eq 0 ]; then
    cp /etc/letsencrypt/live/gfin-system.com/fullchain.pem /gfin/nginx/certs/cert.pem
    cp /etc/letsencrypt/live/gfin-system.com/privkey.pem /gfin/nginx/certs/key.pem
    chmod 644 /gfin/nginx/certs/cert.pem
    chmod 600 /gfin/nginx/certs/key.pem
    docker restart gfin_nginx
    echo "SSL renewed and deployed at $(date)"
fi

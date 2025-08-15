#!/bin/bash
set -e

DOMAINS=( "c.doneztech.com","loginc.doneztech.com","democ.doneztech.com" )
EMAIL=admin@doneztech.com
WEBROOT=/var/www/certbot
CERTBOT_PATH=/opt/ssl/certbot

for DOMAIN in "${DOMAINS[@]}"; do
    if [ ! -f "$CERTBOT_PATH/live/$DOMAIN/fullchain.pem" ]; then
        echo "no cert found. Bootstrapping https..."
    
        docker-compose run --rm certbot certbot certonly --webroot -w $WEBROOT -d $DOMAIN   -d www.$DOMAIN \  --email $EMAIL --agree-tos --non-interactive
               
    fi
done
cp nginx/nginx-https.conf nginx/conf.d/default.conf
docker-compose restart nginx
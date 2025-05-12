#!/bin/bash
set -e

DOMAIN=doneztech.com
EMAIL=admin@doneztech.com
WEBROOT=/var/www/certbot
CERTBOT_PATH=/opt/ssl/certbot

if [ ! -f "$CERTBOT_PATH/live/$DOMAIN/fullchain.pem" ]; then
    echo "no cert found. Bootstrapping https..."
    
    cp nginx/nginx-http.conf nginx/conf.d/default.conf
    docker-compose up -d nginx
    
    sleep 5
    
    docker compose run --rm certbot certonly \
    --webroot -w $WEBROOT \
    -d $DOMAIN -d odoo.$DOMAIN \
    --email $EMAIL --agree-tos --non-interactive
    
    cp nginx/nginx-https.conf nginx/conf.d/default.conf
    docker-compose restart nginx
else
    echo "Cert already exists, skipping bootstrap."
fi
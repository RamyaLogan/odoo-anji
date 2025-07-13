# -------- Stage 1: Build Stage --------
FROM python:3.11-slim-bookworm AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc python3-dev libpq-dev libxml2-dev libxslt1-dev \
    zlib1g-dev libjpeg-dev libldap2-dev libsasl2-dev libssl-dev \
    git wget xz-utils fontconfig libfreetype6 libjpeg62-turbo libx11-6 libxext6 libxrender1

WORKDIR /opt/odoo

COPY ./odoo/requirements.txt .

RUN pip install --upgrade pip && \
    pip install \
        -r requirements.txt \
        psycopg2-binary \
        openpyxl \
        boto3 \
        google-auth \
        greenlet==2.0.2 \
        gevent==22.10.2 \
        zope.event==5.1

# -------- Stage 2: Runtime Stage --------
FROM python:3.11-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc python3-dev libpq-dev libxml2-dev libxslt1-dev \
    zlib1g-dev libjpeg-dev libldap2-dev libsasl2-dev libssl-dev \
    git wget xz-utils fontconfig libfreetype6 libjpeg62-turbo libx11-6 libxext6 libxrender1 \
 && wget https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-3/wkhtmltox_0.12.6.1-3.bookworm_amd64.deb \
 && dpkg -i wkhtmltox_0.12.6.1-3.bookworm_amd64.deb \
 && apt-get install -f -y \
 && rm wkhtmltox_0.12.6.1-3.bookworm_amd64.deb \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/odoo

# 🔥 Install all Python packages HERE (final runtime image)
COPY ./odoo/requirements.txt .
RUN pip install --upgrade pip
RUN pip install \
    -r requirements.txt \
    psycopg2-binary \
    openpyxl \
    boto3 \
    google-auth \
    greenlet==2.0.2 \
    gevent==22.10.2 \
    zope.event==5.1

# ✅ Copy app code
COPY ./odoo /opt/odoo
COPY ./custom_addons /opt/odoo/custom_addons
COPY ./config/odoo.conf /etc/odoo/odoo.conf

# ✅ Create user and set perms
RUN useradd -m -U -r -d /opt/odoo odoo && \
    chown -R odoo:odoo /opt/odoo /etc/odoo && \
    mkdir -p /opt/odoo/.local && chown -R odoo:odoo /opt/odoo/.local

USER odoo

EXPOSE 8069 8071 8072

CMD ["odoo-bin", "-c", "/etc/odoo/odoo.conf"]
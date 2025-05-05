# FROM python:3.11-slim

# RUN apt-get update && apt-get install -y \
#     git gcc python3-dev libxml2-dev libxslt1-dev zlib1g-dev \
#     libsasl2-dev libldap2-dev libssl-dev libpq-dev \
#     wget xz-utils libjpeg-dev libpng-dev libjpeg62-turbo-dev libfreetype6-dev \
#     netcat-openbsd

# WORKDIR /opt/odoo

# COPY ./odoo /opt/odoo
# COPY ./wait-for-it.sh /wait-for-it.sh
# COPY ./config/odoo.conf /etc/odoo/odoo.conf

# RUN chmod +x /wait-for-it.sh
# RUN pip install --upgrade pip
# RUN pip install psycopg2-binary
# RUN pip install -r /opt/odoo/requirements.txt || true  # in case requirements.txt missing temporarily

# EXPOSE 8069

# CMD ["bash"]

# -------- Stage 1: Build Stage --------
    FROM python:3.11-slim-bookworm AS builder

    # Install build dependencies
    RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential gcc python3-dev libpq-dev libxml2-dev libxslt1-dev \
        zlib1g-dev libjpeg-dev libldap2-dev libsasl2-dev libssl-dev git wget xz-utils fontconfig libfreetype6 libjpeg62-turbo libx11-6 libxext6 libxrender1
    
    WORKDIR /opt/odoo
    
    # Copy only requirements.txt
    COPY ./odoo/requirements.txt /opt/odoo/requirements.txt
    
    RUN pip install --upgrade pip
    RUN pip install --prefix=/install psycopg2-binary
    RUN pip install --prefix=/install -r /opt/odoo/requirements.txt || true
    
    # -------- Stage 2: Runtime Stage --------
    FROM python:3.11-slim-bookworm
    
    # Install runtime system dependencies
    RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 libxml2 libxslt1.1 zlib1g libjpeg62-turbo libldap-2.5-0 \
        libsasl2-2 libssl3 fontconfig libfreetype6 libjpeg62-turbo libx11-6 libxext6 libxrender1 wget xz-utils wkhtmltopdf && \
        rm -rf /var/lib/apt/lists/*
    
    WORKDIR /opt/odoo
    
    # Copy Odoo source code
    COPY ./odoo /opt/odoo
    
    # Copy config file
    COPY ./config/odoo.conf /etc/odoo/odoo.conf
    
    # Copy installed Python packages
    COPY --from=builder /install /usr/local
    
    # Create non-root user
    RUN useradd -m -U -r -d /opt/odoo odoo
    RUN chown -R odoo:odoo /opt/odoo /etc/odoo
    RUN mkdir -p /opt/odoo/.local && chown -R odoo:odoo /opt/odoo/.local

    USER odoo
    
    EXPOSE 8069 8071 8072
    
    CMD ["bash"]
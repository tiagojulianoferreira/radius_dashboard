#!/bin/bash
# install.sh - Instalação do Dashboard RADIUS
set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
REPO_RAW="https://raw.githubusercontent.com/tiagojulianoferreira/radius_dashboard/refs/heads/main"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     RADIUS Dashboard - Script de Instalação Automática    ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"

if [ "$EUID" -ne 0 ]; then echo -e "${RED}❌ Execute como root${NC}"; exit 1; fi

# Verifica conexão
echo -e "${YELLOW}[1/5] Verificando conexão...${NC}"
if ! curl -s --connect-timeout 5 -o /dev/null -w "%{http_code}" https://raw.githubusercontent.com | grep -q "200\|301\|302"; then
    echo -e "${RED}❌ Sem conexão com GitHub${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Conexão ok${NC}"

# Instala dependências
echo -e "${YELLOW}[2/5] Instalando dependências...${NC}"
apt update -qq && apt install -y -qq nginx python3 python3-venv wget curl

# Cria diretórios
mkdir -p /opt/radius_dashboard/templates/css /opt/radius_dashboard/templates/js /var/www/html/radius

# Baixa arquivos do repositório
echo -e "${YELLOW}[3/5] Baixando arquivos...${NC}"
for file in gerar_painel.py templates/index.html templates/css/style.css templates/js/dashboard.js config/nginx-radius.conf; do
    wget -q -O /opt/radius_dashboard/${file} ${REPO_RAW}/${file}
done
chmod +x /opt/radius_dashboard/gerar_painel.py

# Configura Nginx
echo -e "${YELLOW}[4/5] Configurando Nginx...${NC}"
cp /opt/radius_dashboard/config/nginx-radius.conf /etc/nginx/sites-available/radius
ln -sf /etc/nginx/sites-available/radius /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

# Configura serviço
echo -e "${YELLOW}[5/5] Configurando serviço...${NC}"
cat > /etc/systemd/system/radius-dashboard.service << 'EOF'
[Unit]
Description=Dashboard RADIUS
After=network.target

[Service]
Type=oneshot
ExecStart=/opt/radius_dashboard/venv/bin/python3 /opt/radius_dashboard/gerar_painel.py
User=www-data
Group=www-data
EOF

cat > /etc/systemd/system/radius-dashboard.timer << 'EOF'
[Unit]Description=Timer Dashboard RADIUS
[Timer]OnBootSec=1min OnUnitActiveSec=5min
[Install]WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable radius-dashboard.timer
systemctl start radius-dashboard.timer

# Gera dashboard
echo -e "${YELLOW}📊 Gerando dashboard...${NC}"
/opt/radius_dashboard/venv/bin/python3 /opt/radius_dashboard/gerar_painel.py

echo -e "${GREEN}✅ Instalação concluída!${NC}"
echo -e "📊 Acesse: ${BLUE}http://$(hostname -I | cut -d' ' -f1):8080/radius/index.html${NC}"

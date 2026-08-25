# RADIUS Dashboard - FreeRADIUS Monitoring

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Nginx](https://img.shields.io/badge/Nginx-1.18+-green.svg)](https://nginx.org)

Dashboard para monitoramento de autenticações FreeRADIUS com análise histórica, identificação de fabricantes e métricas de performance.

## 📊 Funcionalidades

### 📈 Métricas Gerais
- Total de autenticações bem-sucedidas e rejeitadas
- Taxa de falhas geral
- Período dos dados analisados

### 📱 Análise por Fabricante
- Identificação do fabricante do dispositivo via MAC Address (OUI)
- Suporte para MACs randomizados (iOS/Android)
- Gráfico de pizza com distribuição de falhas

### 🔒 Análise de Erros
- Classificação por tipo de erro:
  - Senha incorreta
  - Erro de Certificado CA
  - Certificado inválido
  - Erro TLS
  - Erro Interno TLS

### 📅 Análise Temporal
- Falhas por hora do dia
- Falhas por dia da semana
- Série histórica (últimos 60 dias)

### 👤 Análise por Usuário
- Top 15 usuários com mais falhas
- Identificação de padrões de comportamento

### 📊 Dados do Dia Atual
- Visualização separada das estatísticas do dia
- Comparação rápida com histórico

## 🛠️ Stack Tecnológica

### Backend
- **Python 3.8+** - Processamento de logs
- **FreeRADIUS** - Fonte dos dados- **Systemd** - Agendamento e serviços

### Frontend
- **HTML5 + CSS3** - Interface responsiva
- **Chart.js** - Visualização de dados
- **JavaScript** - Gráficos interativos

### Infraestrutura
- **Nginx** - Servidor web
- **Nginx Proxy Manager** - Proxy reverso (opcional)
- **Logrotate** - Rotação de logs

## 📋 Pré-requisitos

- **Ubuntu/Debian** (ou derivados)
- **FreeRADIUS** instalado e configurado
- **Python 3.8+** com venv
- **Nginx** instalado
- **Acesso root** para instalação

## 🚀 Instalação

### Instalação Automática (Recomendado)

```bash
# Baixe e execute o script de instalação
curl -sSL https://raw.githubusercontent.com/seu-repo/radius-dashboard/main/install.sh | sudo bash

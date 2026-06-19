#!/bin/bash
cd "$(dirname "$0")"
echo "🌸 CRM ИМПУЛЬС запущена"
echo "Открой в браузере: http://localhost:8888/crm.html"
echo "Нажми Ctrl+C для остановки"
python3 -m http.server 8888

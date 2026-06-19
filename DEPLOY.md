# Бот «Импульс» — Деплой на Railway

## 1. Залить код на GitHub

```bash
cd ~/Desktop/ИМПУЛЬС/bot

# Создать репозиторий (если нет)
git init
git add .
git commit -m "initial"

# Создать репозиторий на github.com, потом:
git remote add origin https://github.com/ВАШ_ЛОГИН/impulse-bot.git
git branch -M main
git push -u origin main
```

## 2. Зайти на Railway

1. https://railway.app → Login with GitHub
2. Нажать **New Project** → **Deploy from GitHub repo**
3. Выбрать `impulse-bot`
4. Railway сам соберёт и запустит

## 3. Добавить переменную

В Railway: проект → Variables → добавить:

```
BOT_TOKEN = 8976558743:AAG1V6pz--7MHXS4muOrVJpC6dsOJ9o_oug
```

## 4. Всё

Бот запущен. Зайти в логов — Railway → Deployments → View logs.

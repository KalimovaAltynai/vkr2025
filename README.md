# Клонировать репозиторий
git clone https://github.com/KalimovaAltynai/vkr2025.git
cd vkr2025

# Создать виртуальное окружение
python -m venv .venv
source .venv/bin/activate  # или .venv\Scripts\activate на Windows

# Установить зависимости
pip install -r requirements.txt

# Запустить сервер
uvicorn main:app --reload

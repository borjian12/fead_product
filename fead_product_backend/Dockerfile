FROM python:3.11-slim

WORKDIR /app

# نصب dependencies سیستم
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

# نصب Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# کپی کد
COPY . .

# ایجاد دایرکتوری برای اسکرین‌شات‌ها
RUN mkdir -p /app/screenshots

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
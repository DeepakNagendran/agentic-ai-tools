FROM python:3.10-slim

WORKDIR /app

ENV PYTHONPATH="${PYTHONPATH}:/app"

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8501

CMD ["streamlit", "run", "app/ui/chat_ui.py", "--server.port=8501", "--server.address=0.0.0.0"]

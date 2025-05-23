FROM python:3.11-slim

WORKDIR /app

# Kopiowanie requirements i instalacja zależności
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopiowanie kodu CLI
COPY cli.py .

RUN echo 'alias cli="python cli.py"' >> /root/.bashrc

CMD ["bash"]

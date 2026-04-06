FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && \
    apt-get install -y gcc git libgl1 libglib2.0-0 && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip

COPY . .

RUN pip install "uvicorn[standard]==0.29.0" "fastapi==0.110.0" \
    "pydantic==2.6.4" "numpy>=1.18.5,<1.24.0" "astropy==6.0.1" \
    "opencv-python>=4.1.1" "torch==2.0.1" "torchvision==0.15.2"

RUN mkdir -p /app/reports /app/results

ENTRYPOINT ["uvicorn", "api.main:start", "--host", "0.0.0.0", "--port", "8000"]
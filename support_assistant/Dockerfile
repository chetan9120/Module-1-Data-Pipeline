FROM python:3.12-slim

WORKDIR /app

# System deps for sentence-transformers/torch build wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# MOCK_LLM defaults to "1" (mock/graded baseline). Override with
# `-e MOCK_LLM=0 -e GROQ_API_KEY=...` to opt into the real-LLM extension.
ENV MOCK_LLM=1
ENV PORT=7860

EXPOSE 7860

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]

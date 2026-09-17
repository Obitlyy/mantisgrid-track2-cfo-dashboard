FROM python:3.12.7-slim@sha256:60d9996b6a8a3689d36db740b49f4327be3be09a21122bd02fb8895abb38b50d AS runtime
WORKDIR /app
COPY requirements.lock.txt requirements.decision.lock.txt ./
RUN pip install --no-cache-dir -r requirements.decision.lock.txt
COPY api ./api
COPY decision ./decision
COPY mcp_layer ./mcp_layer
COPY scripts ./scripts
COPY contracts ./contracts
COPY starter/claims.schema.json ./starter/claims.schema.json
CMD ["uvicorn", "decision.app:app", "--host", "0.0.0.0", "--port", "8000"]

FROM runtime AS tools
COPY requirements.dev.lock.txt ./
RUN pip install --no-cache-dir -r requirements.dev.lock.txt

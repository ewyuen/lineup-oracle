FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
COPY lineup_oracle ./lineup_oracle
COPY data ./data
# Editable install keeps lineup_oracle/../data at /app/data, where State.load looks.
# events.jsonl is gitignored, so it is generated here with the committed seed.
RUN pip install --no-cache-dir -e . \
    && python -m lineup_oracle.events --seed 42 --out data/events.jsonl \
    && useradd -r app && chown -R app /app
USER app
EXPOSE 8000
CMD ["uvicorn", "lineup_oracle.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]

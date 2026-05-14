# BuenCholloTech

Monorepo de BuenCholloTech.

## Estructura

```text
buenchollo-api/  Backend FastAPI
buenchollo-web/  Frontend React/TypeScript
```

`API_Amazon_CloudCode/` se mantiene fuera del repositorio como proyecto legacy de referencia.

## Backend

```bash
cd buenchollo-api
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

## Frontend

Consulta las instrucciones dentro de `buenchollo-web/`.

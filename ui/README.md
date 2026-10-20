# Lineup Oracle UI

The UI is an ASP.NET Razor Pages app that uses HTMX to call the Lineup Oracle FastAPI service.

## Run

Start the API from `backend`:

```powershell
uvicorn lineup_oracle.api:create_app --factory
```

In another terminal, run the UI from the repository root:

```powershell
dotnet run --project ui/LineupOracle.Ui
```

The API base URL defaults to `http://127.0.0.1:8000`. Override it with the .NET configuration key `LineupApi:BaseUrl`, for example by setting the environment variable `LineupApi__BaseUrl`.

## Test

From the repository root:

```powershell
dotnet test ui
```

# NEOSSat-Astronomy-Image-Analysis
NEOSSat Image Analyzer processes astronomical images continuously collected 
by the [NEOSSat space telescope](https://www.asc-csa.gc.ca/eng/satellites/neossat/) to automatically detect and report anomalies. 

## Quick Start
```bash
git clone https://github.com/julianadelgado/NEOSSat-Astronomy-Image-Analysis.git
cd your-repo
```
Install the dependencies for the mode(s) you want to use:
```
uv sync --extra api
uv sync --extra cli
```
Or the make command: `make sync-all`

Then run the desired script:

| Command | Description |
|---|---|
| `neossat-api` | Start the REST API server on port 8000 |
| `neossat-cli` | Run the terminal CLI  |

Or use make commands directly:

| Command | Description |
|---|---|
| `make sync-all` | Sync all dependencies |
| `make api` | Run the NEOSSat API |
| `make cli ARGS="..."` | Run the CLI with custom arguments |
| `make streaks` | Run the CLI with `--streaks` |
| `make stars` | Run the CLI with `--stars` |
| `make stack` | Run the CLI with `--image-stacking` |
| `make all` | Run the CLI with all tasks |
| `make test` | Run tests with pytest |
| `make help` | Print all available commands |

## Email Setup

Analysis results are sent via SMTP. Before running, set the following environment variables:

| Variable | Description |
|---|---|
| `SMTP_SERVER` | Your provider's SMTP server (e.g. `smtp.gmail.com`, `smtp.office365.com`) |
| `SMTP_USER` | Your email address |
| `SMTP_PASSWORD` | Your app password |
| `SMTP_PORT` | Defaults to `587` |

**Generating an App Password:**

Most providers require an app-specific password rather than your account password:
- **Gmail:** Google Account → Security → 2-Step Verification → App passwords
- **Outlook:** Microsoft Account → Security → Advanced security options → App passwords

**Setting the variables:**

```bash
# macOS/Linux
export SMTP_SERVER="smtp.gmail.com"
export SMTP_USER="you@example.com"
export SMTP_PASSWORD="your-app-password"

# Windows
set SMTP_SERVER=smtp.gmail.com
set SMTP_USER=you@example.com
set SMTP_PASSWORD=your-app-password
```

## Documentation

For more details, see the [wiki](wiki/).

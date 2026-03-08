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
uv sync --extra gui
```
Then run the desired script:

| Command | Description |
|---|---|
| `neossat-api` | Start the REST API server on port 8000 |
| `neossat-cli` | Run the terminal CLI  |
| `neossat-gui` | Launch the desktop GUI |


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

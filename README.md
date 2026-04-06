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

Notifications that the processes have finished are sent via SMTP. Before running, set the following variables in the `config.yaml` file:

| Variable | Description |
|---|---|
| `smtp_server` | Your provider's SMTP server (e.g. `smtp.gmail.com`, `smtp.office365.com`) |
| `smtp_user` | Your email address |
| `smtp_password` | Your app password as a 16 character code without spaces|
| `smtp_port` | Defaults to `587` |

**Generating an App Password:**

Most providers require an app-specific password rather than your account password:
- **Gmail:** Google Account → Security → 2-Step Verification → App passwords
- **Outlook:** Microsoft Account → Security → Advanced security options → App passwords

## Documentation

For more details, see the [Wiki](https://github.com/julianadelgado/NEOSSat-Astronomy-Image-Analysis/wiki).

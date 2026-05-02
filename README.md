# Family Hero Hub V1.2

Gamified financial education platform for children.

## Quick Start

1.  **Configure Environment:**
    ```bash
    cp .env.example .env
    # Edit .env with your Google OAuth credentials and parent emails
    ```

2.  **Start the App:**
    ```bash
    docker compose up -d --build
    ```

3.  **Access the App:**
    - Frontend: [http://localhost:5173](http://localhost:5173)
    - Backend Health: [http://localhost:8000/api/health](http://localhost:8000/api/health)

## Core Commands

- **Stop:** `docker compose down`
- **Logs:** `docker compose logs -f`
- **Backup Database:** `./scripts/backup_sqlite.sh`
- **Run Backend Tests:** `docker compose exec backend pytest`

## Documentation

- [Google OAuth Setup](docs/GOOGLE_OAUTH.md)
- [Cloudflare Tunnel Deployment](docs/CLOUDFLARE_TUNNEL.md)
- [Future APK (Capacitor) Guide](docs/APK_FUTURE.md)
- [Security Checklist](SECURITY_CHECKLIST.md)

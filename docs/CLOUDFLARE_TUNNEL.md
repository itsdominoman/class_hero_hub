# Cloudflare Tunnel Deployment

> **Current status:** Family Hero Hub currently uses **Caddy**, not Cloudflare Tunnel.
>
> This document is retained only as a future/optional deployment reference. Do not treat it as the current production setup.


This app is designed to be deployed behind a Cloudflare Tunnel using a single hostname.

## Configuration

1.  **Cloudflare Dashboard:**
    - Set up a Tunnel in the Cloudflare One dashboard.
    - Route a public hostname (e.g., `families.loginto.me`) to the local service `http://frontend:5173` or a reverse proxy.
2.  **Hostname Routing:**
    - Path `/api/*` -> `http://backend:8000/api/*`
    - Path `/*` -> `http://frontend:5173/*`
    - Alternatively, use a single entry point that handles routing.

## Example `cloudflared` Config

```yaml
tunnel: <TUNNEL_ID>
credentials-file: /etc/cloudflared/<TUNNEL_ID>.json

ingress:
  - hostname: families.loginto.me
    path: /api
    service: http://backend:8000
  - hostname: families.loginto.me
    service: http://frontend:5173
  - service: http_status:404
```

## Environment Update

Update your `.env` file for production:
```env
PUBLIC_APP_URL=https://families.loginto.me
API_BASE_URL=https://families.loginto.me
GOOGLE_REDIRECT_URI=https://families.loginto.me/api/auth/google/callback
CORS_ORIGINS=https://families.loginto.me
DEV_AUTH_ENABLED=false
```

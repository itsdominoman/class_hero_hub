> Historical note: This document was inherited from Family Hero Hub and is preserved as historical context for the Class Hero Hub fork. It may describe old domains, paths, product assumptions, or infrastructure that are not current.

# Cloudflare Tunnel Deployment

> **Current status:** Family Hero Hub currently uses **Caddy**, not Cloudflare Tunnel.
>
> This document is retained only as a future/optional deployment reference. Do not treat it as the current production setup.
>
> Private admin and Hermes access use the WireGuard mesh, not Cloudflare Tunnel.


This app is designed to be deployed behind a Cloudflare Tunnel using a single hostname.

## Configuration

1.  **Cloudflare Dashboard:**
    - Set up a Tunnel in the Cloudflare One dashboard.
    - Route a public hostname (e.g., `familyherohub.com`) to the local service `http://frontend:5173` or a reverse proxy.
2.  **Hostname Routing:**
    - Path `/api/*` -> `http://backend:8000/api/*`
    - Path `/*` -> `http://frontend:5173/*`
    - Alternatively, use a single entry point that handles routing.

## Example `cloudflared` Config

```yaml
tunnel: <TUNNEL_ID>
credentials-file: /etc/cloudflared/<TUNNEL_ID>.json

ingress:
  - hostname: familyherohub.com
    path: /api
    service: http://backend:8000
  - hostname: familyherohub.com
    service: http://frontend:5173
  - service: http_status:404
```

## Environment Update

Update your `.env` file for production:
```env
PUBLIC_APP_URL=https://familyherohub.com
API_BASE_URL=https://familyherohub.com
GOOGLE_REDIRECT_URI=https://familyherohub.com/api/auth/google/callback
CORS_ORIGINS=https://familyherohub.com
DEV_AUTH_ENABLED=false
```

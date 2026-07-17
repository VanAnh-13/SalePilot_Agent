# Zalo OA integration

## Stub (default)

- `ZALO_CLIENT=mock`  
- `POST /webhooks/zalo` accepts OA-like JSON  
- Replies go to `outbox_messages` (Dashboard Zalo inbox)  
- `python -m scripts.simulate_zalo`  

## Real OA later

1. Create Zalo OA app, enable webhook  
2. Public HTTPS URL → `/webhooks/zalo`  
3. Set:
   ```
   ZALO_CLIENT=http
   ZALO_OA_ACCESS_TOKEN=...
   ZALO_WEBHOOK_SECRET=...
   ZALO_VERIFY_MODE=strict
   ```
4. Implement token refresh if needed in `HttpZaloOAClient`  

Interface: `ZaloOAClient` protocol in `backend/app/channels/zalo/client.py`.

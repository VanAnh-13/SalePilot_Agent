// Same default as the server-side admin proxy (app/api/admin/route.ts):
// set NEXT_PUBLIC_API_URL for deployments; without it both the chat client
// and the admin proxy target the local dev backend.
export const DEFAULT_BACKEND_URL = "http://localhost:8000";

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || DEFAULT_BACKEND_URL;

// Backend endpoint paths used by the chat client.
export const CHAT_PATH = "/chat";
export const CHAT_STREAM_PATH = "/chat/stream";

// Server-side BFF proxy path the browser calls for admin endpoints.
export const ADMIN_PROXY_PATH = "/api/admin";

export const WEB_CHANNEL = "web";
export const WEB_CUSTOMER_NAME = "Khách web";

// localStorage key for the owner token that gates the admin BFF proxy
// (app/api/admin/route.ts checks X-Owner-Token against the server OWNER_TOKEN).
export const OWNER_TOKEN_KEY = "salepilot_owner_token";

/** The POST body shared by the batch and streaming chat calls. */
export function chatBody(message: string, externalId: string) {
  return {
    message,
    external_id: externalId,
    customer_name: WEB_CUSTOMER_NAME,
    channel: WEB_CHANNEL,
  };
}

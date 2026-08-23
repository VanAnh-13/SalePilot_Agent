import { timingSafeEqual } from "crypto";
import { NextRequest, NextResponse } from "next/server";

import { DEFAULT_BACKEND_URL } from "@/lib/constants";

/**
 * Server-side BFF proxy for admin-only backend endpoints.
 *
 * Reads ADMIN_API_KEY from a server-only env var (never NEXT_PUBLIC_),
 * attaches X-Admin-Token, and forwards to the backend.
 *
 * Usage: GET /api/admin?path=/leads
 *        GET /api/admin?path=/memory
 *        POST /api/admin?path=/jobs/tick
 */

const BACKEND_URL =
  process.env.BACKEND_URL?.replace(/\/$/, "") ||
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") ||
  DEFAULT_BACKEND_URL;

function safeCompare(a: string, b: string): boolean {
  if (a.length !== b.length) return false;
  try {
    return timingSafeEqual(Buffer.from(a), Buffer.from(b));
  } catch {
    return false;
  }
}

async function proxyToBackend(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const path = searchParams.get("path");

  if (!path) {
    return NextResponse.json(
      { error: "Missing 'path' query parameter" },
      { status: 400 },
    );
  }

  // Authenticate the BROWSER caller with an owner token (separate from the
  // server-only ADMIN_API_KEY). Without this gate the proxy nullifies the
  // backend's admin auth: any reachable client could dump /leads, /memory, …
  const ownerToken = process.env.OWNER_TOKEN;
  if (!ownerToken) {
    return NextResponse.json(
      { error: "OWNER_TOKEN not configured on server" },
      { status: 503 },
    );
  }
  if (!safeCompare(req.headers.get("x-owner-token") || "", ownerToken)) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const adminKey = process.env.ADMIN_API_KEY;
  if (!adminKey) {
    return NextResponse.json(
      { error: "ADMIN_API_KEY not configured on server" },
      { status: 503 },
    );
  }

  // Only allow known admin paths to prevent open proxy abuse.
  const allowedPrefixes = [
    "/leads",
    "/memory",
    "/jobs",
    "/outbox",
    "/runs",
  ];
  const normalised = path.startsWith("/") ? path : `/${path}`;
  if (!allowedPrefixes.some((p) => normalised.startsWith(p))) {
    return NextResponse.json(
      { error: `Path '${normalised}' is not an allowed admin endpoint` },
      { status: 403 },
    );
  }

  const targetUrl = `${BACKEND_URL}${normalised}`;

  try {
    const resp = await fetch(targetUrl, {
      method: req.method,
      headers: {
        "Content-Type": "application/json",
        "X-Admin-Token": adminKey,
      },
      body: req.method !== "GET" ? await req.text() : undefined,
      cache: "no-store",
    });

    const data = await resp.text();
    return new NextResponse(data, {
      status: resp.status,
      headers: { "Content-Type": resp.headers.get("Content-Type") || "application/json" },
    });
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    return NextResponse.json(
      { error: `Backend unreachable: ${message}` },
      { status: 502 },
    );
  }
}

export async function GET(req: NextRequest) {
  return proxyToBackend(req);
}

export async function POST(req: NextRequest) {
  return proxyToBackend(req);
}

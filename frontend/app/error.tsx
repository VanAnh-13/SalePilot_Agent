"use client";

import { IconAlert } from "@/components/Icons";

export default function ErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <main className="stack" style={{ alignItems: "center", padding: "8vh 0" }}>
      <div className="card" style={{ maxWidth: 520, textAlign: "center", padding: "36px 32px" }}>
        <span className="icon-badge lg rose" style={{ margin: "0 auto 18px" }} aria-hidden>
          <IconAlert width={24} height={24} />
        </span>
        <h1 style={{ fontSize: 22, margin: "0 0 8px" }}>Có lỗi xảy ra</h1>
        <p className="muted" style={{ marginTop: 0 }}>
          {error.message || "Đã xảy ra lỗi không mong muốn."}
        </p>
        {error.digest && (
          <p className="muted" style={{ fontSize: 12 }}>
            digest: <code className="md-code">{error.digest}</code>
          </p>
        )}
        <div className="row" style={{ justifyContent: "center", marginTop: 20 }}>
          <button type="button" className="btn" onClick={reset}>
            Thử lại
          </button>
          <a className="btn ghost" href="/">
            Về trang chủ
          </a>
        </div>
      </div>
    </main>
  );
}

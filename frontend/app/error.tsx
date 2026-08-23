"use client";

export default function ErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div style={{ padding: "2rem", textAlign: "center" }}>
      <h2>Có lỗi xảy ra</h2>
      <p>{error.message || "Đã xảy ra lỗi không mong muốn."}</p>
      <button
        onClick={reset}
        style={{
          marginTop: "1rem",
          padding: "0.5rem 1rem",
          cursor: "pointer",
          borderRadius: "0.25rem",
          border: "1px solid #ccc",
        }}
      >
        Thử lại
      </button>
    </div>
  );
}

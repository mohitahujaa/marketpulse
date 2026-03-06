import { useEffect } from "react";

export default function Toast({ type, message, onClose }) {
  useEffect(() => {
    const t = setTimeout(onClose, 4000);
    return () => clearTimeout(t);
  }, []);

  return (
    <div className={`toast toast-${type}`}>
      <span>{type === "error" ? "⚠️" : "✅"} {Array.isArray(message) ? message.join(", ") : message}</span>
      <button onClick={onClose}>✕</button>
    </div>
  );
}

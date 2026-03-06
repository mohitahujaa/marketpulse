import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { watchlistApi, getErrorMessage } from "../api/client";
import { useAuth } from "../context/AuthContext";
import Toast from "../components/Toast";

export default function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [watchlists, setWatchlists] = useState([]);
  const [toast, setToast] = useState(null);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try {
      const res = await watchlistApi.list();
      setWatchlists(res.data.data);
    } catch (err) {
      setToast({ type: "error", message: getErrorMessage(err) });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      await watchlistApi.create({ name: newName, description: newDesc || undefined });
      setNewName(""); setNewDesc(""); setShowCreate(false);
      setToast({ type: "success", message: "Watchlist created!" });
      load();
    } catch (err) {
      setToast({ type: "error", message: getErrorMessage(err) });
    }
  };

  const handleDelete = async (id, name) => {
    if (!confirm(`Delete "${name}"?`)) return;
    try {
      await watchlistApi.delete(id);
      setToast({ type: "success", message: "Watchlist deleted." });
      load();
    } catch (err) {
      setToast({ type: "error", message: getErrorMessage(err) });
    }
  };

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h2>My Watchlists</h2>
          <p className="subtitle">Welcome back, <strong>{user?.username}</strong> · {user?.role}</p>
        </div>
        <button className="btn-primary" onClick={() => setShowCreate(!showCreate)}>
          {showCreate ? "✕ Cancel" : "+ New Watchlist"}
        </button>
      </div>

      {toast && <Toast {...toast} onClose={() => setToast(null)} />}

      {showCreate && (
        <form className="create-form" onSubmit={handleCreate}>
          <input
            placeholder="Watchlist name"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            required
          />
          <input
            placeholder="Description (optional)"
            value={newDesc}
            onChange={(e) => setNewDesc(e.target.value)}
          />
          <button type="submit" className="btn-primary">Create</button>
        </form>
      )}

      {loading ? (
        <p className="empty-state">Loading…</p>
      ) : watchlists.length === 0 ? (
        <div className="empty-state">
          <p>📋 No watchlists yet.</p>
          <p>Create one to start tracking crypto prices!</p>
        </div>
      ) : (
        <div className="card-grid">
          {watchlists.map((wl) => (
            <div key={wl.id} className="watchlist-card" onClick={() => navigate(`/watchlist/${wl.id}`)}>
              <div className="wl-card-header">
                <h3>{wl.name}</h3>
                <button
                  className="btn-danger-sm"
                  onClick={(e) => { e.stopPropagation(); handleDelete(wl.id, wl.name); }}
                >
                  🗑
                </button>
              </div>
              {wl.description && <p className="wl-desc">{wl.description}</p>}
              <p className="wl-meta">{wl.items.length} coin{wl.items.length !== 1 ? "s" : ""}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

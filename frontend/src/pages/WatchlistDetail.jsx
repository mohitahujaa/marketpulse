import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { marketApi, watchlistApi, getErrorMessage } from "../api/client";
import Toast from "../components/Toast";

export default function WatchlistDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [watchlist, setWatchlist] = useState(null);
  const [prices, setPrices] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [toast, setToast] = useState(null);
  const [loadingPrices, setLoadingPrices] = useState(false);

  const load = async () => {
    try {
      const res = await watchlistApi.get(id);
      setWatchlist(res.data.data);
    } catch {
      navigate("/dashboard");
    }
  };

  useEffect(() => { load(); }, [id]);

  const fetchPrices = async () => {
    setLoadingPrices(true);
    try {
      const res = await watchlistApi.getPrices(id);
      setPrices(res.data.data.prices);
    } catch (err) {
      setToast({ type: "error", message: getErrorMessage(err) });
    } finally {
      setLoadingPrices(false);
    }
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    try {
      const res = await marketApi.search(searchQuery);
      setSearchResults(res.data.data);
    } catch (err) {
      setToast({ type: "error", message: getErrorMessage(err) });
    }
  };

  const handleAddCoin = async (coin) => {
    try {
      await watchlistApi.addCoin(id, { coin_id: coin.id, symbol: coin.symbol });
      setToast({ type: "success", message: `${coin.name} added!` });
      setSearchResults([]);
      setSearchQuery("");
      load();
    } catch (err) {
      setToast({ type: "error", message: getErrorMessage(err) });
    }
  };

  const handleRemoveCoin = async (itemId, symbol) => {
    if (!confirm(`Remove ${symbol}?`)) return;
    try {
      await watchlistApi.removeCoin(id, itemId);
      setToast({ type: "success", message: `${symbol} removed.` });
      load();
      setPrices(null);
    } catch (err) {
      setToast({ type: "error", message: getErrorMessage(err) });
    }
  };

  if (!watchlist) return <div className="loading">Loading…</div>;

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <button className="btn-back" onClick={() => navigate("/dashboard")}>← Back</button>
          <h2>{watchlist.name}</h2>
          {watchlist.description && <p className="subtitle">{watchlist.description}</p>}
        </div>
        <button className="btn-primary" onClick={fetchPrices} disabled={loadingPrices}>
          {loadingPrices ? "Fetching…" : "📊 Fetch Live Prices"}
        </button>
      </div>

      {toast && <Toast {...toast} onClose={() => setToast(null)} />}

      {/* Search & Add Coins */}
      <div className="section">
        <h3>Add Coins</h3>
        <form className="search-form" onSubmit={handleSearch}>
          <input
            placeholder="Search e.g. bitcoin, ethereum…"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          <button type="submit" className="btn-secondary">Search</button>
        </form>

        {searchResults.length > 0 && (
          <div className="search-results">
            {searchResults.map((coin) => (
              <div key={coin.id} className="search-result-item">
                <span><strong>{coin.name}</strong> ({coin.symbol})</span>
                <button className="btn-add" onClick={() => handleAddCoin(coin)}>+ Add</button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Coins List + Prices */}
      <div className="section">
        <h3>Coins ({watchlist.items.length})</h3>
        {watchlist.items.length === 0 ? (
          <p className="empty-state">No coins yet. Search above to add some!</p>
        ) : (
          <div className="coins-table">
            <div className="coins-header">
              <span>Coin</span>
              <span>Price (USD)</span>
              <span>24h Change</span>
              <span>Market Cap</span>
              <span></span>
            </div>
            {watchlist.items.map((item) => {
              const price = prices?.find((p) => p.coin_id === item.coin_id);
              return (
                <div key={item.id} className="coins-row">
                  <span className="coin-name">
                    <strong>{item.symbol}</strong>
                    <small>{item.coin_id}</small>
                  </span>
                  <span>{price ? `$${price.current_price_usd.toLocaleString()}` : "—"}</span>
                  <span className={price ? (price.price_change_24h_pct >= 0 ? "positive" : "negative") : ""}>
                    {price ? `${price.price_change_24h_pct?.toFixed(2)}%` : "—"}
                  </span>
                  <span>{price?.market_cap_usd ? `$${(price.market_cap_usd / 1e9).toFixed(1)}B` : "—"}</span>
                  <button className="btn-danger-sm" onClick={() => handleRemoveCoin(item.id, item.symbol)}>
                    ✕
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

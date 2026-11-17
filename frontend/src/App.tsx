import { useCallback, useState } from "react";
import { AddProduct } from "./AddProduct";
import { clearError, useStore } from "./api";
import { DeviceCard } from "./DeviceCard";
import { LogoMark, Wordmark } from "./Logo";

type Page = "products" | "add";

export function App() {
  const [page, setPage] = useState<Page>("products");
  const [room, setRoom] = useState("Toutes");
  const store = useStore();
  const { info, devices, states, availability, actions, connected, error } = store;
  const [localError, setLocalError] = useState<string | null>(null);
  const onError = useCallback((m: string) => setLocalError(m), []);
  const message = localError ?? error;
  const rooms = ["Toutes", ...Array.from(new Set(devices.map((d) => d.room).filter(Boolean) as string[]))];
  const shown = devices.filter((d) => room === "Toutes" || d.room === room);
  const availableCount = devices.filter((d) => availability[d.topic] ?? d.available).length;

  return (
    <div className="layout">
      <nav className="sidebar" aria-label="Menu principal">
        <div className="brand-line">
          <LogoMark />
          <Wordmark />
        </div>
        <button type="button" className={`nav ${page === "products" ? "current" : ""}`} aria-current={page === "products" ? "page" : undefined} onClick={() => setPage("products")}>
          Mes produits
        </button>
        <button type="button" className={`nav ${page === "add" ? "current" : ""}`} aria-current={page === "add" ? "page" : undefined} onClick={() => setPage("add")}>
          Ajouter un produit
        </button>
        <span className="nav disabled" title="Prévu en bêta">
          Remote Commissioning
        </span>
        <span className="nav disabled" title="Prévu en bêta">
          Télégrammes
        </span>
        <span className="nav disabled" title="Prévu en bêta">
          Réglages
        </span>
        <div className="sidebar-foot">
          <strong>eHomeLabs · open source</strong>
          <span>Version {info?.version ?? "…"} (alpha)</span>
        </div>
      </nav>

      <main className="main">
        <header className="topbar">
          <div>
            <h1>{page === "products" ? "Mes produits" : "Ajouter un produit"}</h1>
            <p className="muted">
              {page === "products"
                ? `${devices.length} produit${devices.length > 1 ? "s" : ""} · ${availableCount} disponible${availableCount > 1 ? "s" : ""}`
                : "Choisissez votre produit dans la bibliothèque, puis suivez sa procédure d'appairage."}
            </p>
          </div>
          <div className="pills-status">
            <span className={`status-pill ${connected ? "ok" : "warn"}`}>
              <span className="dot" />
              {connected ? "Service connecté" : "Connexion au service…"}
            </span>
            <span className={`status-pill ${info?.gateway.connected ? "ok" : "warn"}`}>
              <span className="dot" />
              {info?.gateway.connected ? "Clé EnOcean connectée" : "Clé EnOcean absente"}
            </span>
            {info?.gateway.base_id && <span className="status-pill">Base ID {info.gateway.base_id}</span>}
          </div>
        </header>

        {message && (
          <div className="alert" role="alert">
            <span>{message}</span>
            <button
              type="button"
              className="link"
              onClick={() => {
                setLocalError(null);
                clearError();
              }}
            >
              Fermer
            </button>
          </div>
        )}

        {page === "products" ? (
          <>
            <div className="toolbar">
              <label className="inline">
                Pièce
                <select value={room} onChange={(e) => setRoom(e.target.value)}>
                  {rooms.map((r) => (
                    <option key={r}>{r}</option>
                  ))}
                </select>
              </label>
              <button type="button" className="primary" onClick={() => setPage("add")}>
                + Ajouter un produit
              </button>
            </div>
            {devices.length === 0 ? (
              <div className="card empty">
                <h2>Aucun produit pour l'instant</h2>
                <p>Ajoutez votre premier produit EnOcean depuis la bibliothèque.</p>
                <button type="button" className="primary" onClick={() => setPage("add")}>
                  Ajouter un produit
                </button>
              </div>
            ) : (
              <div className="grid">
                {shown.map((d) => (
                  <DeviceCard
                    key={d.id}
                    device={d}
                    state={states[d.topic] ?? d.state}
                    available={availability[d.topic] ?? d.available}
                    action={actions[d.topic]}
                    onError={onError}
                  />
                ))}
              </div>
            )}
          </>
        ) : (
          <AddProduct onDone={() => setPage("products")} onError={onError} />
        )}
      </main>
    </div>
  );
}

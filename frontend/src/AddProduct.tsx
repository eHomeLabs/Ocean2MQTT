// Ajouter un produit : bibliothèque filtrée, fiche, appairage, nommage
import { useEffect, useMemo, useState } from "react";
import { clearPairing, request, useNow, useStore } from "./api";
import { TEACH_IN, TYPES, label } from "./labels";
import type { Device, Product } from "./types";

type Props = { onDone: () => void; onError: (m: string) => void };

export function AddProduct({ onDone, onError }: Props) {
  const [library, setLibrary] = useState<Product[]>([]);
  const [search, setSearch] = useState("");
  const [brand, setBrand] = useState("Toutes");
  const [type, setType] = useState("Tous");
  const [selected, setSelected] = useState<string | null>(null);
  const { pairing, connected } = useStore();

  useEffect(() => {
    if (connected) request<Product[]>("library").then(setLibrary).catch((e: Error) => onError(e.message));
  }, [connected, onError]);

  const brands = useMemo(() => ["Toutes", ...Array.from(new Set(library.map((p) => p.brand)))], [library]);
  const types = useMemo(() => ["Tous", ...Array.from(new Set(library.map((p) => p.type)))], [library]);
  const words = search.toLowerCase().split(/\s+/).filter(Boolean);
  const items = library.filter(
    (p) =>
      (brand === "Toutes" || p.brand === brand) &&
      (type === "Tous" || p.type === type) &&
      words.every((w) => [p.model, p.name, p.brand, p.eep, ...p.extra_eeps, ...p.variants].join(" ").toLowerCase().includes(w)),
  );
  const product = library.find((p) => p.id === selected) ?? null;
  const active = pairing && (pairing.status === "started" || pairing.status === "success" || pairing.status === "timeout");

  return (
    <div className="split">
      <section className="library" aria-label="Bibliothèque de produits">
        <div className="card filters">
          <label className="field">
            Rechercher
            <input type="search" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Référence, nom ou EEP (ex. SIN-2, fil pilote, D2-01-0C)" />
          </label>
          <Chips label="Marque" values={brands} value={brand} onChange={setBrand} />
          <Chips label="Type" values={types} value={type} onChange={setType} format={(t) => TYPES[t] ?? t} />
        </div>
        <div className="legend small muted">
          <span>{items.length} produit{items.length > 1 ? "s" : ""}</span>
          <span>
            <span className="badge valide">Validé</span> testé sur produit réel · <span className="badge communaute">Communauté</span> pas encore testé
          </span>
        </div>
        <div className="tiles">
          {items.map((p) => (
            <button key={p.id} type="button" className={`tile ${p.id === selected ? "selected" : ""}`} aria-pressed={p.id === selected} onClick={() => setSelected(p.id)}>
              {p.image ? <img src={p.image} alt="" /> : <div className="tile-placeholder" aria-hidden="true" />}
              <span className="brand">{p.brand.toUpperCase()}</span>
              <span className="model">{p.model}</span>
              <span className="name">{p.name}</span>
              <span className="tile-foot">
                <code>{p.eep}</code>
                <span className={`badge ${p.support}`}>{p.support === "valide" ? "Validé" : "Communauté"}</span>
              </span>
            </button>
          ))}
        </div>
      </section>

      <aside className="card sheet" aria-label="Fiche produit">
        {active ? (
          <Pairing library={library} onDone={onDone} onError={onError} />
        ) : product ? (
          <Sheet product={product} onError={onError} />
        ) : (
          <p className="muted">Choisissez un produit dans la bibliothèque pour afficher sa procédure d'appairage.</p>
        )}
      </aside>
    </div>
  );
}

function Chips({ label: title, values, value, onChange, format = (v) => v }: { label: string; values: string[]; value: string; onChange: (v: string) => void; format?: (v: string) => string }) {
  return (
    <div className="chips" role="group" aria-label={title}>
      <span className="small strong chips-label">{title}</span>
      {values.map((v) => (
        <button key={v} type="button" aria-pressed={v === value} className={`chip ${v === value ? "active" : ""}`} onClick={() => onChange(v)}>
          {format(v)}
        </button>
      ))}
    </div>
  );
}

function Sheet({ product, onError }: { product: Product; onError: (m: string) => void }) {
  const features = product.exposes.filter((e) => e.key !== "rssi");
  const start = () => request("pairing/start", { product: product.id, timeout: 60 }).catch((e: Error) => onError(e.message));
  return (
    <div className="sheet-body">
      <div className="sheet-head">
        {product.image ? <img src={product.image} alt={`${product.brand} ${product.model}`} className="photo" /> : <div className="photo placeholder">Photo à fournir</div>}
        <div>
          <span className="brand">{product.brand.toUpperCase()}</span>
          <h2>{product.name}</h2>
          <strong>{product.model}</strong>
          <span className={`badge ${product.support}`}>{product.support === "valide" ? "Validé" : "Communauté"}</span>
        </div>
      </div>
      <dl className="facts">
        <div>
          <dt>Profil EEP</dt>
          <dd>
            <code>{[product.eep, ...product.extra_eeps].join(" + ")}</code>
          </dd>
        </div>
        <div>
          <dt>Appairage</dt>
          <dd>{TEACH_IN[product.teach_in] ?? product.teach_in}</dd>
        </div>
      </dl>
      <h3>Ce que vous obtiendrez</h3>
      <div className="pills">
        {features.map((e) => (
          <span key={e.key} className="pill">
            {label(e.key)}
          </span>
        ))}
      </div>
      <h3>Procédure d'appairage</h3>
      <ol className="steps">
        <li>Cliquez sur « Lancer l'appairage » : Ocean2MQTT écoute pendant 60 s.</li>
        {product.steps.map((s) => (
          <li key={s}>{s}</li>
        ))}
      </ol>
      {product.support === "communaute" && (
        <p className="hint">Fiche pas encore testée sur produit réel : si l'appairage échoue, signalez-le sur GitHub.</p>
      )}
      <div className="sheet-actions">
        <button type="button" className="primary big" onClick={start}>
          Lancer l'appairage (60 s)
        </button>
        {product.manual && (
          <a href={product.manual} target="_blank" rel="noreferrer">
            Notice du produit
          </a>
        )}
      </div>
    </div>
  );
}

function Pairing({ library, onDone, onError }: { library: Product[]; onDone: () => void; onError: (m: string) => void }) {
  const { pairing } = useStore();
  const now = useNow(500);
  const product = library.find((p) => p.id === pairing?.product);
  if (!pairing) return null;
  if (pairing.status === "success") return <Name device={pairing as unknown as Device} onDone={onDone} onError={onError} />;
  if (pairing.status === "timeout") {
    return (
      <div className="pairing">
        <h2>Aucun produit détecté</h2>
        <p>Vérifiez la procédure (alimentation, nombre d'appuis) et que le produit est à portée de la clé, puis réessayez.</p>
        <div className="sheet-actions">
          <button type="button" className="primary" onClick={() => request("pairing/start", { product: pairing.product, timeout: 60 }).catch((e: Error) => onError(e.message))}>
            Réessayer
          </button>
          <button type="button" className="secondary" onClick={clearPairing}>
            Retour à la bibliothèque
          </button>
        </div>
      </div>
    );
  }
  const left = Math.max(0, Math.round(((pairing.until ?? 0) * 1000 - now) / 1000));
  const ratio = pairing.timeout ? left / pairing.timeout : 0;
  return (
    <div className="pairing">
      <div className="countdown" style={{ ["--ratio" as string]: ratio }}>
        <span>{left}</span>
        <small>s</small>
      </div>
      <h2>En écoute…</h2>
      <p>{product ? `Faites maintenant la manipulation du ${product.model} :` : "Faites maintenant la manipulation du produit."}</p>
      {product && (
        <ol className="steps">
          {product.steps.map((s) => (
            <li key={s}>{s}</li>
          ))}
        </ol>
      )}
      <button type="button" className="secondary" onClick={() => request("pairing/stop").then(clearPairing)}>
        Annuler
      </button>
    </div>
  );
}

function Name({ device, onDone, onError }: { device: Device; onDone: () => void; onError: (m: string) => void }) {
  const [name, setName] = useState(device.name);
  const [room, setRoom] = useState(device.room ?? "");
  const slug = name
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_|_$/g, "");
  const save = async () => {
    try {
      await request("device/rename", { id: device.id, name, room });
      clearPairing();
      onDone();
    } catch (e) {
      onError((e as Error).message);
    }
  };
  return (
    <div className="pairing">
      <div className="success-head">
        {device.product?.image && <img src={device.product.image} alt="" className="photo small-photo" />}
        <div>
          <h2>Produit appairé</h2>
          <span className="muted">
            {device.product?.brand} · {device.product?.name} · {device.id}
          </span>
        </div>
      </div>
      {device.product?.after && <p className="hint">{device.product.after}</p>}
      <label className="field">
        Nom du produit
        <input value={name} onChange={(e) => setName(e.target.value)} autoFocus />
      </label>
      <label className="field">
        Pièce (facultatif)
        <input value={room} onChange={(e) => setRoom(e.target.value)} placeholder="Salon, Chambre…" />
      </label>
      <div className="field">
        <span className="small strong">Topic MQTT</span>
        <code className="topic">ocean2mqtt/{slug || device.id}</code>
      </div>
      <div className="sheet-actions">
        <button type="button" className="primary big" onClick={save}>
          Terminer
        </button>
      </div>
    </div>
  );
}

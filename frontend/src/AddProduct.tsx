// Ajouter un produit : bibliothèque filtrée, mode générique, suggestions, appairage, nommage
import { useEffect, useMemo, useState } from "react";
import { clearPairing, clearSuggestion, request, useNow, useStore } from "./api";
import { label, locale, productText, supportName, t, teachIn, typeName } from "./i18n";
import { CodeChoice, codeChoiceValid, type CodeMode } from "./Recom";
import type { Device, Product, Unknown } from "./types";

type Props = { onDone: () => void; onError: (m: string) => void; preset?: string | null };
const GENERIC = "__generic__";
const CATALOG = "https://ehomelabs.github.io/Ocean2MQTT/";

// Formulaire GitHub « Proposer un nouveau produit EnOcean » (champs préremplis si connus)
function proposeUrl(eep?: string | null, manufacturer?: number | null): string {
  const params = new URLSearchParams({ template: "nouveau-produit.yml" });
  if (eep) params.set("eep", eep);
  if (manufacturer != null) params.set("fabricant_id", `0x${manufacturer.toString(16).toUpperCase().padStart(3, "0")}`);
  return `https://github.com/eHomeLabs/Ocean2MQTT/issues/new?${params}`;
}

export function AddProduct({ onDone, onError, preset }: Props) {
  const [library, setLibrary] = useState<Product[]>([]);
  const [generics, setGenerics] = useState<Product[]>([]);
  const [search, setSearch] = useState("");
  const [brand, setBrand] = useState("");
  const [type, setType] = useState("");
  const [selected, setSelected] = useState<string | null>(preset ?? null);
  const [added, setAdded] = useState<Device | null>(null);
  const [dismissed, setDismissed] = useState<string[]>([]);
  const { pairing, connected, suggestion, unknown } = useStore();

  useEffect(() => {
    if (!connected) return;
    request<Product[]>("library").then(setLibrary).catch((e: Error) => onError(e.message));
    request<Product[]>("library/generic").then(setGenerics).catch(() => {});
  }, [connected, onError]);

  const all = useMemo(() => [...library, ...generics], [library, generics]);
  const brands = useMemo(() => Array.from(new Set(library.map((p) => p.brand))), [library]);
  const types = useMemo(() => Array.from(new Set(library.map((p) => p.type))), [library]);
  const words = search.toLowerCase().split(/\s+/).filter(Boolean);
  const items = library.filter(
    (p) =>
      (!brand || p.brand === brand) &&
      (!type || p.type === type) &&
      words.every((w) => [p.model, productText(p).name, p.name, p.brand, p.eep, ...p.extra_eeps, ...p.variants].join(" ").toLowerCase().includes(w)),
  );
  const product = all.find((p) => p.id === selected) ?? null;
  // Bandeau : dernière demande d'appairage d'un émetteur inconnu qui ressemble à un produit
  const banner =
    (suggestion && !dismissed.includes(suggestion.id) && unknown.some((u) => u.id === suggestion.id) ? suggestion : null) ??
    [...unknown].filter((u) => u.teach_in && u.suggestions.length && !dismissed.includes(u.id)).sort((a, b) => b.last_seen.localeCompare(a.last_seen))[0] ??
    null;
  const active = pairing && (pairing.status === "started" || pairing.status === "success" || pairing.status === "timeout");

  const addKnown = async (id: string, productId: string, sender?: string) => {
    try {
      const device = await request<Device>("device/add", { id, product: productId, ...(sender ? { sender } : {}) });
      clearSuggestion();
      setAdded(device);
    } catch (e) {
      onError((e as Error).message);
    }
  };

  return (
    <div className="split">
      <section className="library" aria-label="Bibliothèque">
        {banner && !active && !added && (
          <Suggestion
            entry={banner}
            products={all}
            onPick={(id) => setSelected(id)}
            onAdd={addKnown}
            onClose={() => {
              setDismissed([...dismissed, banner.id]);
              clearSuggestion();
            }}
          />
        )}
        <div className="card filters">
          <label className="field">
            {t("add.search")}
            <input type="search" value={search} onChange={(e) => setSearch(e.target.value)} placeholder={t("add.searchHint")} />
          </label>
          <Chips title={t("add.brand")} values={brands} value={brand} onChange={setBrand} all={t("add.all")} />
          <Chips title={t("add.type")} values={types} value={type} onChange={setType} format={typeName} all={t("add.allTypes")} />
        </div>
        <div className="legend small muted">
          <span>
            {t("add.count", { n: items.length })} ·{" "}
            <a href={CATALOG} target="_blank" rel="noreferrer">
              {t("add.catalog")}
            </a>
          </span>
          <span>
            <span className="badge valide">{t("add.valid")}</span> {t("add.legend")} · <span className="badge communaute">{t("add.community")}</span> {t("add.legendCommunity")}
          </span>
        </div>
        <div className="tiles">
          {items.map((p) => (
            <button key={p.id} type="button" className={`tile ${p.id === selected ? "selected" : ""}`} aria-pressed={p.id === selected} onClick={() => setSelected(p.id)}>
              {p.image ? <img src={p.image} alt="" /> : <div className="tile-placeholder" aria-hidden="true" />}
              <span className="brand">{p.brand.toUpperCase()}</span>
              <span className="model">{p.model}</span>
              <span className="name">{productText(p).name}</span>
              <span className="tile-foot">
                <code>{p.eep}</code>
                <span className={`badge ${p.support}`}>{supportName(p.support)}</span>
              </span>
            </button>
          ))}
          <button type="button" className={`tile generic ${selected === GENERIC || product?.generic ? "selected" : ""}`} onClick={() => setSelected(GENERIC)}>
            <div className="tile-placeholder generic-icon" aria-hidden="true">
              EEP
            </div>
            <span className="brand">{t("add.generic").toUpperCase()}</span>
            <span className="model">{t("add.genericTitle")}</span>
            <span className="name">{t("add.genericTile")}</span>
            <span className="tile-foot">
              <span className="badge generique">{t("add.generic")}</span>
            </span>
          </button>
          <a className="tile propose" href={proposeUrl()} target="_blank" rel="noreferrer">
            <div className="tile-placeholder propose-icon" aria-hidden="true">
              +
            </div>
            <span className="brand">{t("add.proposeBrand").toUpperCase()}</span>
            <span className="model">{t("add.propose")}</span>
            <span className="name">{t("add.proposeTile")}</span>
          </a>
        </div>
        {unknown.length > 0 && <UnknownList unknown={unknown} products={all} onAdd={addKnown} onPick={(id) => setSelected(id)} />}
      </section>

      <aside className="card sheet" aria-label={t("add.procedure")}>
        {added ? (
          <Name
            device={added}
            onDone={() => {
              setAdded(null);
              onDone();
            }}
            onError={onError}
          />
        ) : active ? (
          <Pairing library={all} onDone={onDone} onError={onError} />
        ) : selected === GENERIC ? (
          <GenericPicker generics={generics} onPick={setSelected} />
        ) : product ? (
          <Sheet product={product} onError={onError} onAddById={(id, sender) => addKnown(id, product.id, sender)} onBack={product.generic ? () => setSelected(GENERIC) : undefined} />
        ) : (
          <p className="muted">{t("add.choose")}</p>
        )}
      </aside>
    </div>
  );
}

function Chips({ title, values, value, onChange, format = (v) => v, all }: { title: string; values: string[]; value: string; onChange: (v: string) => void; format?: (v: string) => string; all: string }) {
  return (
    <div className="chips" role="group" aria-label={title}>
      <span className="small strong chips-label">{title}</span>
      {["", ...values].map((v) => (
        <button key={v || "all"} type="button" aria-pressed={v === value} className={`chip ${v === value ? "active" : ""}`} onClick={() => onChange(v)}>
          {v ? format(v) : all}
        </button>
      ))}
    </div>
  );
}

function Suggestion({ entry, products, onPick, onAdd, onClose }: { entry: Unknown; products: Product[]; onPick: (id: string) => void; onAdd: (id: string, product: string) => void; onClose: () => void }) {
  const matches = entry.suggestions.map((id) => products.find((p) => p.id === id)).filter(Boolean) as Product[];
  if (!matches.length) return null;
  return (
    <div className="card suggestion" role="status">
      <div className="row-title">
        <div>
          <h3>{t("add.suggestTitle")}</h3>
          <p className="small muted">{t("add.suggestText", { id: entry.id, eep: entry.eep ?? "?" })}</p>
        </div>
        <button type="button" className="link" onClick={onClose}>
          {t("close")}
        </button>
      </div>
      <div className="suggest-list">
        {matches.map((p) => (
          <div key={p.id} className="suggest-item">
            {p.image ? <img src={p.image} alt="" className="thumb" /> : <div className="thumb placeholder" aria-hidden="true" />}
            <div className="device-title">
              <strong>
                {p.brand} {p.model}
              </strong>
              <span className="small muted">{productText(p).name}</span>
            </div>
            {p.teach_in.endsWith("bidir") ? (
              <button type="button" className="secondary" onClick={() => onPick(p.id)}>
                {t("add.procedure")}
              </button>
            ) : (
              <button type="button" className="primary" onClick={() => onAdd(entry.id, p.id)}>
                {t("add.pairOneClick")}
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

function UnknownList({ unknown, products, onAdd, onPick }: { unknown: Unknown[]; products: Product[]; onAdd: (id: string, product: string) => void; onPick: (id: string) => void }) {
  const [open, setOpen] = useState<string | null>(null);
  const sensors = products.filter((p) => !p.teach_in.endsWith("bidir"));
  return (
    <section className="card stack">
      <div className="row-title">
        <div>
          <h3>{t("add.unknownTitle")}</h3>
          <p className="small muted">{t("add.unknownHint")}</p>
        </div>
        <button type="button" className="link" onClick={() => request("unknown/clear")}>
          {t("add.unknownClear")}
        </button>
      </div>
      <table className="table">
        <tbody>
          {[...unknown]
            .sort((a, b) => b.last_seen.localeCompare(a.last_seen))
            .map((u) => {
              const suggested = u.suggestions.map((id) => products.find((p) => p.id === id)).filter(Boolean) as Product[];
              const candidates = suggested.length ? suggested : sensors.filter((p) => p.eep.slice(0, 2) === u.rorg);
              return (
                <tr key={u.id}>
                  <td>
                    <code>{u.id}</code>
                  </td>
                  <td className="small">
                    <code>{u.eep ?? u.rorg}</code>
                    {u.teach_in && <span className="badge valide"> {t("add.teachIn")}</span>}
                  </td>
                  <td className="small muted">
                    {t("add.seen", { n: u.count })} · {new Date(u.last_seen).toLocaleTimeString(locale())}
                    {u.rssi != null && ` · ${-Math.abs(u.rssi)} dBm`}
                  </td>
                  <td className="right">
                    {!candidates.length && (
                      <a className="link small propose-link" href={proposeUrl(u.eep, u.manufacturer)} target="_blank" rel="noreferrer">
                        {t("add.proposeShort")}
                      </a>
                    )}
                    {open === u.id ? (
                      <select
                        autoFocus
                        aria-label={t("add.pairWith")}
                        defaultValue=""
                        onChange={(e) => {
                          const p = products.find((x) => x.id === e.target.value);
                          if (!p) return;
                          if (p.teach_in.endsWith("bidir")) onPick(p.id);
                          else onAdd(u.id, p.id);
                          setOpen(null);
                        }}
                        onBlur={() => setOpen(null)}
                      >
                        <option value="">{t("add.pairWith")}</option>
                        {candidates.map((p) => (
                          <option key={p.id} value={p.id}>
                            {p.brand} {p.model} — {productText(p).name}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <button type="button" className="secondary" disabled={!candidates.length} onClick={() => setOpen(u.id)}>
                        {t("add.pairWith")}
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
        </tbody>
      </table>
    </section>
  );
}

function GenericPicker({ generics, onPick }: { generics: Product[]; onPick: (id: string) => void }) {
  return (
    <div className="sheet-body">
      <h2>{t("add.genericTitle")}</h2>
      <p className="muted">{t("add.genericIntro")}</p>
      <div className="generic-list">
        {generics.map((p) => (
          <button key={p.id} type="button" className="generic-item" onClick={() => onPick(p.id)}>
            <code>{p.eep.startsWith("D2-01") ? "D2-01-xx" : p.eep}</code>
            <span>{productText(p).name}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

function Sheet({ product, onError, onBack, onAddById }: { product: Product; onError: (m: string) => void; onBack?: () => void; onAddById: (id: string, sender?: string) => void }) {
  const features = product.exposes.filter((e) => e.key !== "rssi");
  const actuator = product.teach_in.endsWith("bidir");
  const { info } = useStore();
  const remote = actuator && product.recom && info?.recom_enabled !== false;
  const [remoteCode, setRemoteCode] = useState("");
  const [sender, setSender] = useState("");
  const cleanSender = sender.trim().toUpperCase().replace(/^0X/, "").replace(/[\s:-]/g, "");
  const base = info?.gateway.base_id ?? null;
  const senderOk = /^[0-9A-F]{8}$/.test(cleanSender) && (!base || (parseInt(cleanSender, 16) - parseInt(base, 16) >= 0 && parseInt(cleanSender, 16) - parseInt(base, 16) < 128));
  const [manualId, setManualId] = useState("");
  const cleanId = manualId.trim().toUpperCase().replace(/^0X/, "").replace(/[\s:-]/g, "");
  const start = () => request("pairing/start", { product: product.id, timeout: 60 }).catch((e: Error) => onError(e.message));
  return (
    <div className="sheet-body">
      {onBack && (
        <button type="button" className="link back" onClick={onBack}>
          ← {t("add.genericTitle")}
        </button>
      )}
      <div className="sheet-head">
        {product.image ? (
          <img src={product.image} alt={`${product.brand} ${product.model}`} className="photo" />
        ) : (
          <div className="photo placeholder">{product.generic ? "EEP" : t("add.photoMissing")}</div>
        )}
        <div>
          <span className="brand">{product.brand.toUpperCase()}</span>
          <h2>{productText(product).name}</h2>
          <strong>{product.model}</strong>
          <span className={`badge ${product.support}`}>{supportName(product.support)}</span>
        </div>
      </div>
      <dl className="facts">
        <div>
          <dt>{t("add.profile")}</dt>
          <dd>
            <code>{[product.eep, ...product.extra_eeps].join(" + ")}</code>
          </dd>
        </div>
        <div>
          <dt>{t("add.pairing")}</dt>
          <dd>{teachIn(product.teach_in)}</dd>
        </div>
      </dl>
      <h3>{t("add.features")}</h3>
      <div className="pills">
        {features.map((e) => (
          <span key={e.key} className="pill">
            {label(e.key)}
          </span>
        ))}
      </div>
      <h3>{t("add.procedure")}</h3>
      <ol className="steps">
        <li>{t("add.step0")}</li>
        {productText(product).steps.map((s) => (
          <li key={s}>{s}</li>
        ))}
      </ol>
      {product.support === "communaute" && <p className="hint">{t("add.communityHint")}</p>}
      {product.generic && <p className="hint">{t("add.genericHint")}</p>}
      <div className="sheet-actions">
        <button type="button" className="primary big" onClick={start}>
          {t("add.start")}
        </button>
        {product.manual && (
          <a href={product.manual} target="_blank" rel="noreferrer">
            {t("detail.manual")}
          </a>
        )}
      </div>
      <details className="manual-id">
        <summary>{t("add.byIdTitle")}</summary>
        {remote ? (
          <form
            className="stack"
            onSubmit={(e) => {
              e.preventDefault();
              request("pairing/remote", { product: product.id, id: cleanId, code: remoteCode.trim() }).catch((err: Error) => onError(err.message));
            }}
          >
            <p className="small">{t("add.remoteIntro")}</p>
            <ol className="steps small">
              <li>{t("add.remoteStep1")}</li>
              <li>{t("add.remoteStep2")}</li>
              <li>{t("add.remoteStep3")}</li>
            </ol>
            <label className="field">
              {t("add.byIdLabel")}
              <input value={manualId} onChange={(e) => setManualId(e.target.value)} placeholder="0512ABCD" spellCheck={false} autoComplete="off" />
            </label>
            <label className="field">
              {t("add.remoteCode")}
              <input value={remoteCode} onChange={(e) => setRemoteCode(e.target.value)} placeholder={t("recom.codeHint")} spellCheck={false} autoComplete="off" />
            </label>
            <button type="submit" className="secondary" disabled={!/^[0-9A-F]{8}$/.test(cleanId)}>
              {t("add.remoteStart")}
            </button>
            <p className="small muted">{t("add.remoteNote")}</p>
          </form>
        ) : null}
        {actuator ? (
          <form
            className="stack"
            onSubmit={(e) => {
              e.preventDefault();
              onAddById(cleanId, cleanSender);
            }}
          >
            <h4>{t("add.senderTitle")}</h4>
            <p className="small muted">{t("add.senderHint", { from: base ?? "?", to: base ? (parseInt(base, 16) + 127).toString(16).toUpperCase().padStart(8, "0") : "?" })}</p>
            {!remote && (
              <label className="field">
                {t("add.byIdLabel")}
                <input value={manualId} onChange={(e) => setManualId(e.target.value)} placeholder="0512ABCD" spellCheck={false} autoComplete="off" />
              </label>
            )}
            <label className="field">
              {t("add.senderLabel")}
              <input value={sender} onChange={(e) => setSender(e.target.value)} placeholder={base ?? "FFE56B80"} spellCheck={false} autoComplete="off" />
            </label>
            {cleanSender.length === 8 && !senderOk && <p className="small error-text">{t("add.senderOut")}</p>}
            <button type="submit" className="secondary" disabled={!/^[0-9A-F]{8}$/.test(cleanId) || !senderOk}>
              {t("add.senderAdd")}
            </button>
          </form>
        ) : (
          <form
            className="stack"
            onSubmit={(e) => {
              e.preventDefault();
              onAddById(cleanId);
            }}
          >
            <p className="small muted">{t("add.byIdHint")}</p>
            <div className="number-form">
              <label className="field grow">
                {t("add.byIdLabel")}
                <input value={manualId} onChange={(e) => setManualId(e.target.value)} placeholder="0512ABCD" spellCheck={false} autoComplete="off" />
              </label>
              <button type="submit" className="secondary" disabled={!/^[0-9A-F]{8}$/.test(cleanId)}>
                {t("add.byIdAdd")}
              </button>
            </div>
          </form>
        )}
      </details>
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
        <h2>{t("add.timeoutTitle")}</h2>
        <p>{t("add.timeoutText")}</p>
        <div className="sheet-actions">
          <button type="button" className="primary" onClick={() => request("pairing/start", { product: pairing.product, timeout: 60 }).catch((e: Error) => onError(e.message))}>
            {t("retry")}
          </button>
          <button type="button" className="secondary" onClick={clearPairing}>
            {t("add.back")}
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
      <h2>{t("add.listening")}</h2>
      <p>{product ? t("add.doNow", { model: product.model }) : t("add.doNowGeneric")}</p>
      {product && (
        <ol className="steps">
          {productText(product).steps.map((s) => (
            <li key={s}>{s}</li>
          ))}
        </ol>
      )}
      <button type="button" className="secondary" onClick={() => request("pairing/stop").then(clearPairing)}>
        {t("cancel")}
      </button>
    </div>
  );
}

function Name({ device, onDone, onError }: { device: Device; onDone: () => void; onError: (m: string) => void }) {
  const [name, setName] = useState(device.name);
  const [room, setRoom] = useState(device.room ?? "");
  const askCode = !!device.recom && !device.recom.has_code;
  const [mode, setMode] = useState<CodeMode>("auto");
  const [code, setCode] = useState("");
  const [saving, setSaving] = useState(false);
  const slug = name
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_|_$/g, "");
  const save = async () => {
    setSaving(true);
    try {
      await request("device/rename", { id: device.id, name, room });
      if (askCode) {
        // Dans la foulée de l'appairage : le produit est encore dans sa fenêtre de mise sous tension
        try {
          await request("device/recom/assign", { id: device.id, mode, code });
        } catch (e) {
          onError(`${(e as Error).message} — ${t("recom.assignLater")}`);
        }
      }
      clearPairing();
      onDone();
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setSaving(false);
    }
  };
  return (
    <div className="pairing">
      <div className="success-head">
        {device.product?.image && <img src={device.product.image} alt="" className="photo small-photo" />}
        <div>
          <h2>{t("add.paired")}</h2>
          <span className="muted">
            {device.product?.brand} · {device.product ? productText(device.product).name : ""} · {device.id}
          </span>
        </div>
      </div>
      {device.product && productText(device.product).after && <p className="hint">{productText(device.product).after}</p>}
      <label className="field">
        {t("add.productName")}
        <input value={name} onChange={(e) => setName(e.target.value)} autoFocus />
      </label>
      <label className="field">
        {t("detail.roomOpt")}
        <input value={room} onChange={(e) => setRoom(e.target.value)} placeholder={t("add.roomHint")} />
      </label>
      <div className="field">
        <span className="small strong">{t("detail.topic")}</span>
        <code className="topic">ocean2mqtt/{slug || device.id}</code>
      </div>
      {askCode && (
        <section className="field">
          <span className="small strong">{t("recom.choiceTitle")}</span>
          <CodeChoice mode={mode} code={code} onChange={(m, c) => { setMode(m); setCode(c); }} />
          {mode !== "none" && <span className="small muted">{t("recom.warning")}</span>}
        </section>
      )}
      <div className="sheet-actions">
        <button type="button" className="primary big" onClick={save} disabled={saving || (askCode && !codeChoiceValid(mode, code))}>
          {saving ? t("loading") : t("add.finish")}
        </button>
      </div>
    </div>
  );
}

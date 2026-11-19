import { useCallback, useState } from "react";
import { AddProduct } from "./AddProduct";
import { clearError, refresh, request, useStore } from "./api";
import { DeviceCard } from "./DeviceCard";
import { DeviceDetail } from "./DeviceDetail";
import { getLang, setLang, t, type Key, type Lang } from "./i18n";
import { BaseIdSection, MqttSection } from "./Gateway";
import { LogoMark, Wordmark } from "./Logo";
import { MigrationBanner, MigrationSettings, MigrationWizard, RepairBanner, type MigrationTarget } from "./Migration";
import { RecomPage } from "./Recom";
import { TelegramsPage } from "./Telegrams";

type Page = "products" | "add" | "recom" | "telegrams" | "settings";
type Open = { id: string; tab?: "control" | "recom" };

const PAGES: [Page, Key][] = [
  ["products", "nav.products"],
  ["add", "nav.add"],
  ["recom", "nav.recom"],
  ["telegrams", "nav.telegrams"],
  ["settings", "nav.settings"],
];

export function App() {
  const [page, setPage] = useState<Page>("products");
  const [room, setRoom] = useState("");
  const [open, setOpen] = useState<Open | null>(null);
  const [migration, setMigration] = useState<MigrationTarget | null>(null);
  const [preset, setPreset] = useState<string | null>(null);
  const store = useStore();
  const { info, devices, states, availability, actions, connected, error } = store;
  const [localError, setLocalError] = useState<string | null>(null);
  const onError = useCallback((m: string) => setLocalError(m), []);
  const message = localError ?? error;
  const rooms = Array.from(new Set(devices.map((d) => d.room).filter(Boolean) as string[]));
  const shown = devices.filter((d) => !room || d.room === room);
  const availableCount = devices.filter((d) => availability[d.topic] ?? d.available).length;
  const openDevice = devices.find((d) => d.id === open?.id);
  const subtitle: Record<Page, string> = {
    products: t("products.count", { n: devices.length, a: availableCount }),
    add: t("add.subtitle"),
    recom: "",
    telegrams: "",
    settings: "",
  };

  return (
    <div className="layout">
      <nav className="sidebar" aria-label="Menu">
        <div className="brand-line">
          <LogoMark />
          <Wordmark />
        </div>
        {PAGES.filter(([key]) => key !== "recom" || info?.recom_enabled !== false).map(([key, text]) => (
          <button key={key} type="button" className={`nav ${page === key ? "current" : ""}`} aria-current={page === key ? "page" : undefined} onClick={() => { setPreset(null); setPage(key); }}>
            {t(text)}
          </button>
        ))}
        <div className="sidebar-foot">
          <strong>eHomeLabs · open source</strong>
          <span>{t("foot.version", { v: info?.version ?? "…" })}</span>
        </div>
      </nav>

      <main className="main">
        <header className="topbar">
          <div>
            <h1>{t(PAGES.find(([k]) => k === page)![1])}</h1>
            {subtitle[page] && <p className="muted">{subtitle[page]}</p>}
          </div>
          <div className="pills-status">
            <span className={`status-pill ${connected ? "ok" : "warn"}`}>
              <span className="dot" />
              {connected ? t("status.service") : t("status.connecting")}
            </span>
            <span className={`status-pill ${info?.gateway.connected ? "ok" : "warn"}`}>
              <span className="dot" />
              {info?.gateway.connected ? t("status.stick") : t("status.noStick")}
            </span>
            {info?.gateway.base_id && <span className="status-pill">Base ID {info.gateway.base_id}</span>}
          </div>
        </header>

        {connected && info && !info.gateway.connected && info.migration?.nodocean.some((s) => s.active) && (
          <div className="alert" role="alert">
            <span>{t("status.noStickNodocean")}</span>
          </div>
        )}

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
              {t("close")}
            </button>
          </div>
        )}

        {page === "products" && (
          <>
            <MigrationBanner onStart={setMigration} />
            <RepairBanner onError={onError} />
            <div className="toolbar">
              <label className="inline">
                {t("products.room")}
                <select value={room} onChange={(e) => setRoom(e.target.value)}>
                  <option value="">{t("products.allRooms")}</option>
                  {rooms.map((r) => (
                    <option key={r}>{r}</option>
                  ))}
                </select>
              </label>
              <button type="button" className="primary" onClick={() => setPage("add")}>
                {t("products.add")}
              </button>
            </div>
            {devices.length === 0 ? (
              <div className="card empty">
                <h2>{t("products.empty")}</h2>
                <p>{t("products.emptyHint")}</p>
                <button type="button" className="primary" onClick={() => setPage("add")}>
                  {t("nav.add")}
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
                    onOpen={() => setOpen({ id: d.id })}
                    onRepair={() => {
                      setPreset(d.product.id);
                      setPage("add");
                    }}
                  />
                ))}
              </div>
            )}
          </>
        )}
        {page === "add" && (
          <AddProduct
            key={preset ?? "add"}
            preset={preset}
            onDone={() => {
              setPreset(null);
              setPage("products");
            }}
            onError={onError}
          />
        )}
        {page === "recom" && <RecomPage onOpen={(d) => setOpen({ id: d.id, tab: "recom" })} />}
        {page === "telegrams" && <TelegramsPage />}
        {page === "settings" && <AppSettings onStart={setMigration} onError={onError} />}
      </main>

      {migration && <MigrationWizard target={migration} onClose={() => setMigration(null)} onError={onError} />}
      {openDevice && <DeviceDetail key={openDevice.id} device={openDevice} initialTab={open?.tab} onClose={() => setOpen(null)} onError={onError} />}
    </div>
  );
}

type SettingsTab = "language" | "gateway" | "mqtt" | "recom" | "migration" | "about";
const SETTINGS_TABS: SettingsTab[] = ["language", "gateway", "mqtt", "recom", "migration", "about"];

function AppSettings({ onStart, onError }: { onStart: (t: MigrationTarget) => void; onError: (m: string) => void }) {
  const { info } = useStore();
  const gw = info?.gateway;
  const [tab, setTab] = useState<SettingsTab>(() => {
    try {
      const saved = sessionStorage.getItem("o2m-settings-tab") as SettingsTab | null;
      return saved && SETTINGS_TABS.includes(saved) ? saved : "language";
    } catch {
      return "language";
    }
  });
  const open = (key: SettingsTab) => {
    setTab(key);
    try {
      sessionStorage.setItem("o2m-settings-tab", key);
    } catch {
      /* stockage indisponible : sans importance */
    }
  };
  return (
    <div className="stack narrow settings-page">
      <div className="tabs settings-tabs" role="tablist" aria-label={t("nav.settings")}>
        {SETTINGS_TABS.map((key) => (
          <button key={key} type="button" role="tab" aria-selected={tab === key} className={tab === key ? "active" : ""} onClick={() => open(key)}>
            {t(`set.tab.${key}` as Key)}
          </button>
        ))}
      </div>
      {tab === "language" && (
        <section className="card stack">
          <h3>{t("app.language")}</h3>
          <div className="segmented two" role="group" aria-label={t("app.language")}>
            {(["fr", "en"] as Lang[]).map((l) => (
              <button
                key={l}
                type="button"
                aria-pressed={getLang() === l}
                className={getLang() === l ? "active" : ""}
                onClick={() => {
                  setLang(l);
                  refresh();
                }}
              >
                {l === "fr" ? "Français" : "English"}
              </button>
            ))}
          </div>
        </section>
      )}
      {tab === "gateway" && (
        <section className="card stack">
          <h3>{t("app.gateway")}</h3>
          <dl className="facts">
            <div>
              <dt>{t("app.port")}</dt>
              <dd><code>{gw?.port ?? "—"}</code></dd>
            </div>
            <div>
              <dt>{t("app.baseId")}</dt>
              <dd><code>{gw?.base_id ?? "—"}</code></dd>
            </div>
            <div>
              <dt>{t("app.chipId")}</dt>
              <dd><code>{gw?.chip_id ?? "—"}</code></dd>
            </div>
            <div>
              <dt>{t("app.firmware")}</dt>
              <dd>{gw?.app_version ?? "—"}</dd>
            </div>
          </dl>
          <BaseIdSection onError={onError} />
        </section>
      )}
      {tab === "mqtt" && (
        <section className="card stack">
          <h3>{t("app.mqtt")}</h3>
          <MqttSection onError={onError} />
        </section>
      )}
      {tab === "recom" && <RecomSettings onError={onError} />}
      {tab === "migration" && <MigrationSettings onStart={onStart} onError={onError} />}
      {tab === "about" && (
        <section className="card stack">
          <h3>{t("app.about")}</h3>
          <dl className="facts">
            <div>
              <dt>{t("about.version")}</dt>
              <dd>{info?.version ?? "—"}</dd>
            </div>
            <div>
              <dt>{t("about.licence")}</dt>
              <dd>MIT · eHomeLabs</dd>
            </div>
          </dl>
          <p className="small">{t("app.aboutText")}</p>
          <ul className="links">
            <li><a href="https://github.com/eHomeLabs/Ocean2MQTT" target="_blank" rel="noreferrer">{t("about.code")}</a></li>
            <li><a href={t("about.wikiUrl")} target="_blank" rel="noreferrer">{t("about.wiki")}</a></li>
            <li><a href="https://ehomelabs.github.io/Ocean2MQTT/" target="_blank" rel="noreferrer">{t("add.catalog")}</a></li>
            <li><a href="https://github.com/eHomeLabs/Ocean2MQTT/issues/new?template=nouveau-produit.yml" target="_blank" rel="noreferrer">{t("add.propose")}</a></li>
            <li><a href="https://github.com/eHomeLabs/Ocean2MQTT/releases" target="_blank" rel="noreferrer">{t("about.releases")}</a></li>
            <li><a href="https://github.com/eHomeLabs/Ocean2MQTT/issues" target="_blank" rel="noreferrer">{t("about.issues")}</a></li>
          </ul>
          <p className="small muted">{t("about.independent")}</p>
        </section>
      )}
    </div>
  );
}

function RecomSettings({ onError }: { onError: (m: string) => void }) {
  const { info } = useStore();
  const enabled = info?.recom_enabled !== false;
  const [busy, setBusy] = useState(false);
  const set = async (value: boolean) => {
    if (value === enabled) return;
    setBusy(true);
    try {
      await request("config/recom/set", { enabled: value });
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  return (
    <section className="card stack">
      <h3>{t("app.recom")}</h3>
      <div className="segmented two" role="group" aria-label={t("app.recom")}>
        <button type="button" aria-pressed={enabled} className={enabled ? "active" : ""} disabled={busy} onClick={() => set(true)}>
          {t("set.recomOn")}
        </button>
        <button type="button" aria-pressed={!enabled} className={!enabled ? "active" : ""} disabled={busy} onClick={() => set(false)}>
          {t("set.recomOff")}
        </button>
      </div>
      <p className="small">{enabled ? t("app.recomOn") : t("set.recomOffText")}</p>
      <p className="small muted">{t("set.recomHint")}</p>
    </section>
  );
}

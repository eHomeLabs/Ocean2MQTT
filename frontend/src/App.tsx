import { useCallback, useState } from "react";
import { AddProduct } from "./AddProduct";
import { clearError, refresh, useStore } from "./api";
import { DeviceCard } from "./DeviceCard";
import { DeviceDetail } from "./DeviceDetail";
import { getLang, setLang, t, type Key, type Lang } from "./i18n";
import { LogoMark, Wordmark } from "./Logo";
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
        {PAGES.map(([key, text]) => (
          <button key={key} type="button" className={`nav ${page === key ? "current" : ""}`} aria-current={page === key ? "page" : undefined} onClick={() => setPage(key)}>
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
                  />
                ))}
              </div>
            )}
          </>
        )}
        {page === "add" && <AddProduct onDone={() => setPage("products")} onError={onError} />}
        {page === "recom" && <RecomPage onOpen={(d) => setOpen({ id: d.id, tab: "recom" })} />}
        {page === "telegrams" && <TelegramsPage />}
        {page === "settings" && <AppSettings />}
      </main>

      {openDevice && <DeviceDetail key={openDevice.id} device={openDevice} initialTab={open?.tab} onClose={() => setOpen(null)} onError={onError} />}
    </div>
  );
}

function AppSettings() {
  const { info } = useStore();
  const gw = info?.gateway;
  const mqtt = (info?.config.mqtt ?? {}) as Record<string, unknown>;
  const yes = (v: unknown) => (v ? t("app.yes") : t("app.no"));
  return (
    <div className="stack narrow">
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
      </section>
      <section className="card stack">
        <h3>{t("app.mqtt")}</h3>
        <dl className="facts">
          <div>
            <dt>{t("app.host")}</dt>
            <dd><code>{String(mqtt.host ?? "—")}:{String(mqtt.port ?? "")}</code></dd>
          </div>
          <div>
            <dt>{t("app.baseTopic")}</dt>
            <dd><code>{String(mqtt.base_topic ?? "ocean2mqtt")}</code></dd>
          </div>
          <div>
            <dt>{t("app.discovery")}</dt>
            <dd>{yes(mqtt.discovery)}</dd>
          </div>
        </dl>
        <p className="small muted">{t("app.configHint")}</p>
      </section>
      <section className="card stack">
        <h3>{t("app.about")}</h3>
        <p className="small">
          {t("app.aboutText")} <a href="https://github.com/eHomeLabs/Ocean2MQTT" target="_blank" rel="noreferrer">github.com/eHomeLabs/Ocean2MQTT</a>
        </p>
      </section>
    </div>
  );
}

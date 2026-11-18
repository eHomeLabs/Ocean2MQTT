// Journal radio en direct : filtres par émetteur et RORG, pause, export CSV
import { useState } from "react";
import { clearTelegrams, pauseTelegrams, useStore } from "./api";
import { locale, t } from "./i18n";
import type { Telegram } from "./types";

const RORGS: Record<string, string> = { F6: "RPS", D5: "1BS", A5: "4BS", D2: "VLD", D4: "UTE", D1: "MSC", C5: "SYS_EX" };

export function TelegramsPage() {
  const { telegrams, devices } = useStore();
  const [sender, setSender] = useState("");
  const [rorg, setRorg] = useState("");
  const [paused, setPaused] = useState(false);
  const names = new Map(devices.map((d) => [d.id, d.name]));
  const senders = Array.from(new Set(telegrams.map((x) => x.sender)));
  const rorgs = Array.from(new Set(telegrams.map((x) => x.rorg))).sort();
  const shown = telegrams.filter((x) => (!sender || x.sender === sender || x.destination === sender) && (!rorg || x.rorg === rorg));
  const exportCsv = () => {
    const head = "time;dir;sender;name;destination;rorg;data;status;dbm;duplicate";
    const rows = shown.map((x) =>
      [new Date(x.time * 1000).toISOString(), x.dir, x.sender, names.get(x.sender) ?? "", x.destination, x.rorg, x.data, x.status, x.dbm ?? "", x.duplicate ? 1 : 0].join(";"),
    );
    const blob = new Blob([[head, ...rows].join("\n")], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `ocean2mqtt-telegrammes-${new Date().toISOString().slice(0, 19).replaceAll(":", "-")}.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  };
  return (
    <div className="stack">
      <div className="toolbar">
        <p className="muted">{t("tg.intro")}</p>
        <div className="button-row">
          <button
            type="button"
            className="secondary"
            onClick={() => {
              pauseTelegrams(!paused);
              setPaused(!paused);
            }}
          >
            {paused ? t("tg.resume") : t("tg.pause")}
          </button>
          <button type="button" className="secondary" onClick={clearTelegrams}>
            {t("tg.clear")}
          </button>
          <button type="button" className="secondary" onClick={exportCsv} disabled={!shown.length}>
            {t("tg.export")}
          </button>
        </div>
      </div>
      <div className="card filters-row">
        <label className="inline">
          {t("tg.sender")}
          <select value={sender} onChange={(e) => setSender(e.target.value)}>
            <option value="">{t("tg.allSenders")}</option>
            {senders.map((s) => (
              <option key={s} value={s}>
                {s}
                {names.get(s) ? ` · ${names.get(s)}` : ""}
              </option>
            ))}
          </select>
        </label>
        <label className="inline">
          {t("tg.rorg")}
          <select value={rorg} onChange={(e) => setRorg(e.target.value)}>
            <option value="">{t("tg.all")}</option>
            {rorgs.map((r) => (
              <option key={r} value={r}>
                {r} {RORGS[r] ? `(${RORGS[r]})` : ""}
              </option>
            ))}
          </select>
        </label>
      </div>
      <TelegramTable telegrams={shown} names={names} />
    </div>
  );
}

export function TelegramTable({ telegrams, names }: { telegrams: Telegram[]; names?: Map<string, string> }) {
  if (!telegrams.length) return <p className="muted">{t("tg.empty")}</p>;
  return (
    <div className="card table-card">
      <table className="table mono">
        <thead>
          <tr>
            <th>{t("tg.time")}</th>
            <th>{t("tg.dir")}</th>
            <th>{t("tg.sender")}</th>
            <th>{t("tg.rorg")}</th>
            <th>{t("tg.data")}</th>
            <th>{t("tg.dbm")}</th>
          </tr>
        </thead>
        <tbody>
          {[...telegrams].reverse().slice(0, 300).map((x, i) => (
            <tr key={`${x.time}-${i}`} className={x.duplicate ? "dim" : ""}>
              <td>{new Date(x.time * 1000).toLocaleTimeString(locale())}</td>
              <td>{x.dir === "tx" ? `→ ${t("tg.tx")}` : `← ${t("tg.rx")}`}</td>
              <td>
                {x.dir === "tx" ? x.destination : x.sender}
                <span className="sans muted"> {(names?.get(x.dir === "tx" ? x.destination : x.sender) ?? x.name) || ""}</span>
              </td>
              <td>
                {x.rorg} <span className="muted">{RORGS[x.rorg] ?? ""}</span>
              </td>
              <td>
                {x.data}
                {x.duplicate && <span className="sans muted"> ({t("tg.dup")})</span>}
              </td>
              <td>{x.dbm != null ? -Math.abs(x.dbm) : ""}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

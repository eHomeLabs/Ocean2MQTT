import { useEffect, useState } from "react";
import { useStore } from "./api";
import { t } from "./i18n";

export function UpdateBanner() {
  const { info } = useStore();
  const [version, setVersion] = useState<string | null>(null);
  useEffect(() => {
    let alive = true;
    const check = async () => {
      try {
        const response = await fetch(new URL("api/version", window.location.href), { cache: "no-store" });
        if (!response.ok) return;
        const data = await response.json();
        if (alive && typeof data.version === "string") setVersion(data.version);
      } catch { /* A reconnect may still be in progress. */ }
    };
    void check();
    const timer = window.setInterval(check, 60000);
    const visible = () => { if (document.visibilityState === "visible") void check(); };
    document.addEventListener("visibilitychange", visible);
    return () => { alive = false; clearInterval(timer); document.removeEventListener("visibilitychange", visible); };
  }, []);
  const current = version ?? info?.version;
  if (!current || current === __APP_VERSION__) return null;
  return <div className="card update-banner" role="status">
    <span>{t("update.available", { version: current })}</span>
    <button type="button" onClick={() => {
      const url = new URL(window.location.href);
      url.searchParams.set("ui", current);
      window.location.replace(url);
    }}>{t("update.reload")}</button>
    <small>{t("update.unsaved")}</small>
  </div>;
}

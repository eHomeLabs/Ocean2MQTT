import { useState } from "react";
import atlas from "./assets/generic-devices.png";
import type { Product } from "./types";

/** Row-major positions in the 4 × 3 generic device artwork library. */
export function genericImageIndex(p: Product): number {
  const eep = p.eep.toUpperCase();
  const keys = new Set(p.exposes.map((e) => e.key));
  if (eep === "F6-05-01" || keys.has("water_leak")) return 11;
  if (eep.startsWith("D5-00") || eep === "F6-10-00" || (keys.has("contact") || keys.has("open"))) return 5;
  if (eep.startsWith("A5-20")) return 10;
  if (eep.startsWith("D2-05") || keys.has("position")) return 7;
  if (p.type === "prise") return 1;
  if (eep.startsWith("A5-09") || keys.has("co2") || keys.has("voc")) return 4;
  if (eep.startsWith("A5-07") || eep.startsWith("A5-08") || (keys.has("occupancy") || keys.has("motion"))) return 2;
  if (eep.startsWith("A5-06") || keys.has("illuminance")) return 3;
  if (p.type === "chauffage" || keys.has("setpoint")) return 9;
  if (eep.startsWith("A5-02") || eep.startsWith("A5-04") || keys.has("temperature")) return 0;
  if (p.type === "interrupteur" || eep.startsWith("F6-02") || eep.startsWith("F6-01")) return 8;
  return 6;
}

export function ProductImage({ product, className = "thumb" }: { product: Product; className?: string }) {
  const [failed, setFailed] = useState<string | null>(null);
  if (product.image && failed !== product.image) {
    return <img src={product.image} alt="" className={className} onError={() => setFailed(product.image!)} />;
  }
  const index = genericImageIndex(product);
  return (
    <span
      className={`${className} generic-product-image`}
      role="img"
      aria-label={`${product.name} — générique`}
      style={{
        backgroundImage: `url(${atlas})`,
        backgroundPosition: `${(index % 4) * 100 / 3}% ${Math.floor(index / 4) * 50}%`,
      }}
    />
  );
}

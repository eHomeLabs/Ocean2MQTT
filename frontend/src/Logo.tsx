export function LogoMark({ size = 36, dark = true }: { size?: number; dark?: boolean }) {
  const ring = dark ? "#FFFFFF" : "#0B2E4A";
  const wave = dark ? "#2DD4BF" : "#14B8A6";
  const bg = dark ? "#0B2E4A" : "#FFFFFF";
  return (
    <svg viewBox="0 0 64 64" width={size} height={size} aria-hidden="true">
      <defs>
        <clipPath id="o2m-clip">
          <circle cx="30" cy="34" r="18.5" />
        </clipPath>
      </defs>
      <circle cx="30" cy="34" r="21" fill="none" stroke={ring} strokeWidth="6" />
      <path clipPath="url(#o2m-clip)" d="M4 37 q6.5 -7 13 0 t13 0 t13 0 t13 0" fill="none" stroke={wave} strokeWidth="6" strokeLinecap="round" />
      <circle cx="44.85" cy="19.15" r="5" fill={wave} stroke={bg} strokeWidth="2.5" />
      <path d="M48.21 6.59 A13 13 0 0 1 57.41 15.79" fill="none" stroke={wave} strokeWidth="4" strokeLinecap="round" />
    </svg>
  );
}

export function Wordmark() {
  return (
    <span className="wordmark">
      <b>Ocean</b>
      <b className="two">2</b>
      <span>MQTT</span>
    </span>
  );
}

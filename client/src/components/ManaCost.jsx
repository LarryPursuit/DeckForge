const COLOR_NAMES = { W: "white", U: "blue", B: "black", R: "red", G: "green", C: "colorless" };

/** Renders "{2}{R}{R}" as small mana pips. */
export default function ManaCost({ cost, size = "sm" }) {
  if (!cost) return null;
  const symbols = cost.match(/\{[^}]+\}/g) || [];
  if (!symbols.length) return null;
  const label = symbols
    .map((s) => {
      const v = s.slice(1, -1);
      return COLOR_NAMES[v] || v;
    })
    .join(" ");
  return (
    <span className={`mana mana-${size}`} aria-label={`Mana cost: ${label}`} title={cost}>
      {symbols.map((s, i) => {
        const v = s.slice(1, -1);
        const kind = COLOR_NAMES[v] ? v : "generic";
        return (
          <span key={i} className={`pip pip-${kind}`} aria-hidden="true">
            {kind === "generic" ? v : ""}
          </span>
        );
      })}
    </span>
  );
}

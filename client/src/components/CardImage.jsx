import { useState } from "react";
import ManaCost from "./ManaCost";

function frameColor(colors = []) {
  if (colors.length === 0) return "colorless";
  if (colors.length > 1) return "gold";
  return colors[0];
}

/**
 * Shows the Scryfall image, or a drawn card frame when there is no image
 * (offline mode, or an image that fails to load).
 */
export default function CardImage({ card, small = false }) {
  const [failed, setFailed] = useState(false);
  const src = small ? card.image_small || card.image_url : card.image_url;

  if (src && !failed) {
    return (
      <img
        className="card-img"
        src={src}
        alt={card.name}
        loading="lazy"
        onError={() => setFailed(true)}
      />
    );
  }

  return (
    <div className={`card-frame frame-${frameColor(card.colors)}`} role="img" aria-label={card.name}>
      <div className="frame-title">
        <span className="frame-name">{card.name}</span>
        <ManaCost cost={card.mana_cost} />
      </div>
      <div className="frame-art" />
      <div className="frame-type">{card.type_line}</div>
      <div className="frame-text" />
    </div>
  );
}

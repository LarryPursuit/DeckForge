import { apiFetch } from "../api";
import CardSearch from "../components/CardSearch";

export default function SearchPage() {
  async function addToCollection(card) {
    const item = await apiFetch("/api/collection", { method: "POST", body: { card_id: card.id } });
    return { message: `Added ${card.name}. You own ${item.quantity}.`, owned: item.quantity };
  }

  return (
    <>
      <div className="page-head">
        <h1>Find cards</h1>
        <p className="lede">
          Search every Magic card on Scryfall. Each click adds one copy to your collection.
        </p>
      </div>
      <CardSearch actionLabel="Add to collection" onPick={addToCollection} autoFocus />
    </>
  );
}

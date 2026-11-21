export default function Pagination({ page, pages, onChange }) {
  if (pages <= 1) return null;
  const go = (p) => {
    onChange(p);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };
  return (
    <nav className="pagination" aria-label="Pages">
      <button type="button" className="btn btn-small" onClick={() => go(page - 1)} disabled={page <= 1}>
        Previous
      </button>
      <span aria-current="page">
        Page {page} of {pages}
      </span>
      <button type="button" className="btn btn-small" onClick={() => go(page + 1)} disabled={page >= pages}>
        Next
      </button>
    </nav>
  );
}

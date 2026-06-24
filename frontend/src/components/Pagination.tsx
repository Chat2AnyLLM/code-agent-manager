type PageSlot = number | 'ellipsis'

type PaginationProps = {
  currentPage: number
  totalPages: number
  disabled?: boolean
  previousLabel: string
  nextLabel: string
  summaryLabel: string
  ariaLabel?: string
  onPageChange: (page: number) => void
}

const PAGE_WINDOW = 2

export function Pagination({
  currentPage,
  totalPages,
  disabled = false,
  previousLabel,
  nextLabel,
  summaryLabel,
  ariaLabel = 'pagination',
  onPageChange,
}: PaginationProps) {
  if (totalPages <= 1) return null

  const clampedPage = Math.min(Math.max(currentPage, 1), totalPages)
  const pages = paginationSlots(clampedPage, totalPages)

  return (
    <nav className="pagination" aria-label={ariaLabel}>
      <button onClick={() => onPageChange(clampedPage - 1)} disabled={disabled || clampedPage === 1}>{previousLabel}</button>
      <ol className="pagination-pages" aria-label={summaryLabel}>
        {pages.map((page, index) => page === 'ellipsis'
          ? <li key={`ellipsis-${index}`} className="pagination-ellipsis" aria-hidden="true">…</li>
          : (
            <li key={page}>
              <button
                className="pagination-page"
                aria-current={page === clampedPage ? 'page' : undefined}
                aria-label={`Go to page ${page}`}
                onClick={() => onPageChange(page)}
                disabled={disabled || page === clampedPage}
              >
                {page}
              </button>
            </li>
          )
        )}
      </ol>
      <span className="pagination-summary">{summaryLabel}</span>
      <button onClick={() => onPageChange(clampedPage + 1)} disabled={disabled || clampedPage === totalPages}>{nextLabel}</button>
    </nav>
  )
}

function paginationSlots(currentPage: number, totalPages: number): PageSlot[] {
  const visible = new Set<number>([1, totalPages])
  const start = Math.max(1, currentPage - PAGE_WINDOW)
  const end = Math.min(totalPages, currentPage + PAGE_WINDOW)

  for (let page = start; page <= end; page += 1) {
    visible.add(page)
  }

  const sorted = Array.from(visible).sort((a, b) => a - b)
  const slots: PageSlot[] = []

  for (const page of sorted) {
    const previous = slots[slots.length - 1]
    if (typeof previous === 'number' && page - previous > 1) {
      slots.push('ellipsis')
    }
    slots.push(page)
  }

  return slots
}

import { Fragment, ReactNode, useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { useTranslation } from 'react-i18next'

// ExpandableTable renders a compact table where each row can toggle open a
// full-width detail panel. It replaces the card grids used across the app:
// rows stay scannable (one line each) while the "usage and details" that used
// to bloat every card move into the expanded cell, revealed on demand.
//
// Expansion is driven by an explicit chevron button (not a whole-row click) so
// interactive controls placed in a row's cells (selects, install buttons, a
// nested <details>) never accidentally toggle the row.

export type Column<T> = {
  header: string
  cell: (row: T) => ReactNode
  className?: string
  width?: string
}

type ExpandableTableProps<T> = {
  columns: Column<T>[]
  rows: T[]
  rowKey: (row: T) => string
  renderExpanded?: (row: T) => ReactNode
  empty?: ReactNode
  ariaLabel?: string
}

export function ExpandableTable<T>({ columns, rows, rowKey, renderExpanded, empty, ariaLabel }: ExpandableTableProps<T>) {
  const { t } = useTranslation()
  const [open, setOpen] = useState<Set<string>>(() => new Set())
  const expandable = Boolean(renderExpanded)
  const colCount = columns.length + (expandable ? 1 : 0)

  function toggle(key: string) {
    setOpen((current) => {
      const next = new Set(current)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  return (
    <div className="table-scroll">
      <table aria-label={ariaLabel}>
        <colgroup>
          {expandable && <col style={{ width: '2.2rem' }} />}
          {columns.map((col) => <col key={col.header} style={col.width ? { width: col.width } : undefined} />)}
        </colgroup>
        <thead>
          <tr>
            {expandable && <th className="col-toggle" scope="col" aria-label="expand" />}
            {columns.map((col) => <th key={col.header} scope="col" className={col.className}>{col.header}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 && empty && (
            <tr><td colSpan={colCount}>{empty}</td></tr>
          )}
          {rows.map((row) => {
            const key = rowKey(row)
            const isOpen = open.has(key)
            return (
              <Fragment key={key}>
                <tr className={expandable ? 'expandable-row' : undefined}>
                  {expandable && (
                    <td className="col-toggle">
                      <button
                        type="button"
                        className="row-toggle"
                        aria-expanded={isOpen}
                        aria-label={isOpen ? t('table.hideDetails') : t('table.details')}
                        onClick={() => toggle(key)}
                      >
                        {isOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                      </button>
                    </td>
                  )}
                  {columns.map((col) => <td key={col.header} className={col.className}>{col.cell(row)}</td>)}
                </tr>
                {expandable && isOpen && (
                  <tr className="expanded-detail-row">
                    <td colSpan={colCount}>{renderExpanded!(row)}</td>
                  </tr>
                )}
              </Fragment>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

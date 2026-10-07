import { useState, useMemo } from 'react'
import type { MatchResult } from '../App'

interface Props {
  results: MatchResult[]
  jobId: string
  onViewValidation: () => void
}

const TIER_STYLES: Record<string, string> = {
  'High': 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300',
  'Probable': 'bg-sky-100 dark:bg-sky-900/30 text-sky-700 dark:text-sky-300',
  'Weak': 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400',
  'No match': 'bg-gray-50 dark:bg-gray-900 text-gray-400 dark:text-gray-500',
}

const REC_STYLES: Record<string, string> = {
  'Worth a credit': 'bg-[var(--accent-light)] text-[var(--accent)] font-medium',
  'Verify first': 'bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-300',
  'Skip': 'bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400',
}

function fmtCurrency(v: number | null | undefined): string {
  if (v == null) return '—'
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`
  if (v >= 1_000) return `$${(v / 1_000).toFixed(0)}K`
  return `$${v.toFixed(0)}`
}

export function ResultsScreen({ results, jobId, onViewValidation }: Props) {
  const [sortKey, setSortKey] = useState<string>('match_confidence')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')
  const [tierFilter, setTierFilter] = useState<string>('all')
  const [recFilter, setRecFilter] = useState<string>('all')
  const [excludeFranchises, setExcludeFranchises] = useState(false)
  const [excludeOwnership, setExcludeOwnership] = useState(false)
  const [minRevenue, setMinRevenue] = useState('')
  const [maxRevenue, setMaxRevenue] = useState('')
  const [selectedRow, setSelectedRow] = useState<MatchResult | null>(null)

  const filtered = useMemo(() => {
    let data = [...results]

    if (tierFilter !== 'all') data = data.filter(r => r.match_tier === tierFilter)
    if (recFilter !== 'all') data = data.filter(r => r.recommendation === recFilter)
    if (excludeFranchises) data = data.filter(r => !r.franchise_flag)
    if (excludeOwnership) data = data.filter(r => !r.change_of_ownership)

    const minRev = minRevenue ? parseFloat(minRevenue) * 1_000_000 : null
    const maxRev = maxRevenue ? parseFloat(maxRevenue) * 1_000_000 : null
    if (minRev) data = data.filter(r => !r.revenue_point || r.revenue_point >= minRev)
    if (maxRev) data = data.filter(r => !r.revenue_point || r.revenue_point <= maxRev)

    data.sort((a, b) => {
      const av = (a as any)[sortKey] ?? 0
      const bv = (b as any)[sortKey] ?? 0
      const cmp = av < bv ? -1 : av > bv ? 1 : 0
      return sortDir === 'asc' ? cmp : -cmp
    })

    return data
  }, [results, sortKey, sortDir, tierFilter, recFilter, excludeFranchises, excludeOwnership, minRevenue, maxRevenue])

  const handleSort = (key: string) => {
    if (sortKey === key) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    } else {
      setSortKey(key)
      setSortDir('desc')
    }
  }

  const sortIcon = (key: string) => {
    if (sortKey !== key) return ''
    return sortDir === 'asc' ? ' ▲' : ' ▼'
  }

  const matchedCount = results.filter(r => r.match_tier !== 'No match').length
  const hasRevenue = results.some(r => r.saasquatch_revenue != null)

  return (
    <div className="flex gap-6">
      {/* Sidebar filters */}
      <aside className="w-56 shrink-0">
        <div className="bg-[var(--surface)] border border-[var(--border)] rounded-lg p-4 sticky top-8">
          <h3 className="text-sm font-medium text-[var(--text-h)] uppercase tracking-wider mb-3">
            Buy Box
          </h3>

          <label className="block text-xs text-[var(--text)] mb-1">Match tier</label>
          <select value={tierFilter} onChange={e => setTierFilter(e.target.value)}
            className="w-full text-sm bg-[var(--bg)] border border-[var(--border)] rounded px-2 py-1 mb-3 text-[var(--text-h)]">
            <option value="all">All tiers</option>
            <option value="High">High</option>
            <option value="Probable">Probable</option>
            <option value="Weak">Weak</option>
            <option value="No match">No match</option>
          </select>

          <label className="block text-xs text-[var(--text)] mb-1">Recommendation</label>
          <select value={recFilter} onChange={e => setRecFilter(e.target.value)}
            className="w-full text-sm bg-[var(--bg)] border border-[var(--border)] rounded px-2 py-1 mb-3 text-[var(--text-h)]">
            <option value="all">All</option>
            <option value="Worth a credit">Worth a credit</option>
            <option value="Verify first">Verify first</option>
            <option value="Skip">Skip</option>
          </select>

          <label className="block text-xs text-[var(--text)] mb-1">Min revenue ($M)</label>
          <input type="number" step="0.1" value={minRevenue} onChange={e => setMinRevenue(e.target.value)}
            placeholder="0"
            className="w-full text-sm bg-[var(--bg)] border border-[var(--border)] rounded px-2 py-1 mb-3 text-[var(--text-h)] font-mono" />

          <label className="block text-xs text-[var(--text)] mb-1">Max revenue ($M)</label>
          <input type="number" step="0.1" value={maxRevenue} onChange={e => setMaxRevenue(e.target.value)}
            placeholder="any"
            className="w-full text-sm bg-[var(--bg)] border border-[var(--border)] rounded px-2 py-1 mb-3 text-[var(--text-h)] font-mono" />

          <label className="flex items-center gap-2 text-sm text-[var(--text)] mb-2 cursor-pointer">
            <input type="checkbox" checked={excludeFranchises} onChange={e => setExcludeFranchises(e.target.checked)} />
            Exclude franchises
          </label>
          <label className="flex items-center gap-2 text-sm text-[var(--text)] mb-4 cursor-pointer">
            <input type="checkbox" checked={excludeOwnership} onChange={e => setExcludeOwnership(e.target.checked)} />
            Exclude ownership changes
          </label>

          <div className="border-t border-[var(--border)] pt-3 mt-1">
            <p className="text-xs text-[var(--text)]">
              {filtered.length} of {results.length} leads shown
            </p>
            <p className="text-xs text-[var(--text)]">
              {matchedCount} matched to PPP records
            </p>
          </div>

          {hasRevenue && (
            <button onClick={onViewValidation}
              className="w-full mt-4 py-2 text-sm bg-[var(--accent)] text-white rounded-md font-medium hover:opacity-90">
              View Validation
            </button>
          )}

          <a href={`/api/export/${jobId}.csv`} download
            className="block w-full mt-2 py-2 text-sm text-center border border-[var(--border)] rounded-md text-[var(--text-h)] hover:bg-[var(--border)] transition-colors">
            Export CSV
          </a>
        </div>
      </aside>

      {/* Main table */}
      <div className="flex-1 min-w-0">
        <div className="bg-[var(--surface)] border border-[var(--border)] rounded-lg overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--border)] bg-[var(--bg)]">
                  {[
                    { key: 'input_name', label: 'Company' },
                    { key: 'input_city', label: 'City' },
                    { key: 'match_tier', label: 'Match' },
                    { key: 'revenue_point', label: 'PPP Revenue' },
                    ...(hasRevenue ? [{ key: 'saasquatch_revenue', label: 'SQ Revenue' }] : []),
                    { key: 'headcount', label: 'Jobs' },
                    { key: 'business_age', label: 'Age' },
                    { key: 'sba_loan_count', label: 'SBA' },
                    { key: 'recommendation', label: 'Rec.' },
                  ].map(({ key, label }) => (
                    <th key={key} onClick={() => handleSort(key)}
                      className="px-3 py-2 text-left text-xs font-medium text-[var(--text)] uppercase tracking-wider cursor-pointer hover:text-[var(--text-h)] whitespace-nowrap">
                      {label}{sortIcon(key)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.map((r) => (
                  <tr key={r.row_index}
                    onClick={() => setSelectedRow(selectedRow?.row_index === r.row_index ? null : r)}
                    className={`border-b border-[var(--border)] cursor-pointer transition-colors ${
                      selectedRow?.row_index === r.row_index
                        ? 'bg-[var(--accent-light)]'
                        : 'hover:bg-[var(--bg)]'
                    }`}>
                    <td className="px-3 py-2.5 text-[var(--text-h)] font-medium max-w-48 truncate">
                      {r.input_name}
                      {r.franchise_flag && <span className="ml-1 text-xs text-orange-500" title="Franchise">F</span>}
                      {r.change_of_ownership && <span className="ml-1 text-xs text-purple-500" title="Change of ownership">C</span>}
                    </td>
                    <td className="px-3 py-2.5 text-[var(--text)] whitespace-nowrap">
                      {r.input_city}, {r.input_state}
                    </td>
                    <td className="px-3 py-2.5">
                      <span className={`inline-block px-2 py-0.5 rounded text-xs ${TIER_STYLES[r.match_tier] || ''}`}
                        title={r.match_reasons.join('; ')}>
                        {r.match_tier}
                      </span>
                    </td>
                    <td className="px-3 py-2.5 font-mono text-[var(--text-h)] whitespace-nowrap"
                      title={r.revenue_formula}>
                      {r.revenue_point ? fmtCurrency(r.revenue_point) : '—'}
                    </td>
                    {hasRevenue && (
                      <td className="px-3 py-2.5 font-mono text-[var(--text)] whitespace-nowrap">
                        {r.saasquatch_revenue_raw || '—'}
                      </td>
                    )}
                    <td className="px-3 py-2.5 font-mono text-[var(--text-h)]">
                      {r.headcount ?? '—'}
                    </td>
                    <td className="px-3 py-2.5 text-[var(--text)] text-xs max-w-24 truncate"
                      title={r.business_age}>
                      {r.business_age || '—'}
                    </td>
                    <td className="px-3 py-2.5 text-[var(--text-h)]">
                      {r.sba_loan_count > 0 ? (
                        <span className="font-mono">
                          {r.sba_loan_count}
                          {r.sba_maturing && <span className="text-amber-500 ml-0.5" title={r.sba_maturing_details}>!</span>}
                        </span>
                      ) : '—'}
                    </td>
                    <td className="px-3 py-2.5">
                      <span className={`inline-block px-2 py-0.5 rounded text-xs ${REC_STYLES[r.recommendation] || ''}`}
                        title={r.recommendation_rule}>
                        {r.recommendation}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Side panel */}
      {selectedRow && (
        <aside className="w-80 shrink-0">
          <div className="bg-[var(--surface)] border border-[var(--border)] rounded-lg p-4 sticky top-8">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-medium text-[var(--text-h)] uppercase tracking-wider">
                Detail
              </h3>
              <button onClick={() => setSelectedRow(null)}
                className="text-[var(--text)] hover:text-[var(--text-h)] text-lg">&times;</button>
            </div>

            <div className="space-y-4 text-sm">
              <section>
                <p className="text-xs text-[var(--text)] uppercase mb-1">Input</p>
                <p className="text-[var(--text-h)] font-medium">{selectedRow.input_name}</p>
                <p className="text-[var(--text)]">{selectedRow.input_city}, {selectedRow.input_state}</p>
              </section>

              {selectedRow.matched_name && (
                <section>
                  <p className="text-xs text-[var(--text)] uppercase mb-1">PPP Match</p>
                  <p className="text-[var(--text-h)]">{selectedRow.matched_name}</p>
                  <p className="text-[var(--text)]">{selectedRow.matched_address}</p>
                  <p className="text-[var(--text)]">{selectedRow.matched_city}, {selectedRow.matched_zip}</p>
                  <p className="text-[var(--text)] mt-1">NAICS: {selectedRow.naics_code}</p>
                </section>
              )}

              <section>
                <p className="text-xs text-[var(--text)] uppercase mb-1">Match reasons</p>
                <ul className="space-y-0.5">
                  {selectedRow.match_reasons.map((r, i) => (
                    <li key={i} className="text-[var(--text)]">{r}</li>
                  ))}
                </ul>
              </section>

              {selectedRow.annual_payroll && (
                <section>
                  <p className="text-xs text-[var(--text)] uppercase mb-1">Revenue (2020-21)</p>
                  <p className="text-[var(--text-h)] font-mono font-medium">
                    {fmtCurrency(selectedRow.revenue_point)}
                  </p>
                  {selectedRow.revenue_low && selectedRow.revenue_high && (
                    <p className="text-xs text-[var(--text)] font-mono">
                      Range: {fmtCurrency(selectedRow.revenue_low)} – {fmtCurrency(selectedRow.revenue_high)}
                    </p>
                  )}
                  <p className="text-xs text-[var(--text)] mt-1">{selectedRow.revenue_formula}</p>
                  <p className="text-xs text-[var(--text)] mt-1">
                    Payroll: {fmtCurrency(selectedRow.annual_payroll)}
                  </p>
                  <p className="text-xs text-[var(--text)]">{selectedRow.payroll_formula}</p>
                  {selectedRow.payroll_proceed_note && (
                    <p className="text-xs text-[var(--text)] mt-1">{selectedRow.payroll_proceed_note}</p>
                  )}
                </section>
              )}

              {selectedRow.sba_loans.length > 0 && (
                <section>
                  <p className="text-xs text-[var(--text)] uppercase mb-1">
                    SBA Loans ({selectedRow.sba_loans.length})
                  </p>
                  <div className="space-y-2">
                    {selectedRow.sba_loans.map((loan, i) => (
                      <div key={i} className="text-xs border-l-2 border-[var(--border)] pl-2">
                        <p className="text-[var(--text-h)]">
                          {loan.program} — {fmtCurrency(loan.amount)}
                        </p>
                        <p className="text-[var(--text)]">
                          {loan.approval_date} · {loan.term_months}mo · {loan.status}
                        </p>
                        <p className="text-[var(--text)]">{loan.lender}</p>
                      </div>
                    ))}
                  </div>
                  {selectedRow.sba_maturing && (
                    <p className="text-xs text-amber-600 dark:text-amber-400 mt-2">
                      Loan maturing within 12 months: {selectedRow.sba_maturing_details}
                    </p>
                  )}
                </section>
              )}

              <section>
                <p className="text-xs text-[var(--text)] uppercase mb-1">Recommendation</p>
                <p className={`inline-block px-2 py-0.5 rounded text-xs ${REC_STYLES[selectedRow.recommendation] || ''}`}>
                  {selectedRow.recommendation}
                </p>
                <p className="text-xs text-[var(--text)] mt-1">{selectedRow.recommendation_rule}</p>
              </section>
            </div>
          </div>
        </aside>
      )}
    </div>
  )
}

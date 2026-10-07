import { useState, useMemo } from 'react'
import type { MatchResult } from '../App'

interface Props {
  results: MatchResult[]
  jobId: string
  groundtruthEnabled: boolean
  onImport: () => void
}

const TIER_COLORS: Record<string, string> = {
  'High': 'bg-emerald-500/20 text-emerald-400',
  'Probable': 'bg-blue-500/20 text-blue-400',
  'Weak': 'bg-gray-500/20 text-gray-400',
  'No match': 'bg-gray-800 text-gray-600',
}

const REC_COLORS: Record<string, string> = {
  'Worth a credit': 'text-emerald-400',
  'Verify first': 'text-amber-400',
  'Skip': 'text-gray-500',
}

function fmt(v: number | null | undefined): string {
  if (v == null) return '—'
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`
  if (v >= 1_000) return `$${(v / 1_000).toFixed(0)}K`
  return `$${v.toFixed(0)}`
}

export function LeadsView({ results, jobId, groundtruthEnabled, onImport }: Props) {
  const [sortKey, setSortKey] = useState('match_confidence')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')
  const [search, setSearch] = useState('')
  const [recFilter, setRecFilter] = useState('all')
  const [selectedRow, setSelectedRow] = useState<MatchResult | null>(null)

  const filtered = useMemo(() => {
    let data = [...results]
    if (search) {
      const q = search.toLowerCase()
      data = data.filter(r => r.input_name.toLowerCase().includes(q) || r.input_city.toLowerCase().includes(q))
    }
    if (recFilter !== 'all') data = data.filter(r => r.recommendation === recFilter)
    data.sort((a, b) => {
      const av = (a as any)[sortKey] ?? 0
      const bv = (b as any)[sortKey] ?? 0
      return sortDir === 'asc' ? (av < bv ? -1 : 1) : (av > bv ? -1 : 1)
    })
    return data
  }, [results, search, recFilter, sortKey, sortDir])

  const handleSort = (key: string) => {
    if (sortKey === key) setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    else { setSortKey(key); setSortDir('desc') }
  }

  if (!results.length) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center max-w-md">
          <div className="w-16 h-16 rounded-2xl bg-[#1a1d2e] flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 7.5v3m0 0v3m0-3h3m-3 0h-3m-2.25-4.125a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zM4 19.235v-.11a6.375 6.375 0 0112.75 0v.109A12.318 12.318 0 0110.374 21c-2.331 0-4.512-.645-6.374-1.766z" />
            </svg>
          </div>
          <h3 className="text-lg font-semibold text-white mb-2">No leads imported</h3>
          <p className="text-sm text-gray-500 mb-6">
            Import your SaaSquatch CSV export to see leads enriched with federal revenue data.
          </p>
          <button onClick={onImport}
            className="px-5 py-2.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-500">
            Import CSV
          </button>
        </div>
      </div>
    )
  }

  const stats = useMemo(() => {
    const matched = results.filter(r => r.match_tier !== 'No match').length
    const enrich = results.filter(r => r.recommendation === 'Worth a credit').length
    const verify = results.filter(r => r.recommendation === 'Verify first').length
    const skip = results.filter(r => r.recommendation === 'Skip').length
    const withRevenue = results.filter(r => r.revenue_point && r.saasquatch_revenue).length
    const off2x = results.filter(r => {
      if (!r.revenue_point || !r.saasquatch_revenue) return false
      const ratio = r.saasquatch_revenue / r.revenue_point
      return ratio > 2 || ratio < 0.5
    }).length
    return { matched, enrich, verify, skip, withRevenue, off2x }
  }, [results])

  return (
    <div className="flex h-screen">
      {/* Main table area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Summary stats */}
        {groundtruthEnabled && (
          <div className="px-6 py-3 border-b border-[#1e2130] bg-[#0f1117] grid grid-cols-6 gap-3">
            {[
              { label: 'Total', value: results.length, color: 'text-white' },
              { label: 'PPP Matched', value: stats.matched, color: 'text-blue-400' },
              { label: 'Enrich', value: stats.enrich, color: 'text-emerald-400' },
              { label: 'Verify', value: stats.verify, color: 'text-amber-400' },
              { label: 'Skip', value: stats.skip, color: 'text-gray-500' },
              { label: 'Revenue 2x+ off', value: stats.off2x, color: stats.off2x > 0 ? 'text-red-400' : 'text-gray-500' },
            ].map((s, i) => (
              <div key={i} className="bg-[#13151c] rounded-lg px-3 py-2 border border-[#1e2130]">
                <p className="text-[9px] text-gray-600 uppercase tracking-wider">{s.label}</p>
                <p className={`text-lg font-bold font-mono ${s.color}`}>{s.value}</p>
              </div>
            ))}
          </div>
        )}

        {/* Top bar */}
        <div className="px-6 py-3 border-b border-[#1e2130] bg-[#0f1117] flex items-center gap-3 sticky top-0 z-10">
          <div className="relative flex-1 max-w-sm">
            <svg className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              value={search} onChange={e => setSearch(e.target.value)}
              placeholder="Search leads..."
              className="w-full bg-[#13151c] border border-[#252840] rounded-lg pl-9 pr-3 py-1.5 text-sm text-gray-300 placeholder-gray-600 focus:outline-none focus:border-blue-500/50"
            />
          </div>

          <div className="flex items-center gap-1 bg-[#13151c] border border-[#252840] rounded-lg p-0.5">
            {['all', 'Worth a credit', 'Verify first', 'Skip'].map(v => (
              <button key={v} onClick={() => setRecFilter(v)}
                className={`px-2.5 py-1 text-xs rounded-md transition-colors ${
                  recFilter === v ? 'bg-[#1a1d2e] text-white' : 'text-gray-500 hover:text-gray-300'
                }`}>
                {v === 'all' ? 'All' : v}
              </button>
            ))}
          </div>

          <span className="text-xs text-gray-600 ml-auto">{filtered.length} leads</span>

          {jobId && (
            <a href={`/api/export/${jobId}.csv`} download
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-gray-400 border border-[#252840] rounded-lg hover:text-gray-200 hover:border-gray-600 transition-colors">
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
              </svg>
              Export
            </a>
          )}
        </div>

        {/* Table */}
        <div className="flex-1 overflow-auto">
          <table className="w-full text-xs">
            <thead className="sticky top-0 z-10">
              <tr className="bg-[#13151c] border-b border-[#1e2130]">
                {[
                  { k: 'input_name', l: 'Company', w: 'min-w-48', gt: false },
                  { k: 'input_city', l: 'Location', w: 'min-w-32', gt: false },
                  { k: 'saasquatch_revenue', l: 'SaaSquatch Est.', w: 'w-28', gt: false },
                  ...(groundtruthEnabled ? [
                    { k: 'match_tier', l: 'GT Match', w: 'w-24', gt: true },
                    { k: 'revenue_point', l: 'PPP Revenue', w: 'w-32', gt: true },
                    { k: 'headcount', l: 'Jobs', w: 'w-16', gt: true },
                    { k: 'sba_loan_count', l: 'SBA', w: 'w-16', gt: true },
                    { k: 'recommendation', l: 'Action', w: 'w-24', gt: true },
                  ] : []),
                ].map(({ k, l, w, gt }) => (
                  <th key={k} onClick={() => handleSort(k)}
                    className={`px-3 py-2.5 text-left text-[10px] font-medium uppercase tracking-wider cursor-pointer hover:text-gray-300 ${w} ${
                      gt ? 'text-emerald-600 bg-emerald-500/[0.03]' : 'text-gray-500'
                    }`}>
                    {l}
                    {sortKey === k && <span className="ml-1">{sortDir === 'asc' ? '▲' : '▼'}</span>}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map(r => (
                <tr key={r.row_index}
                  onClick={() => setSelectedRow(selectedRow?.row_index === r.row_index ? null : r)}
                  className={`border-b border-[#1e2130]/50 cursor-pointer transition-colors ${
                    selectedRow?.row_index === r.row_index ? 'bg-blue-500/5' : 'hover:bg-[#13151c]'
                  }`}>
                  <td className="px-3 py-2.5">
                    <span className="text-gray-200 font-medium">{r.input_name}</span>
                    {r.franchise_flag && <span className="ml-1.5 text-[9px] px-1 py-0.5 rounded bg-orange-500/10 text-orange-400">Franchise</span>}
                    {r.change_of_ownership && <span className="ml-1 text-[9px] px-1 py-0.5 rounded bg-purple-500/10 text-purple-400">Acquired</span>}
                  </td>
                  <td className="px-3 py-2.5 text-gray-400">{r.input_city}, {r.input_state}</td>
                  <td className="px-3 py-2.5 text-gray-400 font-mono">{r.saasquatch_revenue_raw || '—'}</td>

                  {groundtruthEnabled && (
                    <>
                      <td className="px-3 py-2.5 bg-emerald-500/[0.02]">
                        <span className={`inline-block px-1.5 py-0.5 rounded text-[10px] font-medium ${TIER_COLORS[r.match_tier]}`}>
                          {r.match_tier}
                        </span>
                      </td>
                      <td className="px-3 py-2.5 bg-emerald-500/[0.02] font-mono text-gray-200" title={r.revenue_formula}>
                        {fmt(r.revenue_point)}
                        {r.saasquatch_revenue && r.revenue_point && (() => {
                          const ratio = r.saasquatch_revenue / r.revenue_point
                          if (ratio > 2) return <span className="ml-1.5 px-1 py-0.5 rounded bg-red-500/15 text-red-400 text-[9px]">+{((ratio - 1) * 100).toFixed(0)}%</span>
                          if (ratio < 0.5) return <span className="ml-1.5 px-1 py-0.5 rounded bg-red-500/15 text-red-400 text-[9px]">{((ratio - 1) * 100).toFixed(0)}%</span>
                          if (Math.abs(ratio - 1) < 0.3) return <span className="ml-1.5 px-1 py-0.5 rounded bg-emerald-500/10 text-emerald-500 text-[9px]">~</span>
                          return null
                        })()}
                      </td>
                      <td className="px-3 py-2.5 bg-emerald-500/[0.02] text-gray-400 font-mono">{r.headcount ?? '—'}</td>
                      <td className="px-3 py-2.5 bg-emerald-500/[0.02] text-gray-400 font-mono">
                        {r.sba_loan_count > 0 ? r.sba_loan_count : '—'}
                        {r.sba_maturing && <span className="text-amber-400 ml-0.5" title={r.sba_maturing_details}>!</span>}
                      </td>
                      <td className="px-3 py-2.5 bg-emerald-500/[0.02]">
                        <span className={`text-[10px] font-medium ${REC_COLORS[r.recommendation]}`} title={r.recommendation_rule}>
                          {r.recommendation === 'Worth a credit' ? 'Enrich' : r.recommendation}
                        </span>
                      </td>
                    </>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Detail panel */}
      {selectedRow && groundtruthEnabled && (
        <aside className="w-80 border-l border-[#1e2130] bg-[#13151c] overflow-y-auto shrink-0">
          <div className="p-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">GroundTruth Intel</h3>
              <button onClick={() => setSelectedRow(null)} className="text-gray-600 hover:text-gray-300">&times;</button>
            </div>

            <div className="space-y-5">
              {/* Company */}
              <div>
                <p className="text-sm font-medium text-white mb-0.5">{selectedRow.input_name}</p>
                <p className="text-xs text-gray-500">{selectedRow.input_city}, {selectedRow.input_state}</p>
              </div>

              {/* Match */}
              <div className="bg-[#1a1d2e] rounded-lg p-3">
                <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-2">Federal Record Match</p>
                <div className="flex items-center gap-2 mb-2">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-medium ${TIER_COLORS[selectedRow.match_tier]}`}>
                    {selectedRow.match_tier} ({(selectedRow.match_confidence * 100).toFixed(0)}%)
                  </span>
                </div>
                {selectedRow.matched_name && (
                  <div className="text-xs space-y-0.5">
                    <p className="text-gray-300">{selectedRow.matched_name}</p>
                    <p className="text-gray-500">{selectedRow.matched_address}</p>
                    <p className="text-gray-500">{selectedRow.matched_city}, {selectedRow.matched_zip}</p>
                  </div>
                )}
                <div className="mt-2 space-y-0.5">
                  {selectedRow.match_reasons.map((r, i) => (
                    <p key={i} className="text-[10px] text-gray-600 flex items-center gap-1">
                      <span className="w-1 h-1 rounded-full bg-gray-600 shrink-0" />
                      {r}
                    </p>
                  ))}
                </div>
              </div>

              {/* Revenue comparison */}
              {selectedRow.revenue_point && (
                <div className="bg-[#1a1d2e] rounded-lg p-3">
                  <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-2">Revenue Comparison</p>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <p className="text-[10px] text-gray-600">SaaSquatch Est.</p>
                      <p className="text-sm font-mono text-gray-300">{selectedRow.saasquatch_revenue_raw || '—'}</p>
                    </div>
                    <div>
                      <p className="text-[10px] text-gray-600">PPP-Implied</p>
                      <p className="text-sm font-mono text-white">{fmt(selectedRow.revenue_point)}</p>
                    </div>
                  </div>
                  {selectedRow.revenue_low && selectedRow.revenue_high && (
                    <p className="text-[10px] text-gray-600 mt-2 font-mono">
                      Range: {fmt(selectedRow.revenue_low)} – {fmt(selectedRow.revenue_high)}
                    </p>
                  )}
                  <p className="text-[10px] text-gray-600 mt-1">{selectedRow.revenue_formula}</p>
                  <p className="text-[10px] text-gray-600">Payroll: {fmt(selectedRow.annual_payroll)} (2020-21)</p>
                </div>
              )}

              {/* Signals */}
              <div className="bg-[#1a1d2e] rounded-lg p-3">
                <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-2">Signals</p>
                <div className="space-y-2 text-xs">
                  <div className="flex justify-between">
                    <span className="text-gray-500">Headcount at filing</span>
                    <span className="text-gray-300 font-mono">{selectedRow.headcount ?? '—'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">Business age</span>
                    <span className="text-gray-300 text-right max-w-[50%] truncate" title={selectedRow.business_age}>{selectedRow.business_age || '—'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">SBA loans</span>
                    <span className="text-gray-300 font-mono">{selectedRow.sba_loan_count || '—'}</span>
                  </div>
                  {selectedRow.sba_total_borrowed > 0 && (
                    <div className="flex justify-between">
                      <span className="text-gray-500">Total SBA borrowed</span>
                      <span className="text-gray-300 font-mono">{fmt(selectedRow.sba_total_borrowed)}</span>
                    </div>
                  )}
                  {selectedRow.franchise_flag && (
                    <div className="flex justify-between">
                      <span className="text-gray-500">Franchise</span>
                      <span className="text-orange-400">{selectedRow.franchise_name || 'Yes'}</span>
                    </div>
                  )}
                  {selectedRow.change_of_ownership && (
                    <div className="flex justify-between">
                      <span className="text-gray-500">Ownership change</span>
                      <span className="text-purple-400">Recently acquired</span>
                    </div>
                  )}
                  {selectedRow.sba_maturing && (
                    <div className="mt-2 px-2 py-1.5 bg-amber-500/10 border border-amber-500/20 rounded text-[10px] text-amber-400">
                      {selectedRow.sba_maturing_details}
                    </div>
                  )}
                </div>
              </div>

              {/* SBA Loan history */}
              {selectedRow.sba_loans.length > 0 && (
                <div className="bg-[#1a1d2e] rounded-lg p-3">
                  <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-2">SBA Loan History</p>
                  <div className="space-y-2">
                    {selectedRow.sba_loans.map((loan, i) => (
                      <div key={i} className="border-l-2 border-[#252840] pl-2 text-[10px]">
                        <p className="text-gray-300">{loan.program} — {fmt(loan.amount)}</p>
                        <p className="text-gray-600">{loan.approval_date} · {loan.term_months}mo · {loan.lender}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Recommendation */}
              <div className="bg-[#1a1d2e] rounded-lg p-3">
                <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-2">Recommendation</p>
                <p className={`text-sm font-medium ${REC_COLORS[selectedRow.recommendation]}`}>
                  {selectedRow.recommendation}
                </p>
                <p className="text-[10px] text-gray-600 mt-1">{selectedRow.recommendation_rule}</p>
              </div>
            </div>
          </div>
        </aside>
      )}
    </div>
  )
}

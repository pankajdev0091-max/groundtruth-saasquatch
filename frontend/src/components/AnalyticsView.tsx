import { useMemo } from 'react'
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid,
  Tooltip, ReferenceLine, ResponsiveContainer, Cell,
  BarChart, Bar,
} from 'recharts'
import type { MatchResult } from '../App'

interface Props {
  results: MatchResult[]
  jobId: string
}

const TIER_COLORS: Record<string, string> = {
  'High': '#10b981',
  'Probable': '#3b82f6',
  'Weak': '#6b7280',
}

function fmt(v: number): string {
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`
  if (v >= 1_000) return `$${(v / 1_000).toFixed(0)}K`
  return `$${v.toFixed(0)}`
}

export function AnalyticsView({ results, jobId }: Props) {
  const validPairs = useMemo(() =>
    results.filter(r =>
      r.saasquatch_revenue != null && r.saasquatch_revenue > 0 &&
      r.revenue_point != null && r.revenue_point > 0 &&
      r.match_tier !== 'No match'
    ), [results])

  const scatterData = useMemo(() =>
    validPairs.map(r => ({
      x: r.revenue_point!, y: r.saasquatch_revenue!,
      name: r.input_name, tier: r.match_tier,
    })), [validPairs])

  const logRatios = useMemo(() =>
    validPairs.map(r => Math.log(r.saasquatch_revenue! / r.revenue_point!)),
    [validPairs])

  const histogram = useMemo(() => {
    const bins = [
      { label: '<0.25x', min: -Infinity, max: Math.log(0.25), count: 0, color: '#ef4444' },
      { label: '0.25-0.5x', min: Math.log(0.25), max: Math.log(0.5), count: 0, color: '#f97316' },
      { label: '0.5-2x', min: Math.log(0.5), max: Math.log(2), count: 0, color: '#3b82f6' },
      { label: '2-4x', min: Math.log(2), max: Math.log(4), count: 0, color: '#f97316' },
      { label: '>4x', min: Math.log(4), max: Infinity, count: 0, color: '#ef4444' },
    ]
    for (const r of logRatios) {
      for (const b of bins) { if (r >= b.min && r < b.max) { b.count++; break } }
    }
    return bins
  }, [logRatios])

  const offBy2x = logRatios.filter(r => Math.abs(r) > Math.log(2)).length
  const pctOff = validPairs.length > 0 ? ((offBy2x / validPairs.length) * 100).toFixed(0) : '0'
  const matchedCount = results.filter(r => r.match_tier !== 'No match').length
  const worthCredit = results.filter(r => r.recommendation === 'Worth a credit').length
  const verifyFirst = results.filter(r => r.recommendation === 'Verify first').length
  const skip = results.filter(r => r.recommendation === 'Skip').length

  return (
    <div className="h-screen overflow-y-auto">
      <div className="px-8 py-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-lg font-semibold text-white">Revenue Analytics</h2>
            <p className="text-xs text-gray-500 mt-0.5">
              GroundTruth validation — comparing SaaSquatch estimates against PPP-implied revenue
            </p>
          </div>
          {jobId && (
            <a href={`/api/export/${jobId}.csv`} download
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs text-gray-400 border border-[#252840] rounded-lg hover:text-gray-200 transition-colors">
              Export annotated CSV
            </a>
          )}
        </div>

        {/* Stats row */}
        <div className="grid grid-cols-5 gap-3 mb-6">
          {[
            { label: 'Total leads', value: results.length.toString(), color: 'text-white' },
            { label: 'Matched to PPP', value: matchedCount.toString(), color: 'text-blue-400' },
            { label: 'Enrich', value: worthCredit.toString(), color: 'text-emerald-400' },
            { label: 'Verify first', value: verifyFirst.toString(), color: 'text-amber-400' },
            { label: 'Skip', value: skip.toString(), color: 'text-gray-500' },
          ].map((s, i) => (
            <div key={i} className="bg-[#13151c] border border-[#1e2130] rounded-xl p-4">
              <p className="text-[10px] text-gray-600 uppercase tracking-wider mb-1">{s.label}</p>
              <p className={`text-2xl font-bold font-mono ${s.color}`}>{s.value}</p>
            </div>
          ))}
        </div>

        {validPairs.length === 0 ? (
          <div className="bg-[#13151c] border border-[#1e2130] rounded-xl p-12 text-center">
            <p className="text-gray-400">No revenue pairs to validate.</p>
            <p className="text-xs text-gray-600 mt-2">Upload a CSV with an "Estimated Revenue" column to see the comparison.</p>
          </div>
        ) : (
          <>
            {/* Headline */}
            <div className="bg-[#13151c] border border-[#1e2130] rounded-xl p-5 mb-6">
              <p className="text-sm text-gray-300 leading-relaxed">
                On <span className="text-white font-semibold">{validPairs.length}</span> matched leads,
                the SaaSquatch revenue estimate disagreed with the PPP-implied figure by more than 2x
                for <span className="text-white font-semibold">{offBy2x}</span> leads
                (<span className="text-white font-semibold">{pctOff}%</span>).
                {offBy2x > 0 && (
                  <> Those <span className="text-amber-400 font-semibold">{offBy2x} leads</span> represent
                  enrichment credits that need verification before spending.</>
                )}
              </p>
            </div>

            {/* Charts */}
            <div className="grid lg:grid-cols-2 gap-4">
              {/* Scatter */}
              <div className="bg-[#13151c] border border-[#1e2130] rounded-xl p-5">
                <p className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-4">
                  PPP-Implied vs SaaSquatch Revenue
                </p>
                <ResponsiveContainer width="100%" height={320}>
                  <ScatterChart margin={{ top: 10, right: 20, bottom: 40, left: 50 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e2130" />
                    <XAxis type="number" dataKey="x" scale="log" domain={['dataMin', 'dataMax']}
                      tickFormatter={fmt}
                      label={{ value: 'PPP-Implied Revenue', position: 'bottom', offset: 20, fill: '#4b5563', fontSize: 10 }}
                      tick={{ fill: '#4b5563', fontSize: 10 }} />
                    <YAxis type="number" dataKey="y" scale="log" domain={['dataMin', 'dataMax']}
                      tickFormatter={fmt}
                      label={{ value: 'SaaSquatch Estimate', angle: -90, position: 'insideLeft', offset: -35, fill: '#4b5563', fontSize: 10 }}
                      tick={{ fill: '#4b5563', fontSize: 10 }} />
                    <Tooltip content={({ payload }) => {
                      if (!payload?.length) return null
                      const d = payload[0].payload
                      return (
                        <div className="bg-[#1a1d2e] border border-[#252840] rounded-lg p-2.5 text-xs shadow-xl">
                          <p className="text-white font-medium mb-1">{d.name}</p>
                          <p className="text-gray-400">PPP: {fmt(d.x)}</p>
                          <p className="text-gray-400">SQ: {fmt(d.y)}</p>
                          <p className="text-gray-500">{d.tier} match</p>
                        </div>
                      )
                    }} />
                    <ReferenceLine
                      segment={[
                        { x: Math.min(...scatterData.map(d => d.x)), y: Math.min(...scatterData.map(d => d.x)) },
                        { x: Math.max(...scatterData.map(d => d.x)), y: Math.max(...scatterData.map(d => d.x)) },
                      ]}
                      stroke="#374151" strokeDasharray="6 4" />
                    <Scatter data={scatterData}>
                      {scatterData.map((e, i) => (
                        <Cell key={i} fill={TIER_COLORS[e.tier] || '#6b7280'} fillOpacity={0.8} />
                      ))}
                    </Scatter>
                  </ScatterChart>
                </ResponsiveContainer>
                <div className="flex gap-4 justify-center mt-2 text-[10px] text-gray-600">
                  {Object.entries(TIER_COLORS).map(([tier, color]) => (
                    <span key={tier} className="flex items-center gap-1.5">
                      <span className="w-2 h-2 rounded-full" style={{ background: color }} /> {tier}
                    </span>
                  ))}
                </div>
              </div>

              {/* Histogram */}
              <div className="bg-[#13151c] border border-[#1e2130] rounded-xl p-5">
                <p className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-4">
                  Estimate Disagreement
                </p>
                <ResponsiveContainer width="100%" height={320}>
                  <BarChart data={histogram} margin={{ top: 10, right: 20, bottom: 40, left: 40 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e2130" />
                    <XAxis dataKey="label" tick={{ fill: '#4b5563', fontSize: 10 }}
                      label={{ value: 'SaaSquatch / PPP ratio', position: 'bottom', offset: 15, fill: '#4b5563', fontSize: 10 }} />
                    <YAxis tick={{ fill: '#4b5563', fontSize: 10 }}
                      label={{ value: 'Leads', angle: -90, position: 'insideLeft', offset: -20, fill: '#4b5563', fontSize: 10 }} />
                    <Tooltip content={({ payload }) => {
                      if (!payload?.length) return null
                      const d = payload[0].payload
                      return (
                        <div className="bg-[#1a1d2e] border border-[#252840] rounded-lg p-2 text-xs shadow-xl">
                          <p className="text-white">{d.label}: {d.count} leads</p>
                        </div>
                      )
                    }} />
                    <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                      {histogram.map((b, i) => (
                        <Cell key={i} fill={b.color} fillOpacity={0.8} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
                <p className="text-[10px] text-gray-600 text-center mt-2">
                  Blue = within 2x agreement. Orange/red = significant disagreement.
                </p>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

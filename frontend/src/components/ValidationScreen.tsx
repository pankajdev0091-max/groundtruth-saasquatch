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
  'High': '#2563eb',
  'Probable': '#0ea5e9',
  'Weak': '#9ca3af',
}

function fmtCurrency(v: number): string {
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`
  if (v >= 1_000) return `$${(v / 1_000).toFixed(0)}K`
  return `$${v.toFixed(0)}`
}

export function ValidationScreen({ results, jobId }: Props) {
  const validPairs = useMemo(() => {
    return results.filter(r =>
      r.saasquatch_revenue != null &&
      r.saasquatch_revenue > 0 &&
      r.revenue_point != null &&
      r.revenue_point > 0 &&
      r.match_tier !== 'No match'
    )
  }, [results])

  const scatterData = useMemo(() => {
    return validPairs.map(r => ({
      x: r.revenue_point!,
      y: r.saasquatch_revenue!,
      name: r.input_name,
      tier: r.match_tier,
    }))
  }, [validPairs])

  const logRatios = useMemo(() => {
    return validPairs.map(r => {
      const ratio = Math.log(r.saasquatch_revenue! / r.revenue_point!)
      return { ratio, name: r.input_name, tier: r.match_tier }
    })
  }, [validPairs])

  const histogram = useMemo(() => {
    const bins = [
      { label: '<0.25x', min: -Infinity, max: Math.log(0.25), count: 0 },
      { label: '0.25-0.5x', min: Math.log(0.25), max: Math.log(0.5), count: 0 },
      { label: '0.5-2x', min: Math.log(0.5), max: Math.log(2), count: 0 },
      { label: '2-4x', min: Math.log(2), max: Math.log(4), count: 0 },
      { label: '>4x', min: Math.log(4), max: Infinity, count: 0 },
    ]
    for (const { ratio } of logRatios) {
      for (const bin of bins) {
        if (ratio >= bin.min && ratio < bin.max) {
          bin.count++
          break
        }
      }
    }
    return bins
  }, [logRatios])

  const offBy2x = logRatios.filter(r => Math.abs(r.ratio) > Math.log(2)).length
  const pctOff = validPairs.length > 0 ? ((offBy2x / validPairs.length) * 100).toFixed(0) : '0'

  if (validPairs.length === 0) {
    return (
      <div className="max-w-2xl mx-auto text-center py-16">
        <h2 className="text-2xl font-semibold text-[var(--text-h)] mb-4">
          Validation
        </h2>
        <p className="text-[var(--text)]">
          No revenue data to compare. The uploaded CSV needs a revenue column
          (e.g., "Estimated Revenue") with parseable values to generate the validation chart.
        </p>
        <p className="text-sm text-[var(--text)] mt-4">
          Supported formats: $1.2M, $1,200,000, 500K, ranges like $1M-$5M
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-semibold text-[var(--text-h)] mb-2">
          Revenue Validation
        </h2>
        <p className="text-[var(--text)] max-w-3xl">
          Comparing SaaSquatch revenue estimates against PPP-implied revenue
          for {validPairs.length} matched leads. Points are colored by match confidence.
        </p>
      </div>

      {/* Headline stat */}
      <div className="bg-[var(--surface)] border border-[var(--border)] rounded-lg p-6">
        <p className="text-lg text-[var(--text-h)]">
          On <span className="font-semibold">{validPairs.length}</span> matched leads,
          the platform's revenue estimate disagreed with the PPP-implied figure by more
          than 2x for <span className="font-semibold">{offBy2x}</span> leads
          (<span className="font-semibold">{pctOff}%</span>).
          {offBy2x > 0 && (
            <> Those {offBy2x} leads represent <span className="font-semibold">{offBy2x} enrichment credits</span> that
            may need verification before spending.</>
          )}
        </p>
      </div>

      {/* Scatter plot */}
      <div className="bg-[var(--surface)] border border-[var(--border)] rounded-lg p-6">
        <h3 className="text-sm font-medium text-[var(--text-h)] uppercase tracking-wider mb-4">
          PPP-Implied vs SaaSquatch Revenue (log-log)
        </h3>
        <ResponsiveContainer width="100%" height={400}>
          <ScatterChart margin={{ top: 20, right: 40, bottom: 40, left: 60 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis
              type="number"
              dataKey="x"
              scale="log"
              domain={['dataMin', 'dataMax']}
              tickFormatter={(v: number) => fmtCurrency(v)}
              label={{ value: 'PPP-Implied Revenue', position: 'bottom', offset: 20, fill: 'var(--text)' }}
              tick={{ fill: 'var(--text)', fontSize: 11 }}
            />
            <YAxis
              type="number"
              dataKey="y"
              scale="log"
              domain={['dataMin', 'dataMax']}
              tickFormatter={(v: number) => fmtCurrency(v)}
              label={{ value: 'SaaSquatch Estimate', angle: -90, position: 'insideLeft', offset: -40, fill: 'var(--text)' }}
              tick={{ fill: 'var(--text)', fontSize: 11 }}
            />
            <Tooltip
              content={({ payload }) => {
                if (!payload?.length) return null
                const d = payload[0].payload
                return (
                  <div className="bg-[var(--surface)] border border-[var(--border)] rounded p-2 text-xs shadow-lg">
                    <p className="font-medium text-[var(--text-h)]">{d.name}</p>
                    <p className="text-[var(--text)]">PPP: {fmtCurrency(d.x)}</p>
                    <p className="text-[var(--text)]">SQ: {fmtCurrency(d.y)}</p>
                    <p className="text-[var(--text)]">Tier: {d.tier}</p>
                  </div>
                )
              }}
            />
            <ReferenceLine
              segment={[
                { x: Math.min(...scatterData.map(d => d.x)), y: Math.min(...scatterData.map(d => d.x)) },
                { x: Math.max(...scatterData.map(d => d.x)), y: Math.max(...scatterData.map(d => d.x)) },
              ]}
              stroke="var(--text)"
              strokeDasharray="6 4"
              strokeOpacity={0.4}
            />
            <Scatter data={scatterData}>
              {scatterData.map((entry, i) => (
                <Cell key={i} fill={TIER_COLORS[entry.tier] || '#9ca3af'} fillOpacity={0.7} />
              ))}
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
        <div className="flex gap-6 justify-center mt-2 text-xs text-[var(--text)]">
          {Object.entries(TIER_COLORS).map(([tier, color]) => (
            <span key={tier} className="flex items-center gap-1.5">
              <span className="inline-block w-3 h-3 rounded-full" style={{ background: color }} />
              {tier}
            </span>
          ))}
          <span className="flex items-center gap-1.5">
            <span className="inline-block w-6 border-t-2 border-dashed border-[var(--text)]" style={{ opacity: 0.4 }} />
            Perfect agreement
          </span>
        </div>
      </div>

      {/* Histogram */}
      <div className="bg-[var(--surface)] border border-[var(--border)] rounded-lg p-6">
        <h3 className="text-sm font-medium text-[var(--text-h)] uppercase tracking-wider mb-4">
          Estimate Disagreement Distribution
        </h3>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={histogram} margin={{ top: 10, right: 30, bottom: 30, left: 40 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
            <XAxis
              dataKey="label"
              tick={{ fill: 'var(--text)', fontSize: 12 }}
              label={{ value: 'SaaSquatch / PPP ratio', position: 'bottom', offset: 10, fill: 'var(--text)' }}
            />
            <YAxis
              tick={{ fill: 'var(--text)', fontSize: 12 }}
              label={{ value: 'Leads', angle: -90, position: 'insideLeft', offset: -20, fill: 'var(--text)' }}
            />
            <Tooltip
              content={({ payload }) => {
                if (!payload?.length) return null
                const d = payload[0].payload
                return (
                  <div className="bg-[var(--surface)] border border-[var(--border)] rounded p-2 text-xs shadow-lg">
                    <p className="text-[var(--text-h)]">{d.label}: {d.count} leads</p>
                  </div>
                )
              }}
            />
            <Bar dataKey="count" fill="var(--accent)" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Export */}
      <div className="flex justify-end">
        <a href={`/api/export/${jobId}.csv`} download
          className="px-4 py-2 text-sm border border-[var(--border)] rounded-md text-[var(--text-h)] hover:bg-[var(--border)] transition-colors">
          Export Annotated CSV
        </a>
      </div>
    </div>
  )
}

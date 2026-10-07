import { useState, useEffect } from 'react'
import { Sidebar } from './components/Sidebar'
import { LeadsView } from './components/LeadsView'
import { ImportModal } from './components/ImportModal'
import { AnalyticsView } from './components/AnalyticsView'

export type View = 'leads' | 'analytics' | 'import'

export interface MatchResult {
  row_index: number
  input_name: string
  input_city: string
  input_state: string
  match_tier: string
  match_confidence: number
  match_reasons: string[]
  matched_name: string
  matched_city: string
  matched_zip: string
  matched_address: string
  naics_code: string
  processing_method: string
  ppp_loan_amount: number
  annual_payroll: number | null
  payroll_formula: string
  revenue_point: number | null
  revenue_low: number | null
  revenue_high: number | null
  revenue_formula: string
  naics_ratio: number | null
  naics_level: number | null
  payroll_proceed_value: number | null
  payroll_proceed_note: string
  headcount: number | null
  business_age: string
  sba_loan_count: number
  sba_total_borrowed: number
  sba_maturing: boolean
  sba_maturing_details: string
  sba_loans: Array<{
    borrower: string
    program: string
    amount: number
    approval_date: string
    term_months: number | null
    lender: string
    status: string
  }>
  franchise_flag: boolean
  franchise_name: string
  change_of_ownership: boolean
  recommendation: string
  recommendation_rule: string
  saasquatch_revenue: number | null
  saasquatch_revenue_raw: string
}

export interface UploadResponse {
  job_id: string
  filename: string
  row_count: number
  headers: string[]
  mapping: Record<string, { source_column: string; mapped_to: string; confidence: string }>
}

function App() {
  const [view, setView] = useState<View>('leads')
  const [showImport, setShowImport] = useState(false)
  const [results, setResults] = useState<MatchResult[]>([])
  const [jobId, setJobId] = useState('')
  const [groundtruthEnabled, setGroundtruthEnabled] = useState(true)

  const hasData = results.length > 0

  useEffect(() => {
    if (!hasData) setShowImport(true)
  }, [])

  return (
    <div className="min-h-screen bg-[#0f1117] text-gray-200 flex">
      <Sidebar
        view={view}
        onViewChange={setView}
        onImport={() => setShowImport(true)}
        hasData={hasData}
        groundtruthEnabled={groundtruthEnabled}
        onToggleGroundtruth={() => setGroundtruthEnabled(!groundtruthEnabled)}
        matchedCount={results.filter(r => r.match_tier !== 'No match').length}
        totalCount={results.length}
      />

      <main className="flex-1 overflow-hidden">
        {view === 'leads' && (
          <LeadsView
            results={results}
            jobId={jobId}
            groundtruthEnabled={groundtruthEnabled}
            onImport={() => setShowImport(true)}
          />
        )}
        {view === 'analytics' && (
          <AnalyticsView results={results} jobId={jobId} />
        )}
      </main>

      {showImport && (
        <ImportModal
          onClose={() => setShowImport(false)}
          onComplete={(matchResults, id) => {
            setResults(matchResults)
            setJobId(id)
            setShowImport(false)
            setView('leads')
          }}
        />
      )}
    </div>
  )
}

export default App

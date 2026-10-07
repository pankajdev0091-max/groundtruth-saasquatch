import { useCallback, useState, useRef } from 'react'
import type { UploadResponse, MatchResult } from '../App'

const API = '/api'

interface Props {
  onUploadComplete: (data: UploadResponse) => void
  onMatchComplete: (results: MatchResult[]) => void
  uploadData: UploadResponse | null
  jobId: string
}

export function UploadScreen({ onUploadComplete, onMatchComplete, uploadData, jobId }: Props) {
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [matching, setMatching] = useState(false)
  const [progress, setProgress] = useState({ completed: 0, total: 0 })
  const [error, setError] = useState('')
  const [mapping, setMapping] = useState<Record<string, string>>({})
  const fileRef = useRef<HTMLInputElement>(null)

  const handleFile = useCallback(async (file: File) => {
    setError('')
    setUploading(true)
    try {
      const form = new FormData()
      form.append('file', file)
      const res = await fetch(`${API}/upload`, { method: 'POST', body: form })
      if (!res.ok) {
        const err = await res.json()
        throw new Error(err.detail || 'Upload failed')
      }
      const data: UploadResponse = await res.json()
      const initialMapping: Record<string, string> = {}
      for (const [field, m] of Object.entries(data.mapping)) {
        initialMapping[field] = m.source_column
      }
      setMapping(initialMapping)
      onUploadComplete(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Upload failed')
    } finally {
      setUploading(false)
    }
  }, [onUploadComplete])

  const handleMatch = useCallback(async () => {
    if (!jobId) return
    setMatching(true)
    setProgress({ completed: 0, total: 0 })
    setError('')

    try {
      const res = await fetch(`${API}/match`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          job_id: jobId,
          mapping: Object.keys(mapping).length > 0 ? mapping : undefined,
        }),
      })
      if (!res.ok) throw new Error('Match request failed')

      const reader = res.body?.getReader()
      if (!reader) throw new Error('No response stream')
      const decoder = new TextDecoder()
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.trim()) continue
          const msg = JSON.parse(line)
          if (msg.type === 'progress') {
            setProgress({ completed: msg.completed, total: msg.total })
          } else if (msg.type === 'done') {
            setProgress({ completed: msg.total, total: msg.total })
          }
        }
      }

      const fullRes = await fetch(`${API}/results/${jobId}`)
      const fullData = await fullRes.json()
      onMatchComplete(fullData.results)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Matching failed')
    } finally {
      setMatching(false)
    }
  }, [jobId, mapping, onMatchComplete])

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }, [handleFile])

  const fieldLabels: Record<string, string> = {
    company_name: 'Company Name',
    city: 'City',
    state: 'State',
    zip: 'Zip Code',
    address: 'Address',
    website: 'Website',
    phone: 'Phone',
    industry: 'Industry',
    estimated_revenue: 'Estimated Revenue',
    employee_count: 'Employee Count',
  }

  return (
    <div className="max-w-3xl mx-auto">
      {/* Step context */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-full bg-[var(--accent)] text-white flex items-center justify-center text-lg font-bold">1</div>
          <div>
            <h2 className="text-2xl font-bold text-[var(--text-h)]">
              Upload & Map Columns
            </h2>
            <p className="text-[var(--text)] text-sm">
              Upload your SaaSquatch CSV export. We'll detect the columns and let you verify before matching.
            </p>
          </div>
        </div>
      </div>

      {!uploadData && (
        <div className="bg-[var(--surface)] border border-[var(--border)] rounded-xl overflow-hidden">
          <div
            onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            onClick={() => fileRef.current?.click()}
            className={`p-16 text-center cursor-pointer transition-all ${
              dragging
                ? 'bg-[var(--accent-light)] border-[var(--accent)]'
                : 'hover:bg-[var(--bg)]'
            }`}
          >
            <input
              ref={fileRef}
              type="file"
              accept=".csv"
              className="hidden"
              onChange={(e) => {
                const file = e.target.files?.[0]
                if (file) handleFile(file)
              }}
            />
            {uploading ? (
              <div className="flex flex-col items-center gap-3">
                <div className="w-10 h-10 border-2 border-[var(--accent)] border-t-transparent rounded-full animate-spin"></div>
                <p className="text-[var(--text)]">Reading CSV...</p>
              </div>
            ) : (
              <>
                <div className="w-16 h-16 rounded-2xl bg-[var(--accent-light)] flex items-center justify-center mx-auto mb-4">
                  <svg className="w-8 h-8 text-[var(--accent)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
                  </svg>
                </div>
                <p className="text-lg font-medium text-[var(--text-h)] mb-1">
                  Drop your SaaSquatch CSV here
                </p>
                <p className="text-sm text-[var(--text)] mb-4">
                  or click to browse
                </p>
                <p className="text-xs text-[var(--text)] opacity-60">
                  Expects columns like Company, City, State, Industry, Estimated Revenue
                </p>
              </>
            )}
          </div>

          <div className="border-t border-[var(--border)] px-6 py-3 bg-[var(--bg)] flex items-center gap-4 text-xs text-[var(--text)]">
            <span>Supported: SaaSquatch CSV export, Apollo export, or any CSV with company name + location</span>
          </div>
        </div>
      )}

      {error && (
        <div className="mt-4 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-300 text-sm flex items-start gap-3">
          <span className="text-red-500 mt-0.5 font-bold">!</span>
          <span>{error}</span>
        </div>
      )}

      {uploadData && !matching && (
        <div className="bg-[var(--surface)] border border-[var(--border)] rounded-xl overflow-hidden">
          {/* File info bar */}
          <div className="px-6 py-4 border-b border-[var(--border)] bg-[var(--bg)] flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-green-100 dark:bg-green-900/30 flex items-center justify-center">
                <svg className="w-4 h-4 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <div>
                <p className="font-medium text-[var(--text-h)] text-sm">{uploadData.filename}</p>
                <p className="text-xs text-[var(--text)]">{uploadData.row_count} leads detected across {uploadData.headers.length} columns</p>
              </div>
            </div>
            <button
              onClick={() => window.location.reload()}
              className="text-xs text-[var(--accent)] hover:underline"
            >
              Change file
            </button>
          </div>

          {/* Column mapping */}
          <div className="p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-sm font-semibold text-[var(--text-h)]">
                  Column Mapping
                </h3>
                <p className="text-xs text-[var(--text)] mt-0.5">
                  We detected these columns automatically. Adjust if needed.
                </p>
              </div>
              <div className="flex items-center gap-2 text-xs text-[var(--text)]">
                <span className="inline-block w-2 h-2 rounded-full bg-green-500"></span> auto-detected
              </div>
            </div>

            <div className="grid gap-2 mb-6">
              {Object.entries(uploadData.mapping).map(([field, m]) => (
                <div key={field} className="flex items-center gap-3 text-sm bg-[var(--bg)] rounded-lg px-3 py-2">
                  <span className="w-36 text-[var(--text)] font-medium text-xs uppercase tracking-wide">
                    {fieldLabels[field] || field}
                  </span>
                  <svg className="w-4 h-4 text-[var(--text)] opacity-40 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
                  </svg>
                  <select
                    value={mapping[field] || m.source_column}
                    onChange={(e) => setMapping({ ...mapping, [field]: e.target.value })}
                    className="flex-1 bg-[var(--surface)] border border-[var(--border)] rounded-md px-2 py-1.5 text-sm text-[var(--text-h)]"
                  >
                    {uploadData.headers.map((h) => (
                      <option key={h} value={h}>{h}</option>
                    ))}
                  </select>
                  <span className={`w-2 h-2 rounded-full shrink-0 ${
                    m.confidence === 'high' ? 'bg-green-500' : m.confidence === 'medium' ? 'bg-yellow-500' : 'bg-gray-400'
                  }`} title={`${m.confidence} confidence`}></span>
                </div>
              ))}
            </div>
          </div>

          {/* Match button */}
          <div className="px-6 py-4 border-t border-[var(--border)] bg-[var(--bg)]">
            <button
              onClick={handleMatch}
              className="w-full py-3 bg-[var(--accent)] text-white rounded-lg font-semibold hover:opacity-90 transition-opacity shadow-lg shadow-blue-500/20 flex items-center justify-center gap-2"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              Match {uploadData.row_count} leads against federal records
            </button>
            <p className="text-xs text-[var(--text)] text-center mt-2 opacity-60">
              Matches against PPP loan data (11.5M businesses) and SBA 7(a)/504 records
            </p>
          </div>
        </div>
      )}

      {matching && (
        <div className="bg-[var(--surface)] border border-[var(--border)] rounded-xl p-8 text-center">
          <div className="w-12 h-12 border-3 border-[var(--accent)] border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-lg font-medium text-[var(--text-h)] mb-1">Matching in progress</p>
          <p className="text-sm text-[var(--text)] mb-6">
            Comparing each lead against PPP and SBA loan records by name, city, and zip code
          </p>
          <div className="max-w-md mx-auto">
            <div className="flex justify-between text-xs text-[var(--text)] mb-1">
              <span>{progress.completed} of {progress.total} leads</span>
              <span>{progress.total > 0 ? Math.round((progress.completed / progress.total) * 100) : 0}%</span>
            </div>
            <div className="w-full bg-[var(--border)] rounded-full h-2.5">
              <div
                className="bg-[var(--accent)] h-2.5 rounded-full transition-all duration-300"
                style={{ width: `${progress.total > 0 ? (progress.completed / progress.total) * 100 : 0}%` }}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

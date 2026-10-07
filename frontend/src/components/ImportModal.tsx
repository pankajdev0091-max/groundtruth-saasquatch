import { useCallback, useState, useRef } from 'react'
import type { UploadResponse, MatchResult } from '../App'

const API = '/api'

interface Props {
  onClose: () => void
  onComplete: (results: MatchResult[], jobId: string) => void
}

type Step = 'upload' | 'map' | 'matching' | 'done'

export function ImportModal({ onClose, onComplete }: Props) {
  const [step, setStep] = useState<Step>('upload')
  const [dragging, setDragging] = useState(false)
  const [uploadData, setUploadData] = useState<UploadResponse | null>(null)
  const [mapping, setMapping] = useState<Record<string, string>>({})
  const [progress, setProgress] = useState({ completed: 0, total: 0 })
  const [error, setError] = useState('')
  const fileRef = useRef<HTMLInputElement>(null)

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

  const handleFile = useCallback(async (file: File) => {
    setError('')
    try {
      const form = new FormData()
      form.append('file', file)
      const res = await fetch(`${API}/upload`, { method: 'POST', body: form })
      if (!res.ok) throw new Error((await res.json()).detail || 'Upload failed')
      const data: UploadResponse = await res.json()
      const m: Record<string, string> = {}
      for (const [f, v] of Object.entries(data.mapping)) m[f] = v.source_column
      setMapping(m)
      setUploadData(data)
      setStep('map')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Upload failed')
    }
  }, [])

  const handleMatch = useCallback(async () => {
    if (!uploadData) return
    setStep('matching')
    setProgress({ completed: 0, total: 0 })
    try {
      const res = await fetch(`${API}/match`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_id: uploadData.job_id, mapping }),
      })
      if (!res.ok) throw new Error('Match failed')
      const reader = res.body?.getReader()
      if (!reader) throw new Error('No stream')
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
          if (msg.type === 'progress') setProgress({ completed: msg.completed, total: msg.total })
          if (msg.type === 'done') setProgress({ completed: msg.total, total: msg.total })
        }
      }
      const fullRes = await fetch(`${API}/results/${uploadData.job_id}`)
      const fullData = await fullRes.json()
      onComplete(fullData.results, uploadData.job_id)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Matching failed')
      setStep('map')
    }
  }, [uploadData, mapping, onComplete])

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0])
  }, [handleFile])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={step !== 'matching' ? onClose : undefined} />
      <div className="relative bg-[#13151c] border border-[#252840] rounded-2xl shadow-2xl w-full max-w-lg mx-4 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#1e2130]">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-blue-500/20 flex items-center justify-center">
              <svg className="w-4 h-4 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
              </svg>
            </div>
            <div>
              <h2 className="text-sm font-semibold text-white">Import Leads</h2>
              <p className="text-xs text-gray-500">
                {step === 'upload' && 'Upload your SaaSquatch CSV export'}
                {step === 'map' && 'Verify column mapping'}
                {step === 'matching' && 'Matching against federal records...'}
              </p>
            </div>
          </div>
          {step !== 'matching' && (
            <button onClick={onClose} className="text-gray-500 hover:text-gray-300 text-lg">&times;</button>
          )}
        </div>

        {/* Body */}
        <div className="px-6 py-5">
          {step === 'upload' && (
            <div
              onDragOver={e => { e.preventDefault(); setDragging(true) }}
              onDragLeave={() => setDragging(false)}
              onDrop={onDrop}
              onClick={() => fileRef.current?.click()}
              className={`border border-dashed rounded-xl p-12 text-center cursor-pointer transition-all ${
                dragging ? 'border-blue-500 bg-blue-500/5' : 'border-[#252840] hover:border-blue-500/50'
              }`}
            >
              <input ref={fileRef} type="file" accept=".csv" className="hidden"
                onChange={e => { if (e.target.files?.[0]) handleFile(e.target.files[0]) }} />
              <svg className="w-10 h-10 text-gray-600 mx-auto mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
              </svg>
              <p className="text-sm text-gray-300 mb-1">Drop your CSV export here</p>
              <p className="text-xs text-gray-600">SaaSquatch export, Apollo export, or any lead CSV</p>
            </div>
          )}

          {step === 'map' && uploadData && (
            <div className="space-y-3">
              <div className="flex items-center gap-2 px-3 py-2 bg-emerald-500/10 border border-emerald-500/20 rounded-lg mb-4">
                <svg className="w-4 h-4 text-emerald-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
                <span className="text-xs text-emerald-300">
                  {uploadData.filename} — {uploadData.row_count} leads detected
                </span>
              </div>

              {Object.entries(uploadData.mapping).map(([field, m]) => (
                <div key={field} className="flex items-center gap-2 text-sm">
                  <span className="w-32 text-xs text-gray-500 uppercase tracking-wide shrink-0">
                    {fieldLabels[field] || field}
                  </span>
                  <svg className="w-3 h-3 text-gray-600 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M13 7l5 5m0 0l-5 5m5-5H6" />
                  </svg>
                  <select
                    value={mapping[field] || m.source_column}
                    onChange={e => setMapping({ ...mapping, [field]: e.target.value })}
                    className="flex-1 bg-[#0f1117] border border-[#252840] rounded-md px-2 py-1.5 text-xs text-gray-300"
                  >
                    {uploadData.headers.map(h => <option key={h} value={h}>{h}</option>)}
                  </select>
                </div>
              ))}
            </div>
          )}

          {step === 'matching' && (
            <div className="text-center py-6">
              <div className="w-10 h-10 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
              <p className="text-sm text-gray-300 mb-1">Matching against PPP & SBA records</p>
              <p className="text-xs text-gray-600 mb-4">Comparing by name, city, zip, and industry</p>
              <div className="max-w-xs mx-auto">
                <div className="flex justify-between text-xs text-gray-500 mb-1">
                  <span>{progress.completed}/{progress.total}</span>
                  <span>{progress.total > 0 ? Math.round((progress.completed / progress.total) * 100) : 0}%</span>
                </div>
                <div className="w-full bg-[#1e2130] rounded-full h-1.5">
                  <div className="bg-blue-500 h-1.5 rounded-full transition-all duration-300"
                    style={{ width: `${progress.total > 0 ? (progress.completed / progress.total) * 100 : 0}%` }} />
                </div>
              </div>
            </div>
          )}

          {error && (
            <p className="text-xs text-red-400 mt-3">{error}</p>
          )}
        </div>

        {/* Footer */}
        {step === 'map' && (
          <div className="px-6 py-4 border-t border-[#1e2130] flex justify-end gap-2">
            <button onClick={onClose}
              className="px-4 py-2 text-xs text-gray-400 hover:text-gray-200 rounded-lg">
              Cancel
            </button>
            <button onClick={handleMatch}
              className="px-5 py-2 text-xs bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-500 transition-colors flex items-center gap-2">
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              Match {uploadData?.row_count} leads
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

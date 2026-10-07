import type { View } from '../App'

interface Props {
  view: View
  onViewChange: (v: View) => void
  onImport: () => void
  hasData: boolean
  groundtruthEnabled: boolean
  onToggleGroundtruth: () => void
  matchedCount: number
  totalCount: number
}

export function Sidebar({
  view, onViewChange, onImport, hasData,
  groundtruthEnabled, onToggleGroundtruth,
  matchedCount, totalCount,
}: Props) {
  return (
    <aside className="w-60 bg-[#13151c] border-r border-[#1e2130] flex flex-col h-screen sticky top-0">
      {/* Brand */}
      <div className="px-4 py-5 border-b border-[#1e2130]">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center shadow-lg shadow-blue-500/20">
            <span className="text-white font-bold text-xs">SQ</span>
          </div>
          <div>
            <span className="text-sm font-semibold text-white tracking-tight">SaaSquatch</span>
            <span className="text-[10px] text-gray-500 block -mt-0.5">Leads Platform</span>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        <p className="text-[10px] uppercase tracking-widest text-gray-600 px-2 mb-2">Workspace</p>

        <button
          onClick={() => onViewChange('leads')}
          className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors ${
            view === 'leads'
              ? 'bg-[#1a1d2e] text-white'
              : 'text-gray-400 hover:text-gray-200 hover:bg-[#1a1d2e]/50'
          }`}
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z" />
          </svg>
          Leads
          {totalCount > 0 && (
            <span className="ml-auto text-xs text-gray-500 font-mono">{totalCount}</span>
          )}
        </button>

        <button
          onClick={() => hasData && onViewChange('analytics')}
          className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors ${
            view === 'analytics'
              ? 'bg-[#1a1d2e] text-white'
              : hasData
              ? 'text-gray-400 hover:text-gray-200 hover:bg-[#1a1d2e]/50'
              : 'text-gray-600 cursor-not-allowed'
          }`}
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
          </svg>
          Revenue Analytics
        </button>

        <button
          onClick={onImport}
          className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-gray-400 hover:text-gray-200 hover:bg-[#1a1d2e]/50 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
          </svg>
          Import CSV
        </button>
      </nav>

      {/* GroundTruth integration panel */}
      <div className="px-3 pb-4">
        <div className="bg-[#1a1d2e] rounded-xl p-3 border border-[#252840]">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <div className="w-5 h-5 rounded bg-emerald-500/20 flex items-center justify-center">
                <span className="text-emerald-400 text-[10px] font-bold">GT</span>
              </div>
              <span className="text-xs font-semibold text-gray-300">GroundTruth</span>
            </div>
            <button
              onClick={onToggleGroundtruth}
              className={`w-9 h-5 rounded-full transition-colors relative ${
                groundtruthEnabled ? 'bg-emerald-500' : 'bg-gray-600'
              }`}
            >
              <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow-sm transition-all duration-200 ${
                groundtruthEnabled ? 'left-[18px]' : 'left-0.5'
              }`} />
            </button>
          </div>

          {hasData ? (
            <div className="space-y-1.5">
              <div className="flex justify-between text-xs">
                <span className="text-gray-500">Matched</span>
                <span className="text-gray-300 font-mono">{matchedCount}/{totalCount}</span>
              </div>
              <div className="w-full bg-[#0f1117] rounded-full h-1.5">
                <div
                  className="bg-emerald-500 h-1.5 rounded-full transition-all"
                  style={{ width: `${totalCount > 0 ? (matchedCount / totalCount) * 100 : 0}%` }}
                />
              </div>
              <p className="text-[10px] text-gray-600">
                PPP + SBA loan records from SBA FOIA
              </p>
            </div>
          ) : (
            <p className="text-[10px] text-gray-600">
              Import leads to match against 11.5M federal loan records
            </p>
          )}
        </div>
      </div>
    </aside>
  )
}

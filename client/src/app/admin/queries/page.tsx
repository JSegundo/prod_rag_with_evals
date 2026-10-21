'use client'

import React, { useState, useEffect } from 'react'
import { Search, ChevronDown, ChevronUp, ThumbsUp, ThumbsDown, AlertCircle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { apiFetch } from '@/lib/api'

interface QueryLog {
  id: number
  documentId: number
  documentName: string | null
  question: string
  answer: string | null
  retrievedDocTitles: string[] | null
  topScore: number | null
  confidence: string | null
  wasRefused: boolean
  helpful: boolean | null
  createdAt: string | null
}

const confidenceBadge: Record<string, { variant: 'default' | 'secondary' | 'destructive'; label: string }> = {
  high: { variant: 'default', label: 'High' },
  medium: { variant: 'secondary', label: 'Medium' },
  low: { variant: 'destructive', label: 'Low' },
}

function formatTime(iso: string | null): string {
  if (!iso) return '-'
  const d = new Date(iso)
  return d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

export default function AdminQueriesPage() {
  const [logs, setLogs] = useState<QueryLog[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [expandedId, setExpandedId] = useState<number | null>(null)

  // Filters
  const [refused, setRefused] = useState(false)
  const [unhelpful, setUnhelpful] = useState(false)
  const [searchText, setSearchText] = useState('')
  const [searchInput, setSearchInput] = useState('')

  const perPage = 20

  useEffect(() => {
    loadLogs()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, refused, unhelpful, searchText])

  async function loadLogs() {
    setLoading(true)
    try {
      const params = new URLSearchParams({ page: String(page), per_page: String(perPage) })
      if (refused) params.set('refused', 'true')
      if (unhelpful) params.set('unhelpful', 'true')
      if (searchText) params.set('search', searchText)

      const data = await apiFetch<{ logs: QueryLog[]; total: number }>(`/api/admin/query-logs?${params}`)
      setLogs(data.logs)
      setTotal(data.total)
    } finally {
      setLoading(false)
    }
  }

  const totalPages = Math.ceil(total / perPage)

  return (
    <div>
      <h2 className="mb-4 text-lg font-semibold">Query Log</h2>

      {/* Filters */}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <form onSubmit={(e) => { e.preventDefault(); setSearchText(searchInput); setPage(1) }} className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Search questions or answers..."
            className="pl-9 h-9 text-sm"
          />
        </form>
        <Button
          variant={refused ? 'default' : 'outline'}
          size="sm"
          onClick={() => { setRefused(!refused); setPage(1) }}
          className="h-9"
        >
          <AlertCircle className="mr-1.5 h-3.5 w-3.5" />
          Refused
        </Button>
        <Button
          variant={unhelpful ? 'default' : 'outline'}
          size="sm"
          onClick={() => { setUnhelpful(!unhelpful); setPage(1) }}
          className="h-9"
        >
          <ThumbsDown className="mr-1.5 h-3.5 w-3.5" />
          Unhelpful
        </Button>
      </div>

      {/* Table */}
      {loading ? (
        <div className="space-y-2">
          {[1, 2, 3, 4, 5].map(i => (
            <div key={i} className="h-12 animate-pulse rounded-lg bg-muted" />
          ))}
        </div>
      ) : logs.length === 0 ? (
        <div className="rounded-lg border border-dashed border-muted-foreground/20 py-12 text-center text-muted-foreground">
          No query logs found.
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/50">
                <th className="px-4 py-2.5 text-left font-medium text-muted-foreground w-8"></th>
                <th className="px-4 py-2.5 text-left font-medium text-muted-foreground">Time</th>
                <th className="px-4 py-2.5 text-left font-medium text-muted-foreground">Document</th>
                <th className="px-4 py-2.5 text-left font-medium text-muted-foreground">Question</th>
                <th className="px-4 py-2.5 text-center font-medium text-muted-foreground">Confidence</th>
                <th className="px-4 py-2.5 text-center font-medium text-muted-foreground">Score</th>
                <th className="px-4 py-2.5 text-center font-medium text-muted-foreground">Refused</th>
                <th className="px-4 py-2.5 text-center font-medium text-muted-foreground">Helpful</th>
              </tr>
            </thead>
            <tbody>
              {logs.map(log => (
                <React.Fragment key={log.id}>
                <tr
                    className="border-b last:border-0 hover:bg-muted/30 transition-colors cursor-pointer"
                    onClick={() => setExpandedId(expandedId === log.id ? null : log.id)}
                  >
                    <td className="px-4 py-3 text-muted-foreground">
                      {expandedId === log.id ? <ChevronUp className="h-3.5 w-3.5" /> : <ChevronDown className="h-3.5 w-3.5" />}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground whitespace-nowrap text-xs">{formatTime(log.createdAt)}</td>
                    <td className="px-4 py-3 text-xs truncate max-w-[120px]">{log.documentName || '-'}</td>
                    <td className="px-4 py-3 truncate max-w-[250px]">{log.question}</td>
                    <td className="px-4 py-3 text-center">
                      {log.confidence && confidenceBadge[log.confidence] ? (
                        <Badge variant={confidenceBadge[log.confidence].variant} className="text-[10px]">
                          {confidenceBadge[log.confidence].label}
                        </Badge>
                      ) : '-'}
                    </td>
                    <td className="px-4 py-3 text-center text-xs text-muted-foreground">
                      {log.topScore !== null ? log.topScore.toFixed(2) : '-'}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {log.wasRefused ? (
                        <Badge variant="destructive" className="text-[10px]">Yes</Badge>
                      ) : (
                        <span className="text-xs text-muted-foreground">No</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {log.helpful === true && <ThumbsUp className="mx-auto h-3.5 w-3.5 text-emerald-500" />}
                      {log.helpful === false && <ThumbsDown className="mx-auto h-3.5 w-3.5 text-red-400" />}
                      {log.helpful === null && <span className="text-xs text-muted-foreground">-</span>}
                    </td>
                  </tr>
                  {expandedId === log.id && (
                    <tr key={`${log.id}-expanded`} className="border-b bg-muted/20">
                      <td colSpan={8} className="px-8 py-4">
                        <div className="space-y-3 text-sm">
                          <div>
                            <p className="text-xs font-medium text-muted-foreground mb-1">Question</p>
                            <p>{log.question}</p>
                          </div>
                          <div>
                            <p className="text-xs font-medium text-muted-foreground mb-1">Answer</p>
                            <p className="whitespace-pre-wrap">{log.answer || 'No answer (refused)'}</p>
                          </div>
                          {log.retrievedDocTitles && log.retrievedDocTitles.length > 0 && (
                            <div>
                              <p className="text-xs font-medium text-muted-foreground mb-1">Retrieved Documents</p>
                              <div className="flex flex-wrap gap-1">
                                {log.retrievedDocTitles.map((title, i) => (
                                  <Badge key={i} variant="secondary" className="text-[10px]">{title}</Badge>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="mt-4 flex items-center justify-between">
          <p className="text-xs text-muted-foreground">{total} total queries</p>
          <div className="flex gap-1">
            <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>
              Previous
            </Button>
            <span className="flex items-center px-3 text-sm text-muted-foreground">
              {page} / {totalPages}
            </span>
            <Button variant="outline" size="sm" disabled={page >= totalPages} onClick={() => setPage(page + 1)}>
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

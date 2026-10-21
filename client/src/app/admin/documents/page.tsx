'use client'

import { useState, useEffect } from 'react'
import { FileText, RefreshCw, CheckCircle, XCircle, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { apiFetch } from '@/lib/api'

interface AdminDocument {
  id: number
  filename: string
  hasFile: boolean
  chunkCount: number
  queryCount: number
  createdAt: string | null
}

interface Stats {
  totalDocuments: number
  totalChunks: number
  totalQueries: number
  refusalRate: number
  avgSimilarity: number
}

function formatDate(iso: string | null): string {
  if (!iso) return '-'
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

export default function AdminDocumentsPage() {
  const [documents, setDocuments] = useState<AdminDocument[]>([])
  const [stats, setStats] = useState<Stats | null>(null)
  const [loading, setLoading] = useState(true)
  const [reindexing, setReindexing] = useState<Set<number>>(new Set())

  useEffect(() => {
    loadData()
  }, [])

  async function loadData() {
    try {
      const [docsRes, statsRes] = await Promise.all([
        apiFetch<{ documents: AdminDocument[] }>('/api/admin/documents'),
        apiFetch<Stats>('/api/admin/stats'),
      ])
      setDocuments(docsRes.documents)
      setStats(statsRes)
    } finally {
      setLoading(false)
    }
  }

  async function handleReindex(docId: number) {
    setReindexing(prev => new Set(prev).add(docId))
    try {
      await apiFetch(`/api/admin/documents/${docId}/reindex`, { method: 'POST' })
      // Reload after a delay to let processing finish
      setTimeout(loadData, 3000)
    } catch (e) {
      console.error('Reindex failed:', e)
    } finally {
      setReindexing(prev => {
        const next = new Set(prev)
        next.delete(docId)
        return next
      })
    }
  }

  async function handleReindexAll() {
    try {
      await apiFetch('/api/admin/documents/reindex-all', { method: 'POST' })
    } catch (e) {
      console.error('Reindex all failed:', e)
    }
  }

  if (loading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="h-16 animate-pulse rounded-lg bg-muted" />
        ))}
      </div>
    )
  }

  return (
    <div>
      {/* Stats cards */}
      {stats && (
        <div className="mb-8 grid grid-cols-2 gap-4 sm:grid-cols-4">
          <StatCard label="Documents" value={stats.totalDocuments} />
          <StatCard label="Total Chunks" value={stats.totalChunks} />
          <StatCard label="Total Queries" value={stats.totalQueries} />
          <StatCard label="Refusal Rate" value={`${(stats.refusalRate * 100).toFixed(1)}%`} />
        </div>
      )}

      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold">Document Index</h2>
        <Button variant="outline" size="sm" onClick={handleReindexAll}>
          <RefreshCw className="mr-1.5 h-3.5 w-3.5" />
          Reindex All
        </Button>
      </div>

      {/* Table */}
      {documents.length === 0 ? (
        <div className="rounded-lg border border-dashed border-muted-foreground/20 py-12 text-center text-muted-foreground">
          No documents uploaded yet.
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/50">
                <th className="px-4 py-2.5 text-left font-medium text-muted-foreground">Filename</th>
                <th className="px-4 py-2.5 text-center font-medium text-muted-foreground">Chunks</th>
                <th className="px-4 py-2.5 text-center font-medium text-muted-foreground">Queries</th>
                <th className="px-4 py-2.5 text-center font-medium text-muted-foreground">Status</th>
                <th className="px-4 py-2.5 text-left font-medium text-muted-foreground">Uploaded</th>
                <th className="px-4 py-2.5 text-right font-medium text-muted-foreground">Actions</th>
              </tr>
            </thead>
            <tbody>
              {documents.map(doc => (
                <tr key={doc.id} className="border-b last:border-0 hover:bg-muted/30 transition-colors">
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <FileText className="h-4 w-4 text-muted-foreground" />
                      <span className="font-medium truncate max-w-[200px]">{doc.filename}</span>
                    </div>
                  </td>
                  <td className="px-4 py-3 text-center">{doc.chunkCount}</td>
                  <td className="px-4 py-3 text-center">{doc.queryCount}</td>
                  <td className="px-4 py-3 text-center">
                    {doc.hasFile ? (
                      <CheckCircle className="mx-auto h-4 w-4 text-emerald-500" />
                    ) : (
                      <XCircle className="mx-auto h-4 w-4 text-red-400" />
                    )}
                  </td>
                  <td className="px-4 py-3 text-muted-foreground">{formatDate(doc.createdAt)}</td>
                  <td className="px-4 py-3 text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      disabled={!doc.hasFile || reindexing.has(doc.id)}
                      onClick={() => handleReindex(doc.id)}
                      className="h-7 text-xs"
                    >
                      {reindexing.has(doc.id) ? (
                        <Loader2 className="mr-1 h-3 w-3 animate-spin" />
                      ) : (
                        <RefreshCw className="mr-1 h-3 w-3" />
                      )}
                      Reindex
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function StatCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg border border-border bg-card p-4">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-2xl font-semibold">{value}</p>
    </div>
  )
}

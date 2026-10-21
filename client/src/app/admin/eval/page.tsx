'use client'

import { useState, useEffect } from 'react'
import { BarChart3, Target, ShieldCheck, MessageSquareWarning } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { apiFetch } from '@/lib/api'

interface EvalRun {
  id: number
  totalQuestions: number
  avgFaithfulness: number | null
  avgRelevance: number | null
  avgRetrievalPrecision: number | null
  refusalRate: number | null
  regressionDetected: boolean
  completedAt: string | null
}

interface EvalResult {
  questionId: string
  question: string
  expectedDocTitle: string | null
  actualAnswer: string | null
  retrievalHit: boolean | null
  wasRefused: boolean
}

function formatPct(v: number | null): string {
  return v === null ? '--' : `${(v * 100).toFixed(0)}%`
}

// Same coloring idea the original spec used for faithfulness, applied to all
// four metrics -- green/yellow/red bands, not a separate threshold per metric.
function colorFor(v: number | null): string {
  if (v === null) return 'text-muted-foreground/30'
  if (v >= 0.85) return 'text-emerald-500'
  if (v >= 0.70) return 'text-amber-500'
  return 'text-red-500'
}

function formatTime(iso: string | null): string {
  if (!iso) return '-'
  return new Date(iso).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

export default function AdminEvalPage() {
  const [run, setRun] = useState<EvalRun | null>(null)
  const [results, setResults] = useState<EvalResult[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    apiFetch<{ run: EvalRun | null; results: EvalResult[] }>('/api/admin/eval/latest')
      .then(data => {
        setRun(data.run)
        setResults(data.results)
      })
      .finally(() => setLoading(false))
  }, [])

  const cards = [
    { label: 'Retrieval Precision', icon: Target, description: 'Did the system find the right documents?', value: run?.avgRetrievalPrecision ?? null },
    { label: 'Faithfulness Score', icon: ShieldCheck, description: 'Are answers faithful to the context?', value: run?.avgFaithfulness ?? null },
    { label: 'Answer Relevance', icon: BarChart3, description: 'Do answers actually address the question?', value: run?.avgRelevance ?? null },
    { label: 'Refusal Rate', icon: MessageSquareWarning, description: 'How often does the system refuse to answer?', value: run?.refusalRate ?? null },
  ]

  const unanswered = results.filter(r => r.wasRefused)

  return (
    <div>
      <div className="mb-2 flex items-center gap-3">
        <h2 className="text-lg font-semibold">Eval Dashboard</h2>
        {run?.regressionDetected && <Badge variant="destructive">Regression detected</Badge>}
      </div>

      <p className="mb-6 text-sm text-muted-foreground max-w-2xl">
        {run
          ? `Latest run: #${run.id} • ${run.totalQuestions} questions • ${formatTime(run.completedAt)}`
          : 'No eval run yet.'}
        {' '}Read-only for now -- trigger a new run with{' '}
        <code className="rounded bg-muted px-1 py-0.5 text-xs">eval/run_generation_eval.py</code>, then refresh.
      </p>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        {cards.map(card => (
          <div key={card.label} className="rounded-lg border border-border bg-card p-4">
            <card.icon className="h-5 w-5 text-muted-foreground/50" />
            <p className="mt-2 text-sm font-medium text-muted-foreground">{card.label}</p>
            <p className="mt-0.5 text-xs text-muted-foreground/60">{card.description}</p>
            <p className={`mt-3 text-2xl font-semibold ${colorFor(card.value)}`}>{formatPct(card.value)}</p>
          </div>
        ))}
      </div>

      <div className="mt-8">
        <h3 className="mb-3 text-sm font-semibold">Unanswered Questions</h3>
        {loading ? (
          <div className="h-12 animate-pulse rounded-lg bg-muted" />
        ) : unanswered.length === 0 ? (
          <div className="rounded-lg border border-dashed border-muted-foreground/20 py-8 text-center text-sm text-muted-foreground">
            No refused questions in the latest run.
          </div>
        ) : (
          <div className="overflow-hidden rounded-lg border border-border">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-muted/50">
                  <th className="px-4 py-2.5 text-left font-medium text-muted-foreground">Question</th>
                  <th className="px-4 py-2.5 text-left font-medium text-muted-foreground">Expected Doc</th>
                </tr>
              </thead>
              <tbody>
                {unanswered.map(r => (
                  <tr key={r.questionId} className="border-b last:border-0">
                    <td className="px-4 py-3">{r.question}</td>
                    <td className="px-4 py-3 text-xs text-muted-foreground">{r.expectedDocTitle}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

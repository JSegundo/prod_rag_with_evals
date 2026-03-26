'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { FileText, MessageSquare, Share2, Clock } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

interface Document {
  id: number
  filename: string
  shareToken: string
  chunkCount: number
  created_at: string | null
}

function formatDate(iso: string | null): string {
  if (!iso) return ''
  const date = new Date(iso)
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(true)
  const [copied, setCopied] = useState<string | null>(null)

  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
    fetch(`${apiUrl}/api/documents`, { credentials: 'include' })
      .then(res => res.json())
      .then(data => setDocuments(data.documents || []))
      .finally(() => setLoading(false))
  }, [])

  const copyShareLink = (shareToken: string) => {
    const url = `${window.location.origin}/chat/${shareToken}`
    navigator.clipboard.writeText(url)
    setCopied(shareToken)
    setTimeout(() => setCopied(null), 2000)
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-3xl px-6 py-16">
        <div className="space-y-4">
          {[1, 2, 3].map(i => (
            <div key={i} className="h-20 animate-pulse rounded-xl bg-muted" />
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-3xl px-6 py-16">
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight text-foreground">Your Documents</h1>
        <p className="mt-1.5 text-muted-foreground">
          Select a document to chat with, or upload a new one.
        </p>
      </div>

      {documents.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-muted-foreground/20 py-16">
          <FileText className="h-10 w-10 text-muted-foreground" />
          <p className="mt-3 text-muted-foreground">No documents uploaded yet.</p>
          <Link href="/">
            <Button className="mt-4">Upload a PDF</Button>
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {documents.map(doc => (
            <div
              key={doc.id}
              className="group flex items-center justify-between rounded-xl border border-border bg-card p-4 transition-colors hover:bg-muted/50"
            >
              <Link href={`/chat/${doc.shareToken}`} className="flex min-w-0 flex-1 items-center gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                  <FileText className="h-5 w-5 text-primary" />
                </div>
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-foreground">{doc.filename}</p>
                  <div className="flex items-center gap-3 text-xs text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {formatDate(doc.created_at)}
                    </span>
                    <Badge variant="secondary" className="text-[10px] px-1.5 py-0">
                      {doc.chunkCount} chunks
                    </Badge>
                  </div>
                </div>
              </Link>

              <div className="flex items-center gap-1.5">
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-8 w-8 text-muted-foreground"
                  onClick={() => copyShareLink(doc.shareToken)}
                  title="Copy share link"
                >
                  <Share2 className="h-3.5 w-3.5" />
                </Button>
                {copied === doc.shareToken && (
                  <span className="text-xs text-primary">Copied!</span>
                )}
                <Link href={`/chat/${doc.shareToken}`}>
                  <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground">
                    <MessageSquare className="h-3.5 w-3.5" />
                  </Button>
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

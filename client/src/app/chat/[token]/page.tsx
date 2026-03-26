'use client'

import { useState, useRef, useEffect, use } from 'react'
import { MessageSquare, FileText } from 'lucide-react'
import ChatMessage from '../../components/ChatMessage'
import ChatInput from '../../components/ChatInput'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'

interface Message {
  role: 'user' | 'assistant'
  content: string
  timestamp?: number
}

interface DocumentInfo {
  id: number
  filename: string
  shareToken: string
  chunkCount: number
}

const SUGGESTED_PROMPTS = [
  "What is this document about?",
  "Summarize the key points",
  "What are the main conclusions?",
]

export default function DocumentChatPage({ params }: { params: Promise<{ token: string }> }) {
  const { token } = use(params)
  const [document, setDocument] = useState<DocumentInfo | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)
  const [docLoading, setDocLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Load document info and chat history
  useEffect(() => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

    async function loadDocument() {
      try {
        const res = await fetch(`${apiUrl}/api/documents/${token}`, { credentials: 'include' })
        if (!res.ok) throw new Error('Document not found')
        const doc = await res.json()
        setDocument(doc)

        // Load chat history
        const historyRes = await fetch(`${apiUrl}/api/chat/history/${doc.id}`, { credentials: 'include' })
        if (historyRes.ok) {
          const data = await historyRes.json()
          setMessages(data.history || [])
        }
      } catch {
        setError('Document not found or has been removed.')
      } finally {
        setDocLoading(false)
      }
    }

    loadDocument()
  }, [token])

  const sendMessage = async (text: string) => {
    if (!document) return
    setMessages(prev => [...prev, { role: 'user', content: text, timestamp: Date.now() }])
    setLoading(true)

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/chat/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          message: text,
          documentId: document.id,
        })
      })

      if (!response.ok) throw new Error('Failed to send message')

      const data = await response.json()
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.message,
        timestamp: data.timestamp
      }])
    } catch {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.'
      }])
    } finally {
      setLoading(false)
    }
  }

  if (docLoading) {
    return (
      <div className="flex items-center justify-center" style={{ height: 'calc(100vh - 3.5rem)' }}>
        <div className="space-y-3 text-center">
          <Skeleton className="mx-auto h-10 w-10 rounded-xl" />
          <Skeleton className="h-4 w-48" />
        </div>
      </div>
    )
  }

  if (error || !document) {
    return (
      <div className="flex items-center justify-center" style={{ height: 'calc(100vh - 3.5rem)' }}>
        <div className="text-center">
          <FileText className="mx-auto h-10 w-10 text-muted-foreground" />
          <p className="mt-3 text-muted-foreground">{error || 'Document not found'}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col" style={{ height: 'calc(100vh - 3.5rem)' }}>
      {/* Document header */}
      <div className="border-b border-border px-6 py-2.5">
        <div className="mx-auto flex max-w-3xl items-center gap-2">
          <FileText className="h-4 w-4 text-muted-foreground" />
          <span className="text-sm font-medium text-foreground truncate">{document.filename}</span>
          <Badge variant="secondary" className="text-xs">{document.chunkCount} chunks</Badge>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-3xl px-6 py-6">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center pt-20">
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10">
                <MessageSquare className="h-7 w-7 text-primary" />
              </div>
              <h2 className="mt-4 text-xl font-semibold text-foreground">
                Chat with {document.filename}
              </h2>
              <p className="mt-1.5 text-sm text-muted-foreground">
                Ask questions about this document.
              </p>
              <div className="mt-6 flex flex-wrap justify-center gap-2">
                {SUGGESTED_PROMPTS.map((prompt) => (
                  <button
                    key={prompt}
                    onClick={() => sendMessage(prompt)}
                    className="rounded-full border border-border px-4 py-2 text-sm text-muted-foreground transition-colors hover:border-primary/30 hover:bg-primary/5 hover:text-foreground"
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="space-y-1">
              {messages.map((msg, i) => (
                <ChatMessage key={i} message={msg} />
              ))}
              {loading && (
                <div className="flex gap-3 py-4">
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-muted">
                    <MessageSquare className="h-4 w-4 text-muted-foreground" />
                  </div>
                  <div className="space-y-2 pt-1">
                    <Skeleton className="h-4 w-48" />
                    <Skeleton className="h-4 w-72" />
                    <Skeleton className="h-4 w-36" />
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>
      </div>

      <ChatInput onSend={sendMessage} disabled={loading} />
    </div>
  )
}

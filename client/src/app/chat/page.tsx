'use client'

import { useState, useRef, useEffect } from 'react'
import { MessageSquare } from 'lucide-react'
import ChatMessage from '../components/ChatMessage'
import type { Message } from '../components/ChatMessage'
import ChatInput from '../components/ChatInput'
import { Skeleton } from '@/components/ui/skeleton'
import { apiFetch } from '@/lib/api'

const SUGGESTED_PROMPTS = [
  "What is this document about?",
  "Summarize the key points",
  "What are the main conclusions?",
]

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)
  const [historyLoading, setHistoryLoading] = useState(true)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Load this session's chat history (one global conversation, not per document)
  useEffect(() => {
    async function loadHistory() {
      try {
        const data = await apiFetch<{ history: Message[] }>('/api/chat/history')
        setMessages(data.history || [])
      } catch {
        // No history yet (or first-ever session) -- start with an empty chat
      } finally {
        setHistoryLoading(false)
      }
    }
    loadHistory()
  }, [])

  const sendMessage = async (text: string) => {
    setMessages(prev => [...prev, { role: 'user', content: text, timestamp: Date.now() }])
    setLoading(true)

    try {
      const data = await apiFetch<Message & { message: string }>('/api/chat/chat', {
        method: 'POST',
        body: JSON.stringify({ message: text }),
      })

      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.message,
        timestamp: data.timestamp,
        citations: data.citations,
        confidence: data.confidence,
        topScore: data.topScore,
        wasRefused: data.wasRefused,
        queryLogId: data.queryLogId,
      }])
    } catch {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
      }])
    } finally {
      setLoading(false)
    }
  }

  const handleFeedback = async (queryLogId: number, helpful: boolean) => {
    try {
      await apiFetch(`/api/chat/feedback/${queryLogId}`, {
        method: 'PATCH',
        body: JSON.stringify({ helpful }),
      })
    } catch (e) {
      console.error('Feedback submission failed:', e)
    }
  }

  if (historyLoading) {
    return (
      <div className="flex items-center justify-center" style={{ height: 'calc(100vh - 3.5rem)' }}>
        <div className="space-y-3 text-center">
          <Skeleton className="mx-auto h-10 w-10 rounded-xl" />
          <Skeleton className="h-4 w-48" />
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col" style={{ height: 'calc(100vh - 3.5rem)' }}>
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-3xl px-6 py-6">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center pt-20">
              <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10">
                <MessageSquare className="h-7 w-7 text-primary" />
              </div>
              <h2 className="mt-4 text-xl font-semibold text-foreground">
                Ask anything about your documents
              </h2>
              <p className="mt-1.5 text-sm text-muted-foreground">
                Searches across every uploaded document, not just one.
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
                <ChatMessage key={i} message={msg} onFeedback={handleFeedback} />
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

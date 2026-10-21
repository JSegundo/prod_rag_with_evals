'use client'

import { useState } from 'react'
import { Bot, User, ThumbsUp, ThumbsDown, FileText } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { Badge } from '@/components/ui/badge'

export interface Citation {
  sourceIndex: number
  docTitle: string
  pageNumbers: number[]
  sectionHeader: string | null
  score: number
}

export interface Message {
  role: 'user' | 'assistant'
  content: string
  timestamp?: number
  citations?: Citation[]
  confidence?: 'high' | 'medium' | 'low'
  topScore?: number
  wasRefused?: boolean
  queryLogId?: number
}

interface ChatMessageProps {
  message: Message
  onFeedback?: (queryLogId: number, helpful: boolean) => void
}

const confidenceColor = {
  high: 'bg-emerald-500',
  medium: 'bg-amber-500',
  low: 'bg-red-500',
}

function formatTime(timestamp?: number): string {
  if (!timestamp) return ''
  return new Date(timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function formatPages(pages: number[]): string {
  if (!pages.length) return ''
  return `p.${pages.join(', ')}`
}

function stripSourceRefs(content: string): string {
  return content.replace(/\s*\[Source\s+\d+\]/g, '').replace(/\n{3,}/g, '\n\n')
}

export default function ChatMessage({ message, onFeedback }: ChatMessageProps) {
  const isUser = message.role === 'user'
  const [feedbackGiven, setFeedbackGiven] = useState<boolean | null>(null)

  const handleFeedback = (helpful: boolean) => {
    if (feedbackGiven !== null || !message.queryLogId || !onFeedback) return
    setFeedbackGiven(helpful)
    onFeedback(message.queryLogId, helpful)
  }

  return (
    <div className={`flex gap-3 py-4 ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div className="relative flex h-8 w-8 shrink-0 items-center justify-center rounded-full" style={{
        backgroundColor: isUser ? 'hsl(var(--primary))' : 'hsl(var(--muted))',
        color: isUser ? 'hsl(var(--primary-foreground))' : 'hsl(var(--muted-foreground))',
      }}>
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
        {/* Confidence dot */}
        {!isUser && message.confidence && (
          <span className={`absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full border-2 border-background ${confidenceColor[message.confidence]}`} />
        )}
      </div>

      {/* Content */}
      <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} max-w-[80%]`}>
        {/* Refusal badge */}
        {message.wasRefused && (
          <Badge variant="outline" className="mb-1 border-amber-300 text-amber-600 text-[10px]">
            Low confidence
          </Badge>
        )}

        {/* Message bubble */}
        <div className={`rounded-2xl px-4 py-2.5 ${
          isUser
            ? 'bg-primary text-primary-foreground rounded-br-md'
            : message.wasRefused
              ? 'border border-amber-300 bg-amber-50/50 rounded-bl-md'
              : 'bg-card border border-border rounded-bl-md'
        }`}>
          {isUser ? (
            <p className="whitespace-pre-wrap text-sm leading-relaxed">{message.content}</p>
          ) : (
            <div className="prose prose-sm prose-neutral max-w-none text-sm leading-relaxed [&_p]:mb-2 [&_p:last-child]:mb-0 [&_ul]:my-1 [&_ol]:my-1 [&_li]:my-0.5 [&_strong]:font-semibold [&_code]:rounded [&_code]:bg-muted [&_code]:px-1 [&_code]:py-0.5 [&_code]:text-xs [&_pre]:rounded-lg [&_pre]:bg-muted [&_pre]:p-3">
              <ReactMarkdown>{stripSourceRefs(message.content)}</ReactMarkdown>
            </div>
          )}
        </div>

        {/* Citations */}
        {!isUser && message.citations && message.citations.length > 0 && (
          <div className="mt-1.5 flex flex-wrap gap-1">
            {message.citations.map((citation) => (
              <Badge
                key={citation.sourceIndex}
                variant="secondary"
                className="gap-1 text-[10px] font-normal px-2 py-0.5"
              >
                <FileText className="h-2.5 w-2.5" />
                {citation.docTitle}
                {citation.pageNumbers.length > 0 && `, ${formatPages(citation.pageNumbers)}`}
              </Badge>
            ))}
          </div>
        )}

        {/* Footer: feedback + timestamp */}
        <div className={`mt-1 flex items-center gap-2 px-1 ${isUser ? 'flex-row-reverse' : ''}`}>
          {/* Feedback buttons (assistant only, not for refusals) */}
          {!isUser && message.queryLogId && !message.wasRefused && (
            <div className="flex items-center gap-0.5">
              <button
                onClick={() => handleFeedback(true)}
                disabled={feedbackGiven !== null}
                className={`rounded p-1 transition-colors ${
                  feedbackGiven === true
                    ? 'text-emerald-600'
                    : feedbackGiven !== null
                      ? 'text-muted-foreground/30 cursor-default'
                      : 'text-muted-foreground/50 hover:text-emerald-600'
                }`}
              >
                <ThumbsUp className="h-3 w-3" />
              </button>
              <button
                onClick={() => handleFeedback(false)}
                disabled={feedbackGiven !== null}
                className={`rounded p-1 transition-colors ${
                  feedbackGiven === false
                    ? 'text-red-500'
                    : feedbackGiven !== null
                      ? 'text-muted-foreground/30 cursor-default'
                      : 'text-muted-foreground/50 hover:text-red-500'
                }`}
              >
                <ThumbsDown className="h-3 w-3" />
              </button>
            </div>
          )}

          {message.timestamp && (
            <span className="text-[11px] text-muted-foreground/60">
              {formatTime(message.timestamp)}
            </span>
          )}
        </div>
      </div>
    </div>
  )
}

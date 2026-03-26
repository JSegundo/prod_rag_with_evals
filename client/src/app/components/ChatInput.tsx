'use client'

import { useState, useRef, useEffect, KeyboardEvent } from 'react'
import { ArrowUp } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface ChatInputProps {
  onSend: (message: string) => void
  disabled?: boolean
}

export default function ChatInput({ onSend, disabled }: ChatInputProps) {
  const [input, setInput] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current
    if (el) {
      el.style.height = 'auto'
      el.style.height = Math.min(el.scrollHeight, 160) + 'px'
    }
  }, [input])

  const handleSend = () => {
    if (input.trim() && !disabled) {
      onSend(input.trim())
      setInput('')
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const hasInput = input.trim().length > 0

  return (
    <div className="border-t border-border bg-background px-6 py-4">
      <div className="mx-auto flex max-w-3xl items-end gap-2">
        <div className="relative flex-1">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            placeholder="Ask a question about your documents..."
            className="w-full resize-none rounded-xl border border-border bg-muted/50 px-4 py-3 pr-12 text-sm leading-relaxed text-foreground placeholder:text-muted-foreground/60 focus:border-primary/30 focus:bg-background focus:outline-none focus:ring-1 focus:ring-primary/20 disabled:opacity-50"
            rows={1}
          />
        </div>
        <Button
          onClick={handleSend}
          disabled={disabled || !hasInput}
          size="icon"
          className={`h-10 w-10 shrink-0 rounded-xl transition-all ${
            hasInput
              ? 'bg-primary text-primary-foreground shadow-sm hover:bg-primary/90'
              : 'bg-muted text-muted-foreground hover:bg-muted'
          }`}
        >
          <ArrowUp className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}

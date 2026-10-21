'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { FileText, List, BarChart3 } from 'lucide-react'
import { cn } from '@/lib/utils'

const tabs = [
  { href: '/admin/documents', label: 'Documents', icon: FileText },
  { href: '/admin/queries', label: 'Query Log', icon: List },
  { href: '/admin/eval', label: 'Eval Dashboard', icon: BarChart3 },
]

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()

  return (
    <div>
      <div className="border-b border-border">
        <div className="mx-auto flex max-w-5xl gap-1 px-6">
          {tabs.map((tab) => {
            const isActive = pathname.startsWith(tab.href)
            return (
              <Link
                key={tab.href}
                href={tab.href}
                className={cn(
                  'flex items-center gap-1.5 border-b-2 px-4 py-2.5 text-sm font-medium transition-colors',
                  isActive
                    ? 'border-primary text-primary'
                    : 'border-transparent text-muted-foreground hover:text-foreground'
                )}
              >
                <tab.icon className="h-3.5 w-3.5" />
                {tab.label}
              </Link>
            )
          })}
        </div>
      </div>
      <div className="mx-auto max-w-5xl px-6 py-8">{children}</div>
    </div>
  )
}

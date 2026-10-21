import "./globals.css"
import { Inter } from "next/font/google"
import type React from "react"
import Link from "next/link"
import { FileText, FolderOpen, MessageSquare, Shield, Upload } from "lucide-react"

const inter = Inter({ subsets: ["latin"] })

export const metadata = {
  title: "DocChat — AI Document Assistant",
  description: "Upload PDFs and chat with your documents using AI-powered retrieval",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={`${inter.className} min-h-screen bg-background`}>
        <nav className="sticky top-0 z-50 border-b border-border/40 bg-background/80 backdrop-blur-lg">
          <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-6">
            <Link href="/" className="flex items-center gap-2 font-semibold text-foreground">
              <FileText className="h-5 w-5 text-primary" />
              DocChat
            </Link>
            <div className="flex items-center gap-1">
              <Link
                href="/"
                className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
              >
                <Upload className="h-3.5 w-3.5" />
                Upload
              </Link>
              <Link
                href="/chat"
                className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
              >
                <MessageSquare className="h-3.5 w-3.5" />
                Chat
              </Link>
              <Link
                href="/documents"
                className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
              >
                <FolderOpen className="h-3.5 w-3.5" />
                Documents
              </Link>
              <Link
                href="/admin"
                className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
              >
                <Shield className="h-3.5 w-3.5" />
                Admin
              </Link>
            </div>
          </div>
        </nav>
        <main>{children}</main>
      </body>
    </html>
  )
}

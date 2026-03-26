'use client'
import { Search, Zap, Shield } from "lucide-react"
import PDFDropzone from "./components/PDFDropzone"
import { Badge } from "@/components/ui/badge"

export default function Home() {
  return (
    <div className="flex flex-col items-center px-6 py-16">
      <div className="mb-10 text-center">
        <h1 className="text-4xl font-bold tracking-tight text-foreground sm:text-5xl">
          Upload & Chat with your PDFs
        </h1>
        <p className="mt-3 text-lg text-muted-foreground">
          AI-powered document analysis. Upload a PDF and start asking questions instantly.
        </p>
      </div>

      <PDFDropzone />

      <div className="mt-12 flex flex-wrap justify-center gap-3">
        <Badge variant="secondary" className="gap-1.5 px-3 py-1.5 text-sm font-normal">
          <Search className="h-3.5 w-3.5" />
          Semantic Search
        </Badge>
        <Badge variant="secondary" className="gap-1.5 px-3 py-1.5 text-sm font-normal">
          <Zap className="h-3.5 w-3.5" />
          Instant Answers
        </Badge>
        <Badge variant="secondary" className="gap-1.5 px-3 py-1.5 text-sm font-normal">
          <Shield className="h-3.5 w-3.5" />
          Secure Processing
        </Badge>
      </div>
    </div>
  )
}

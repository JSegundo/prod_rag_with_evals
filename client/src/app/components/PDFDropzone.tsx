"use client"

import { useCallback, useState } from "react"
import { useRouter } from "next/navigation"
import { useDropzone } from "react-dropzone"
import { FileText, UploadCloud, X, AlertCircle, Loader2 } from "lucide-react"
import React from "react"
import { validatePDF } from "../utils/pdfUtils"
import { ProcessingStatus } from './ProcessingStatus'
import { Button } from "@/components/ui/button"

interface UploadResponse {
  jobId: string;
  message: string;
  originalName: string;
}

enum DocumentPageState {
  UPLOAD,
  PROCESSING,
  CHAT
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

export default function PDFDropzone() {
  const router = useRouter()
  const [pageState, setPageState] = useState<DocumentPageState>(DocumentPageState.UPLOAD)
  const [file, setFile] = useState<File | null>(null)
  const [error, setError] = useState<string | null>("")
  const [isUploading, setIsUploading] = useState(false)
  const [jobId, setJobId] = useState<string | null>(null)

  const handleUploadSuccess = (newFileId: string) => {
    setJobId(newFileId)
    setPageState(DocumentPageState.PROCESSING)
  }

  const handleProcessingComplete = (shareToken: string) => {
    router.push(`/chat/${shareToken}`)
  }

  const handleProcessingFailed = (errorMessage: string) => {
    setError(errorMessage)
    setPageState(DocumentPageState.UPLOAD)
  }

  const resetPage = () => {
    setJobId(null)
    setFile(null)
    setError(null)
    setPageState(DocumentPageState.UPLOAD)
  }

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    const selectedFile = acceptedFiles[0]
    if (!selectedFile) return

    setError("")
    setFile(null)
    setJobId(null)

    const validationResult = await validatePDF(selectedFile, {
      maxSizeInMB: 30,
      maxWordCount: 1
    })

    if (validationResult.isValid) {
      setFile(selectedFile)
    } else {
      setError(validationResult.error || "Invalid PDF file")
    }
  }, [])

  const uploadFile = async () => {
    if (!file) return

    setIsUploading(true)
    setError("")

    try {
      const formData = new FormData()
      formData.append('file', file)

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      const response = await fetch(`${apiUrl}/api/document/upload`, {
        method: 'POST',
        body: formData,
        credentials: 'include',
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.message || 'Upload failed')
      }

      const data: UploadResponse = await response.json()
      setJobId(data.jobId)
      handleUploadSuccess(data.jobId)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to upload file')
    } finally {
      setIsUploading(false)
    }
  }

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "application/pdf": [".pdf"] },
    multiple: false,
  })

  if (pageState === DocumentPageState.PROCESSING && jobId) {
    return (
      <div className="w-full max-w-lg">
        <ProcessingStatus
          fileId={jobId}
          onProcessingComplete={handleProcessingComplete}
          onProcessingFailed={handleProcessingFailed}
        />
      </div>
    )
  }

  return (
    <div className="w-full max-w-lg">
      <div
        {...getRootProps()}
        className={`group flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-10 transition-all duration-200 cursor-pointer ${
          isDragActive
            ? "border-primary bg-primary/5 scale-[1.02]"
            : "border-muted-foreground/20 bg-card hover:border-muted-foreground/40 hover:bg-muted/50"
        }`}
      >
        <input {...getInputProps()} />
        {file ? (
          <div className="flex flex-col items-center gap-3">
            <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-primary/10">
              <FileText className="h-7 w-7 text-primary" />
            </div>
            <div className="text-center">
              <p className="text-sm font-medium text-foreground">{file.name}</p>
              <p className="text-xs text-muted-foreground">{formatFileSize(file.size)}</p>
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-3">
            <div className={`flex h-14 w-14 items-center justify-center rounded-xl transition-colors ${
              isDragActive ? "bg-primary/10" : "bg-muted"
            }`}>
              <UploadCloud className={`h-7 w-7 transition-colors ${
                isDragActive ? "text-primary" : "text-muted-foreground"
              }`} />
            </div>
            <div className="text-center">
              <p className="text-sm font-medium text-foreground">
                {isDragActive ? "Drop your PDF here" : "Drag & drop a PDF"}
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                or click to browse (max 30 MB)
              </p>
            </div>
          </div>
        )}
      </div>

      {file && (
        <div className="mt-4 flex gap-2">
          <Button
            variant="outline"
            className="flex-1"
            onClick={(e) => {
              e.stopPropagation()
              resetPage()
            }}
          >
            <X className="mr-1.5 h-3.5 w-3.5" />
            Clear
          </Button>
          <Button
            className="flex-1"
            onClick={uploadFile}
            disabled={isUploading}
          >
            {isUploading ? (
              <>
                <Loader2 className="mr-1.5 h-3.5 w-3.5 animate-spin" />
                Uploading...
              </>
            ) : (
              <>
                <UploadCloud className="mr-1.5 h-3.5 w-3.5" />
                Upload PDF
              </>
            )}
          </Button>
        </div>
      )}

      {error && (
        <div className="mt-4 flex items-start gap-2 rounded-lg border border-destructive/20 bg-destructive/5 p-3">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" />
          <div className="flex-1">
            <p className="text-sm text-destructive">{error}</p>
            <Button
              variant="ghost"
              size="sm"
              className="mt-1.5 h-7 px-2 text-xs text-destructive hover:text-destructive"
              onClick={resetPage}
            >
              Try again
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}

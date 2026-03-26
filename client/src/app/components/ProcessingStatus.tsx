import React, { useState, useEffect } from 'react';
import { CheckCircle2, Loader2 } from "lucide-react";
import { Card, CardContent } from "@/app/components/ui/card";
import { cn } from "@/lib/utils";

interface ProcessingStatusProps {
  fileId: string;
  onProcessingComplete: () => void;
  onProcessingFailed: (error: string) => void;
}

// Define the processing stages
interface ProcessingStage {
  id: string;
  label: string;
  description: string;
}

const STAGES: ProcessingStage[] = [
  {
    id: "started",
    label: "Processing Started",
    description: "Initializing document processing pipeline"
  },
  {
    id: "extracting",
    label: "Extracting Text",
    description: "Pulling text content from your document"
  },
  {
    id: "chunking",
    label: "Breaking Down Content",
    description: "Splitting content into searchable chunks"
  },
  {
    id: "embedding",
    label: "Generating Embeddings",
    description: "Creating vector representations for semantic search"
  },
  {
    id: "storing",
    label: "Storing Data",
    description: "Saving processed data for quick retrieval"
  }
];

export const ProcessingStatus: React.FC<ProcessingStatusProps> = ({ 
  fileId, 
  onProcessingComplete,
  onProcessingFailed
}) => {
  const [currentStage, setCurrentStage] = useState<string | null>(null);
  const [isComplete, setIsComplete] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [progressValue, setProgressValue] = useState(0);
  const [activeStage, setActiveStage] = useState<ProcessingStage | undefined>(undefined);
  
  // Find the current stage index
  const currentStageIndex = currentStage 
    ? STAGES.findIndex((s) => s.id === currentStage)
    : -1;

  // Update progress and active stage whenever currentStage changes
  useEffect(() => {
    setActiveStage(STAGES.find((s) => s.id === currentStage));
    
    if (currentStageIndex >= 0) {
      // Calculate progress based on current stage
      const stageProgress = ((currentStageIndex + 1) / STAGES.length) * 100;
      setProgressValue(stageProgress);
    }
  }, [currentStage, currentStageIndex]);

  useEffect(() => {
    console.log(`Setting up WebSocket for ${fileId}`);
    
    // Create WebSocket with explicit URL
    const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';
    const socket = new WebSocket(`${WS_URL}/ws/status/${fileId}`);
    
    socket.onopen = () => {
      console.log(`WebSocket connected for ${fileId}`);
    };
    
    socket.onmessage = (event) => {
      console.log(`Message received for ${fileId}:`, event.data);
      try {
        const data = JSON.parse(event.data);
        
        if (data.type === 'status_update') {
          if (data.status === 'processing') {
            setCurrentStage(data.metadata?.stage || null);
          } else if (data.status === 'completed') {
            setIsComplete(true);
            setProgressValue(100);
            socket.close();
            onProcessingComplete();
          } else if (data.status === 'failed') {
            // Ensure error is always a string (defensive handling)
            const errorMsg = data.metadata?.error
              ? (typeof data.metadata.error === 'string'
                  ? data.metadata.error
                  : JSON.stringify(data.metadata.error))
              : 'Processing failed';
            setError(errorMsg);
            socket.close();
            onProcessingFailed(errorMsg);
          }
        }
      } catch (error) {
        console.error('Error parsing message:', error);
      }
    };
    
    socket.onclose = (event) => {
      console.log(`WebSocket closed for ${fileId}: ${event.code} ${event.reason}`);
      if (!event.wasClean && !isComplete && !error) {
        setError('Connection closed unexpectedly');
        onProcessingFailed('Connection closed unexpectedly');
      }
    };
    
    socket.onerror = (error) => {
      console.error(`WebSocket error for ${fileId}:`, error);
      setError('WebSocket error occurred');
      onProcessingFailed('WebSocket error occurred');
    };
    
    // Cleanup
    return () => {
      console.log(`Cleaning up WebSocket for ${fileId}`);
      if (socket.readyState === WebSocket.OPEN || socket.readyState === WebSocket.CONNECTING) {
        socket.close(1000, "Component unmounting");
      }
    };
  }, [fileId, onProcessingComplete, onProcessingFailed, isComplete, error]);

  if (error) {
    return (
      <Card className="overflow-hidden border-destructive/20 shadow-md">
        <div className="h-2 bg-destructive" />
        <CardContent className="p-6">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-xl font-semibold">Processing Error</h3>
          </div>
          
          <div className="mb-8 flex items-center">
            <div className="w-12 h-12 rounded-full flex items-center justify-center mr-4 bg-destructive/10 text-destructive">
              <Loader2 className="w-6 h-6" />
            </div>
            <div>
              <h4 className="font-medium text-lg">Processing Failed</h4>
              <p className="text-muted-foreground">{error}</p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="overflow-hidden border-primary/20 shadow-md">
      <div className="h-2 bg-primary transition-all duration-300">
        <div 
          className="h-full bg-primary-foreground/20" 
          style={{ width: `${100 - progressValue}%`, float: "right" }} 
        />
      </div>

      <CardContent className="p-6">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-xl font-semibold">Processing Document</h3>
          <span className="text-sm font-medium bg-primary/10 text-primary px-3 py-1 rounded-full">
            {progressValue.toFixed(0)}%
          </span>
        </div>

        {activeStage && (
          <div className="mb-8 flex items-center">
            <div className="w-12 h-12 rounded-full flex items-center justify-center mr-4 bg-primary/10 text-primary">
              {isComplete ? (
                <CheckCircle2 className="w-6 h-6" />
              ) : (
                <Loader2 className="w-6 h-6 animate-spin" />
              )}
            </div>
            <div>
              <h4 className="font-medium text-lg">{activeStage.label}</h4>
              <p className="text-muted-foreground">{activeStage.description}</p>
            </div>
          </div>
        )}

        <div className="relative mt-12">
          {/* Line connecting all stages */}
          <div className="absolute top-3 left-0 right-0 h-0.5 bg-muted" />

          {/* Stages */}
          <div className="flex justify-between relative">
            {STAGES.map((stage, index) => {
              const isCompleted = currentStageIndex > index;
              const isCurrent = currentStageIndex === index;

              return (
                <div
                  key={stage.id}
                  className={cn(
                    "flex flex-col items-center relative transition-all duration-300",
                    isCompleted || isCurrent ? "text-primary" : "text-muted-foreground"
                  )}
                >
                  <div
                    className={cn(
                      "w-7 h-7 rounded-full flex items-center justify-center z-10 transition-all duration-300 border-2",
                      isCompleted
                        ? "bg-primary border-primary text-primary-foreground"
                        : isCurrent
                          ? "bg-primary/20 border-primary text-primary"
                          : "bg-muted border-muted-foreground/30"
                    )}
                  >
                    {isCompleted ? (
                      <CheckCircle2 className="w-4 h-4" />
                    ) : isCurrent ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <span className="w-1.5 h-1.5 rounded-full bg-muted-foreground/50" />
                    )}
                  </div>
                  <div
                    className={cn(
                      "text-xs mt-2 font-medium transition-all duration-300",
                      isCompleted
                        ? "text-primary"
                        : isCurrent
                          ? "text-primary"
                          : "text-muted-foreground"
                    )}
                  >
                    {stage.label}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

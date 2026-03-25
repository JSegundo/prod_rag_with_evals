// server/src/services/websocket/server.ts

import WebSocket, { WebSocketServer } from 'ws';
import { IncomingMessage, Server } from 'http';
import { parse } from 'url';
import { StatusUpdate } from '../../types';
import { setTimeout } from 'timers';

// Map to store WebSocket connections by fileId
const connections = new Map<string, WebSocket>();
// Map to store cleanup timers for connections
const connectionTimers = new Map<string, NodeJS.Timeout>();
// Map to store pending messages for fileIds that don't have connections yet
const pendingMessages = new Map<string, Array<{ status: string; metadata: Record<string, any>; timestamp: number }>>();

// Interface for the status server
export interface StatusServerInterface {
  sendStatusUpdate(fileId: string, status: StatusUpdate['status'], metadata?: Record<string, any>): void;
}

export function setupWebSocketServer(httpServer: Server): StatusServerInterface {
  const wss = new WebSocketServer({ noServer: true });
  console.log('WebSocket server initialized');
  
  // Handle WebSocket upgrade requests
  httpServer.on('upgrade', (request: IncomingMessage, socket, head) => {
    console.log(`Upgrade request received for: ${request.url}`);
    const { pathname, query } = parse(request.url || '', true);
    console.log(`Parsed pathname: ${pathname}`);
    
    // Check if this is a status WebSocket request
    if (pathname?.startsWith('/status/')) {
      // Extract fileId from URL path
      const fileId = pathname.split('/')[2];
      console.log(`Processing WebSocket connection for fileId: ${fileId}`);
      
      try {
        // Handle the WebSocket upgrade
        wss.handleUpgrade(request, socket, head, (ws: WebSocket) => {
          console.log(`handleUpgrade! WebSocket connection established for fileId: ${fileId}`);
          
          // Store the connection
          connections.set(fileId, ws);
          console.log(`Connections map now has ${connections.size} connections`);
          console.log(`Available connections: ${Array.from(connections.keys()).join(', ')}`);
          
          // Send initial connection message
          try {
            ws.send(JSON.stringify({
              type: 'status_update',
              fileId,
              status: 'connected',
              metadata: { timestamp: Date.now() }
            }));
            console.log(`Sent connection message to ${fileId}`);

            // Deliver any pending messages for this fileId
            const pending = pendingMessages.get(fileId);
            if (pending && pending.length > 0) {
              console.log(`Delivering ${pending.length} pending messages for ${fileId}`);
              for (const msg of pending) {
                ws.send(JSON.stringify({
                  type: 'status_update',
                  fileId,
                  status: msg.status,
                  metadata: msg.metadata,
                  timestamp: msg.timestamp
                }));
              }
              pendingMessages.delete(fileId);
            }
          } catch (err) {
            console.error(`Error sending test message:`, err);
          }
          
          // WebSocket event handlers
          ws.on('message', (message) => {
            console.log(`Received message from ${fileId}:`, message.toString());
          });
          
          ws.on('close', (code, reason) => {
            console.log(`WebSocket closed for ${fileId}: Code ${code}, Reason: ${reason}`);
            
            // Clear any existing timer
            if (connectionTimers.has(fileId)) {
              clearTimeout(connectionTimers.get(fileId)!);
              connectionTimers.delete(fileId);
            }
            
            // Don't remove the connection immediately to allow for pending notifications
            // Give a grace period before removing the connection
            const timer = setTimeout(() => {
              console.log(`Removing stale connection for ${fileId}`);
              connections.delete(fileId);
              connectionTimers.delete(fileId);
              console.log(`Remaining connections: ${Array.from(connections.keys()).join(', ')}`);
            }, 60000); // 1 minute retention
            
            connectionTimers.set(fileId, timer);
          });
          
          ws.on('error', (error) => {
            console.error(`WebSocket error for ${fileId}:`, error);
          });
        });
      } catch (err) {
        console.error('Error handling WebSocket upgrade:', err);
        socket.destroy();
      }
    } else {
      console.log(`Ignoring non-status WebSocket request: ${pathname}`);
    }
  });
  
  // Return the interface for sending status updates
  return {
    sendStatusUpdate: (fileId: string, status: StatusUpdate['status'], metadata: Record<string, any> = {}) => {
      console.log(`Trying to send status update for ${fileId}. Connections: ${connections.size}`);
      console.log(`Available connections: ${Array.from(connections.keys()).join(', ')}`);
      
      const connection = connections.get(fileId);
      if (connection) {
        try {
          if (connection.readyState === WebSocket.OPEN) {
            console.log(`Sending update to ${fileId}: ${status}`);
            connection.send(JSON.stringify({
              type: 'status_update',
              fileId,
              status,
              metadata,
              timestamp: Date.now()
            }));
          } else {
            console.log(`Connection for ${fileId} exists but is not open (state: ${connection.readyState})`);
            
            // If connection is not open, we should clean it up
            if (connection.readyState === WebSocket.CLOSED || connection.readyState === WebSocket.CLOSING) {
              console.log(`Removing closed connection for ${fileId}`);
              connections.delete(fileId);
            }
          }
        } catch (err) {
          console.error(`Error sending status update:`, err);
        }
      } else {
        console.log(`No connection found for ${fileId}, queuing message`);

        // Store the notification for later delivery when client connects
        const pending = pendingMessages.get(fileId) || [];
        pending.push({ status, metadata, timestamp: Date.now() });
        pendingMessages.set(fileId, pending);
        console.log(`Queued message for ${fileId}. Total pending: ${pending.length}`);
      }
    }
  };
}
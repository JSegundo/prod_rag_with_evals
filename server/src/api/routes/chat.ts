import { Router, Request, Response } from 'express';
import { Express } from 'express';
import { ChatManager } from '../../services/chat/chatManager';
import { ChatRequest, ChatMessage } from '../../types/chat';

const router = Router();
const chatManager = new ChatManager();

router.post('/chat', async (req: Request, res: Response) => {
    try {
        const request: ChatRequest = req.body;
        
        if (!request.message) {
            return res.status(400).json({ error: 'Message is required' });
        }

        const response = await chatManager.handleMessage(request);
        res.json(response);
    } catch (error) {
        console.error('Error handling chat message:', error);
        res.status(500).json({ error: 'Internal server error' });
    }
});

// Get conversation history
router.get('/history/:conversationId', (req: Request, res: Response) => {
    try {
        const { conversationId } = req.params;
        const history = chatManager.getConversationHistory(conversationId);
        res.json({ history });
    } catch (error) {
        console.error('Error getting conversation history:', error);
        res.status(500).json({ error: 'Internal server error' });
    }
});

export const setupChatRoutes = (app: Express) => {
  app.use('/api/chat', router);
};

export default router; 

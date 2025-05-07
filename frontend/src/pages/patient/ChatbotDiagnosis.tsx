import React, { useState, useRef, useEffect, FC, ChangeEvent, KeyboardEvent } from 'react';
import {
  Box,
  Paper,
  TextField,
  Button,
  Typography,
  List,
  ListItem,
  ListItemText,
  CircularProgress,
  Card,
  CardContent,
} from '@mui/material';
import { Send as SendIcon } from '@mui/icons-material';
import { api } from '../../config';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

const ChatbotDiagnosis: FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [newMessage, setNewMessage] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Start chat session when component mounts
  useEffect(() => {
    const startChat = async () => {
    try {
      setIsLoading(true);
        const response = await api.post('/api/chat/start');
      setMessages([{ role: 'assistant', content: response.data.message }]);
    } catch (error) {
        console.error('Error starting chat:', error);
        setMessages([{ role: 'assistant', content: 'Sorry, there was an error starting the chat. Please try again later.' }]);
    } finally {
      setIsLoading(false);
    }
  };

    startChat();
  }, []);

  const handleSend = async () => {
    if (!newMessage.trim()) return;

    const userMessage = newMessage.trim();
    setMessages((prevMessages: Message[]) => [...prevMessages, { role: 'user', content: userMessage }]);
    setNewMessage('');
    setIsLoading(true);

    try {
      const response = await api.post('/api/chat/message', {
          message: userMessage
      });

      // Add the chatbot response to messages
      setMessages((prevMessages: Message[]) => [...prevMessages, { role: 'assistant', content: response.data.message }]);
    } catch (error) {
      console.error('Error sending message:', error);
      setMessages((prevMessages: Message[]) => [...prevMessages, { role: 'assistant', content: 'Sorry, there was an error processing your message.' }]);
    } finally {
      setIsLoading(false);
      // Refocus the input after sending
      inputRef.current?.focus();
    }
  };

  const handleKeyPress = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  };

  return (
    <Box sx={{ height: 'calc(100vh - 80px)', display: 'flex', flexDirection: 'column' }}>
      <Card elevation={0} sx={{ mb: 3, borderRadius: 2, bgcolor: 'background.paper' }}>
        <CardContent>
          <Typography variant="h5" color="primary" gutterBottom fontWeight={600}>
            Chat with Dr. Mind
                </Typography>
                <Typography variant="body2" color="text.secondary" gutterBottom>
            Talk with Dr. Mind about your mental health concerns. Your conversation is private and secure.
          </Typography>
        </CardContent>
      </Card>

      <Paper 
        elevation={0}
        sx={{ 
          flexGrow: 1, 
          mb: 2, 
          p: 2, 
          overflow: 'auto',
          maxHeight: 'calc(100vh - 240px)',
          borderRadius: 2,
          border: '1px solid rgba(0, 0, 0, 0.08)',
          backgroundColor: '#fafcff'
        }}
      >
        {isLoading && messages.length === 0 ? (
          <Box display="flex" justifyContent="center" alignItems="center" height="100%">
            <CircularProgress size={40} />
            <Typography variant="body1" color="text.secondary" sx={{ ml: 2 }}>
              Starting conversation...
            </Typography>
          </Box>
        ) : (
          <List>
            {messages.map((message: Message, index: number) => (
              <ListItem
                key={index}
                sx={{
                  justifyContent: message.role === 'user' ? 'flex-end' : 'flex-start',
                  mb: 1.5,
                  py: 0,
                }}
              >
                <Paper
                  elevation={0}
                  sx={{
                    p: 2,
                    maxWidth: '70%',
                    backgroundColor: message.role === 'user' ? 'primary.light' : 'background.paper',
                    color: message.role === 'user' ? 'white' : 'text.primary',
                    borderRadius: message.role === 'user' ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
                    boxShadow: '0px 2px 6px rgba(0, 0, 0, 0.05)',
                    border: message.role === 'user' ? 'none' : '1px solid rgba(0, 0, 0, 0.08)',
                  }}
                >
                  <ListItemText 
                    primary={message.content} 
                    primaryTypographyProps={{
                      style: { wordBreak: 'break-word' }
                    }}
                  />
                </Paper>
              </ListItem>
            ))}
            <div ref={messagesEndRef} />
          </List>
        )}
      </Paper>
      
      <Box sx={{ 
        display: 'flex', 
        gap: 1,
        backgroundColor: 'background.paper',
        p: 2,
        borderRadius: 2,
        border: '1px solid rgba(0, 0, 0, 0.08)',
      }}>
        <TextField
          fullWidth
          multiline
          maxRows={4}
          value={newMessage}
          onChange={(e: ChangeEvent<HTMLInputElement>) => setNewMessage(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Type your message..."
          variant="outlined"
          inputRef={inputRef}
          InputProps={{
            sx: {
              borderRadius: 3,
              backgroundColor: '#fff',
              '& .MuiOutlinedInput-notchedOutline': {
                borderColor: 'rgba(0, 0, 0, 0.1)',
              },
            }
          }}
        />
        <Button
          variant="contained"
          onClick={handleSend}
          disabled={!newMessage.trim() || isLoading}
          sx={{ 
            minWidth: 56, 
            height: 56, 
            borderRadius: 3,
            boxShadow: 'none',
          }}
        >
          <SendIcon />
        </Button>
      </Box>
    </Box>
  );
};

export default ChatbotDiagnosis; 
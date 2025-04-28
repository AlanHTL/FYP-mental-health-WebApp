import React, { useState, useRef, useEffect } from 'react';
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
import axios from 'axios';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

const ChatbotDiagnosis = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [newMessage, setNewMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const messagesEndRef = useRef<null | HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const startSession = async () => {
    try {
      setIsLoading(true);
      const token = localStorage.getItem('token');
      const response = await axios.post(
        'http://localhost:8000/api/diagnosis/screening/start',
        {
          patient_info: {
            name: 'User',
            chief_complaints: ['Initial consultation']
          },
          symptoms: ['Initial consultation']
        },
        {
          headers: {
            Authorization: `Bearer ${token}`
          }
        }
      );
      setSessionId(response.data.session_id);
      setMessages([{ role: 'assistant', content: response.data.message }]);
    } catch (error) {
      console.error('Error starting session:', error);
      setMessages([{ role: 'assistant', content: 'Sorry, there was an error starting the chat session. Please try again later.' }]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    startSession();
  }, []);

  const handleSend = async () => {
    if (!newMessage.trim() || !sessionId) return;

    const userMessage = newMessage.trim();
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setNewMessage('');
    setIsLoading(true);

    try {
      const token = localStorage.getItem('token');
      const response = await axios.post(
        'http://localhost:8000/api/diagnosis/message',
        {
          session_id: sessionId,
          message: userMessage
        },
        {
          headers: {
            Authorization: `Bearer ${token}`
          }
        }
      );

      setMessages(prev => [...prev, { role: 'assistant', content: response.data.message }]);
    } catch (error) {
      console.error('Error sending message:', error);
      setMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, there was an error processing your message.' }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (event: React.KeyboardEvent) => {
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
            Mental Health Chatbot
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Talk with our AI assistant about your mental health concerns. Your conversation is private and will help us provide personalized assessments.
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
            {messages.map((message, index) => (
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
            {isLoading && messages.length > 0 && (
              <ListItem sx={{ justifyContent: 'flex-start', mb: 1.5, py: 0 }}>
                <Paper
                  elevation={0}
                  sx={{
                    p: 2,
                    display: 'flex',
                    alignItems: 'center',
                    backgroundColor: 'background.paper',
                    borderRadius: '16px 16px 16px 4px',
                    boxShadow: '0px 2px 6px rgba(0, 0, 0, 0.05)',
                    border: '1px solid rgba(0, 0, 0, 0.08)',
                  }}
                >
                  <CircularProgress size={20} sx={{ mr: 2 }} />
                  <Typography variant="body2" color="text.secondary">
                    Thinking...
                  </Typography>
                </Paper>
              </ListItem>
            )}
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
          onChange={(e) => setNewMessage(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Type your message..."
          disabled={isLoading && messages.length === 0}
          variant="outlined"
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
          disabled={!newMessage.trim() || isLoading || !sessionId}
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
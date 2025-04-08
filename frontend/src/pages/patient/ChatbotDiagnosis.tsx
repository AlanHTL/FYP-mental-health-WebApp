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
} from '@mui/material';
import { Send as SendIcon, ArrowBack } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

const ChatbotDiagnosis = () => {
  const navigate = useNavigate();
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
      alert('Failed to start chat session');
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
    <Box sx={{ height: 'calc(100vh - 100px)', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <Button 
          startIcon={<ArrowBack />} 
          onClick={() => navigate('/patient/home')}
          variant="outlined"
          sx={{ mr: 2 }}
        >
          Back to Home
        </Button>
        <Typography variant="h5">
          Mental Health Chatbot
        </Typography>
      </Box>
      <Paper 
        elevation={3} 
        sx={{ 
          flexGrow: 1, 
          mb: 2, 
          p: 2, 
          overflow: 'auto',
          maxHeight: 'calc(100vh - 240px)'
        }}
      >
        <List>
          {messages.map((message, index) => (
            <ListItem
              key={index}
              sx={{
                justifyContent: message.role === 'user' ? 'flex-end' : 'flex-start',
                mb: 1,
              }}
            >
              <Paper
                elevation={1}
                sx={{
                  p: 2,
                  maxWidth: '70%',
                  backgroundColor: message.role === 'user' ? 'primary.light' : 'grey.100',
                  color: message.role === 'user' ? 'white' : 'text.primary',
                }}
              >
                <ListItemText primary={message.content} />
              </Paper>
            </ListItem>
          ))}
          {isLoading && (
            <ListItem sx={{ justifyContent: 'flex-start' }}>
              <CircularProgress size={20} />
            </ListItem>
          )}
          <div ref={messagesEndRef} />
        </List>
      </Paper>
      <Box sx={{ display: 'flex', gap: 1 }}>
        <TextField
          fullWidth
          multiline
          maxRows={4}
          value={newMessage}
          onChange={(e) => setNewMessage(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Type your message..."
          disabled={isLoading}
        />
        <Button
          variant="contained"
          onClick={handleSend}
          disabled={!newMessage.trim() || isLoading}
          sx={{ minWidth: 100 }}
        >
          <SendIcon />
        </Button>
      </Box>
    </Box>
  );
};

export default ChatbotDiagnosis; 
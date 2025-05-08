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
  ButtonGroup,
  Chip,
} from '@mui/material';
import { Send as SendIcon, Description as DescriptionIcon } from '@mui/icons-material';
import { api } from '../../config';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

interface AssessmentOption {
  id: string;
  text: string;
}

const ChatbotDiagnosis: FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [newMessage, setNewMessage] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [showOptions, setShowOptions] = useState<boolean>(false);
  const [options, setOptions] = useState<AssessmentOption[]>([]);
  const [showReportButton, setShowReportButton] = useState<boolean>(false);
  const [isGeneratingReport, setIsGeneratingReport] = useState<boolean>(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [shouldFocusInput, setShouldFocusInput] = useState<boolean>(false);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (shouldFocusInput && inputRef.current && !showOptions) {
      inputRef.current.focus();
      setShouldFocusInput(false);
    }
  }, [shouldFocusInput, showOptions]);

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
        setShouldFocusInput(true);
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

      // Check if response contains assessment options
      if (response.data.assessment && response.data.options) {
        setShowOptions(true);
        setOptions(response.data.options);
      } else {
        setShowOptions(false);
        setOptions([]);
      }

      // Check if response contains a diagnosis result
      if (response.data.diagnosis && response.data.follow_up) {
        setMessages((prevMessages: Message[]) => [
          ...prevMessages, 
          { role: 'assistant', content: response.data.message },
          { role: 'assistant', content: response.data.follow_up }
        ]);
      } else {
        // Add the chatbot response to messages
        setMessages((prevMessages: Message[]) => [
          ...prevMessages, 
          { role: 'assistant', content: response.data.message }
        ]);
      }

      // Check if we should show the report button
      if (response.data.show_report_button) {
        setShowReportButton(true);
      }
    } catch (error) {
      console.error('Error sending message:', error);
      setMessages((prevMessages: Message[]) => [
        ...prevMessages, 
        { role: 'assistant', content: 'Sorry, there was an error processing your message.' }
      ]);
    } finally {
      setIsLoading(false);
      setShouldFocusInput(true);
    }
  };

  const handleOptionSelect = async (optionId: string) => {
    // Send the selected option to the backend
    setMessages((prevMessages: Message[]) => [
      ...prevMessages, 
      { role: 'user', content: optionId }
    ]);
    setIsLoading(true);

    try {
      const response = await api.post('/api/chat/message', {
        message: optionId
      });

      // Check if response contains more assessment options
      if (response.data.assessment && response.data.options) {
        setShowOptions(true);
        setOptions(response.data.options);
      } else {
        setShowOptions(false);
        setOptions([]);
        setShouldFocusInput(true);
      }

      // Add the chatbot response to messages
      setMessages((prevMessages: Message[]) => [
        ...prevMessages, 
        { role: 'assistant', content: response.data.message }
      ]);

      // Check if we should show the report button
      if (response.data.show_report_button) {
        setShowReportButton(true);
      }
    } catch (error) {
      console.error('Error sending option:', error);
      setMessages((prevMessages: Message[]) => [
        ...prevMessages, 
        { role: 'assistant', content: 'Sorry, there was an error processing your selection.' }
      ]);
      setShowOptions(false);
      setShouldFocusInput(true);
    } finally {
      setIsLoading(false);
    }
  };

  const handleGenerateReport = async () => {
    setIsGeneratingReport(true);
    setMessages((prevMessages: Message[]) => [
      ...prevMessages, 
      { role: 'user', content: 'Generate diagnosis report' }
    ]);

    try {
      const response = await api.post('/api/chat/message', {
        message: 'Generate diagnosis report'
      });

      // Add the report to messages
      setMessages((prevMessages: Message[]) => [
        ...prevMessages, 
        { role: 'assistant', content: response.data.message }
      ]);

      // Hide the report button after generating
      setShowReportButton(false);
    } catch (error) {
      console.error('Error generating report:', error);
      setMessages((prevMessages: Message[]) => [
        ...prevMessages, 
        { role: 'assistant', content: 'Sorry, there was an error generating the report.' }
      ]);
    } finally {
      setIsGeneratingReport(false);
      setShouldFocusInput(true);
    }
  };

  const handleKeyPress = (event: KeyboardEvent<HTMLDivElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  };

  const formatMessage = (content: string) => {
    // Check if the content is JSON
    if (content.startsWith('{{') && content.endsWith('}}')) {
      try {
        const jsonObject = JSON.parse(content);
        return (
          <Box sx={{ p: 1, bgcolor: '#f5f5f5', borderRadius: 1 }}>
            <Typography variant="body2" component="pre" sx={{ whiteSpace: 'pre-wrap', fontFamily: 'monospace' }}>
              {JSON.stringify(jsonObject, null, 2)}
            </Typography>
          </Box>
        );
      } catch (e) {
        // Not valid JSON, continue with normal formatting
      }
    }

    // Handle markdown sections
    if (content.includes('# ')) {
      const sections = content.split('\n');
      return (
        <>
          {sections.map((section, i) => {
            if (section.startsWith('# ')) {
              return (
                <Typography key={i} variant="h6" sx={{ mt: 2, mb: 1, fontWeight: 'bold' }}>
                  {section.replace('# ', '')}
                </Typography>
              );
            } else if (section.startsWith('## ')) {
              return (
                <Typography key={i} variant="subtitle1" sx={{ mt: 1.5, mb: 0.5, fontWeight: 'bold' }}>
                  {section.replace('## ', '')}
                </Typography>
              );
            } else if (section.startsWith('*') && section.endsWith('*')) {
              return (
                <Typography key={i} variant="body2" sx={{ mt: 1, fontStyle: 'italic', color: 'text.secondary' }}>
                  {section.replace(/^\*/, '').replace(/\*$/, '')}
                </Typography>
              );
            } else if (section.trim() !== '') {
              return (
                <Typography key={i} variant="body1" paragraph sx={{ my: 0.5 }}>
                  {section}
                </Typography>
              );
            }
            return null;
          })}
        </>
      );
    }

    // Default text formatting
    return content;
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
                    primary={formatMessage(message.content)} 
                    primaryTypographyProps={{
                      style: { wordBreak: 'break-word' }
                    }}
                  />
                </Paper>
              </ListItem>
            ))}
            {showOptions && (
              <ListItem sx={{ justifyContent: 'flex-start', flexDirection: 'column', alignItems: 'flex-start' }}>
                <Typography variant="caption" color="text.secondary" sx={{ mb: 1 }}>
                  Please select one option:
                </Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, width: '100%', maxWidth: '70%' }}>
                  {options.map((option) => (
                    <Button
                      key={option.id}
                      variant="outlined"
                      color="primary"
                      onClick={() => handleOptionSelect(option.id)}
                      disabled={isLoading}
                      sx={{ 
                        justifyContent: 'flex-start',
                        textTransform: 'none',
                        borderRadius: 2
                      }}
                    >
                      <Box sx={{ display: 'flex', alignItems: 'center', width: '100%' }}>
                        <Chip 
                          label={option.id} 
                          size="small" 
                          sx={{ mr: 1, minWidth: '24px' }}
                        />
                        <Typography variant="body2" textAlign="left">
                          {option.text}
                        </Typography>
                      </Box>
                    </Button>
                  ))}
                </Box>
              </ListItem>
            )}
            {isLoading && (
              <ListItem sx={{ justifyContent: 'flex-start' }}>
                <CircularProgress size={24} sx={{ m: 1 }} />
              </ListItem>
            )}
            {showReportButton && !isGeneratingReport && (
              <ListItem sx={{ justifyContent: 'center', my: 2 }}>
                <Button
                  variant="contained"
                  color="primary"
                  startIcon={<DescriptionIcon />}
                  onClick={handleGenerateReport}
                  sx={{ 
                    borderRadius: 2,
                    boxShadow: '0px 3px 8px rgba(0, 0, 0, 0.1)'
                  }}
                >
                  Generate Diagnosis Report
                </Button>
              </ListItem>
            )}
            {isGeneratingReport && (
              <ListItem sx={{ justifyContent: 'center', my: 2 }}>
                <Button
                  variant="outlined"
                  disabled
                  startIcon={<CircularProgress size={20} />}
                  sx={{ 
                    borderRadius: 2
                  }}
                >
                  Generating Report...
                </Button>
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
          onChange={(e: ChangeEvent<HTMLInputElement>) => setNewMessage(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Type your message..."
          variant="outlined"
          disabled={showOptions}
          inputRef={inputRef}
          sx={{
            '& .MuiInputBase-input.Mui-disabled': {
              WebkitTextFillColor: 'rgba(0, 0, 0, 0.38)',
            },
          }}
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
          disabled={!newMessage.trim() || showOptions}
          sx={{ 
            minWidth: 56, 
            height: 56, 
            borderRadius: 3,
            boxShadow: 'none',
            opacity: isLoading ? 0.7 : 1,
            transition: 'opacity 0.2s',
            '&:disabled': {
              backgroundColor: (theme) => theme.palette.primary.main,
              opacity: 0.5,
            }
          }}
        >
          {isLoading ? <CircularProgress size={24} color="inherit" /> : <SendIcon />}
        </Button>
      </Box>
    </Box>
  );
};

export default ChatbotDiagnosis; 
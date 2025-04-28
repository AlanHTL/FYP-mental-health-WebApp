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
  Stepper,
  Step,
  StepLabel,
  Radio,
  RadioGroup,
  FormControlLabel,
  FormControl,
  FormLabel,
  Alert,
  Divider,
} from '@mui/material';
import { Send as SendIcon, Assessment as AssessmentIcon, Description as DescriptionIcon } from '@mui/icons-material';
import { api } from '../../config';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

interface DiagnosisJson {
  result: string[];
  probabilities: number[];
}

interface AssessmentQuestion {
  question: string;
  options: string[];
}

interface AssessmentResult {
  score: number;
  severity: string;
  subscales?: Record<string, number>;
}

const ChatbotDiagnosis = () => {
  // Chat state
  const [messages, setMessages] = useState<Message[]>([]);
  const [newMessage, setNewMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const messagesEndRef = useRef<null | HTMLDivElement>(null);
  
  // Multi-agent workflow state
  const [activeStep, setActiveStep] = useState(0);
  const [diagnosisResult, setDiagnosisResult] = useState<DiagnosisJson | null>(null);
  const [recommendedAssessment, setRecommendedAssessment] = useState<string | null>(null);
  
  // Assessment state
  const [assessmentQuestions, setAssessmentQuestions] = useState<string[]>([]);
  const [assessmentOptions, setAssessmentOptions] = useState<string[]>([]);
  const [assessmentResponses, setAssessmentResponses] = useState<number[]>([]);
  const [assessmentResult, setAssessmentResult] = useState<any | null>(null);
  const [assessmentId, setAssessmentId] = useState<string | null>(null);
  
  // Report state
  const [report, setReport] = useState<any | null>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const startSession = async () => {
    try {
      setIsLoading(true);
      const response = await api.post(
        '/api/diagnosis/screening/start',
        {
          patient_info: {
            name: 'User',
            chief_complaints: ['Initial consultation']
          },
          symptoms: ['Initial consultation']
        }
      );
      setSessionId(response.data.session_id);
      setMessages([{ role: 'assistant', content: response.data.message }]);
      setActiveStep(0); // Screening step
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
      const response = await api.post(
        '/api/diagnosis/message',
        {
          session_id: sessionId,
          message: userMessage
        }
      );

      // Add the chatbot response to messages
      setMessages(prev => [...prev, { role: 'assistant', content: response.data.message }]);
      
      // Check if screening is complete and assessment is recommended
      if (response.data.diagnosis_json) {
        setDiagnosisResult(response.data.diagnosis_json);
        setRecommendedAssessment(response.data.recommended_assessment);
        setActiveStep(1); // Move to assessment selection step
      }
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

  const startAssessment = async (assessment: string) => {
    if (!sessionId) return;
    
    setIsLoading(true);
    setAssessmentId(assessment);
    
    try {
      const response = await api.post(
        '/api/diagnosis/assessment/start',
        {
          session_id: sessionId,
          assessment_id: assessment,
          patient_info: {
            age: 30, // Default values, could be collected from user
            gender: 'not specified'
          }
        }
      );
      
      // Add the assessment introduction message
      setMessages(prev => [...prev, { role: 'assistant', content: response.data.message }]);
      
      // Store assessment questions and options
      setAssessmentQuestions(response.data.questions);
      setAssessmentOptions(response.data.options);
      
      // Initialize responses array with default values (0)
      setAssessmentResponses(new Array(response.data.questions.length).fill(0));
      
      // Move to assessment questions step
      setActiveStep(2);
    } catch (error) {
      console.error('Error starting assessment:', error);
      setMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, there was an error starting the assessment.' }]);
    } finally {
      setIsLoading(false);
    }
  };
  
  const handleResponseChange = (questionIndex: number, value: number) => {
    setAssessmentResponses(prev => {
      const newResponses = [...prev];
      newResponses[questionIndex] = value;
      return newResponses;
    });
  };
  
  const submitAssessment = async () => {
    if (!sessionId || !assessmentId) return;
    
    setIsLoading(true);
    
    try {
      const response = await api.post(
        '/api/diagnosis/assessment/submit',
        {
          session_id: sessionId,
          assessment_id: assessmentId,
          responses: assessmentResponses
        }
      );
      
      // Store assessment result
      setAssessmentResult(response.data.result);
      
      // Add result message
      setMessages(prev => [...prev, { role: 'assistant', content: response.data.interpretation }]);
      
      // Move to report generation step
      setActiveStep(3);
    } catch (error) {
      console.error('Error submitting assessment:', error);
      setMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, there was an error processing your assessment responses.' }]);
    } finally {
      setIsLoading(false);
    }
  };
  
  const generateReport = async () => {
    if (!sessionId) return;
    
    setIsLoading(true);
    
    try {
      const response = await api.post(
        '/api/diagnosis/report/generate',
        {
          session_id: sessionId,
          additional_info: ''
        }
      );
      
      // Store report
      setReport(response.data.full_report);
      
      // Add report message
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: `Your assessment report is ready. Diagnosis: ${response.data.diagnosis}. ${response.data.summary}`
      }]);
      
      // Move to completed step
      setActiveStep(4);
    } catch (error) {
      console.error('Error generating report:', error);
      setMessages(prev => [...prev, { role: 'assistant', content: 'Sorry, there was an error generating your report.' }]);
    } finally {
      setIsLoading(false);
    }
  };
  
  // Render different UI based on current step
  const renderStepContent = () => {
    switch(activeStep) {
      case 0: // Screening
        return renderChatInterface();
      case 1: // Assessment Selection
        return (
          <Box sx={{ mt: 3 }}>
            <Card sx={{ mb: 2, p: 2 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>Screening Complete</Typography>
                <Typography variant="body1" gutterBottom>
                  Based on our conversation, the initial screening suggests:
                </Typography>
                {diagnosisResult && (
                  <Box sx={{ my: 2 }}>
                    <Typography variant="subtitle1">
                      Potential condition(s): {diagnosisResult.result.join(', ')}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Confidence: {diagnosisResult.probabilities.map(p => `${p * 100}%`).join(', ')}
                    </Typography>
                  </Box>
                )}
                <Typography variant="body1" mt={2}>
                  To get a more accurate assessment, please complete the recommended assessment:
                </Typography>
                <Button 
                  variant="contained" 
                  sx={{ mt: 2 }}
                  onClick={() => recommendedAssessment && startAssessment(recommendedAssessment)}
                >
                  Start {recommendedAssessment} Assessment
                </Button>
              </CardContent>
            </Card>
            {renderChatInterface()}
          </Box>
        );
      case 2: // Assessment Questions
        return (
          <Box sx={{ mt: 3 }}>
            <Card sx={{ mb: 2, p: 2 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  {assessmentId} Assessment
                </Typography>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Please answer each question honestly. Your responses will help provide a more accurate assessment.
                </Typography>
                
                <Box sx={{ mt: 3 }}>
                  {assessmentQuestions.map((question, index) => (
                    <FormControl key={index} component="fieldset" sx={{ mb: 3, width: '100%' }}>
                      <FormLabel component="legend" sx={{ fontSize: '1rem', mb: 1 }}>
                        {index + 1}. {question}
                      </FormLabel>
                      <RadioGroup
                        value={assessmentResponses[index]}
                        onChange={(e) => handleResponseChange(index, Number(e.target.value))}
                        sx={{ ml: 2 }}
                      >
                        {assessmentOptions.map((option, optIndex) => (
                          <FormControlLabel
                            key={optIndex}
                            value={optIndex}
                            control={<Radio />}
                            label={option}
                            sx={{ mb: 0.5 }}
                          />
                        ))}
                      </RadioGroup>
                    </FormControl>
                  ))}
                  
                  <Button
                    variant="contained"
                    onClick={submitAssessment}
                    disabled={assessmentResponses.length !== assessmentQuestions.length}
                    sx={{ mt: 2 }}
                  >
                    Submit Assessment
                  </Button>
                </Box>
              </CardContent>
            </Card>
            {renderChatInterface()}
          </Box>
        );
      case 3: // Report Generation
        return (
          <Box sx={{ mt: 3 }}>
            <Card sx={{ mb: 2, p: 2 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>Assessment Complete</Typography>
                
                {assessmentResult && (
                  <Box sx={{ my: 2 }}>
                    <Typography variant="subtitle1" gutterBottom>
                      Assessment Results:
                    </Typography>
                    
                    {assessmentId === 'DASS-21' && assessmentResult.depression && (
                      <Box sx={{ mb: 2 }}>
                        <Typography variant="body1">
                          Depression: {assessmentResult.depression.score} - {assessmentResult.depression.severity}
                        </Typography>
                        <Typography variant="body1">
                          Anxiety: {assessmentResult.anxiety.score} - {assessmentResult.anxiety.severity}
                        </Typography>
                        <Typography variant="body1">
                          Stress: {assessmentResult.stress.score} - {assessmentResult.stress.severity}
                        </Typography>
                      </Box>
                    )}
                    
                    {assessmentId === 'PCL-5' && (
                      <Box sx={{ mb: 2 }}>
                        <Typography variant="body1">
                          Total Score: {assessmentResult.score} - {assessmentResult.severity}
                        </Typography>
                        {assessmentResult.subscales && (
                          <>
                            <Typography variant="body2" mt={1}>Subscales:</Typography>
                            <Typography variant="body2">
                              Intrusion: {assessmentResult.subscales.intrusion}
                            </Typography>
                            <Typography variant="body2">
                              Avoidance: {assessmentResult.subscales.avoidance}
                            </Typography>
                            <Typography variant="body2">
                              Cognition & Mood: {assessmentResult.subscales.cognition_mood}
                            </Typography>
                            <Typography variant="body2">
                              Arousal & Reactivity: {assessmentResult.subscales.arousal_reactivity}
                            </Typography>
                          </>
                        )}
                      </Box>
                    )}
                    
                    <Alert severity="info" sx={{ mb: 2 }}>
                      This assessment provides an initial understanding of your symptoms. For a complete diagnosis, please consult with a mental health professional.
                    </Alert>
                    
                    <Button 
                      variant="contained" 
                      sx={{ mt: 2 }}
                      onClick={generateReport}
                    >
                      Generate Comprehensive Report
                    </Button>
                  </Box>
                )}
              </CardContent>
            </Card>
            {renderChatInterface()}
          </Box>
        );
      case 4: // Completed
        return (
          <Box sx={{ mt: 3 }}>
            <Card sx={{ mb: 2, p: 2 }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>Assessment Report</Typography>
                
                {report && (
                  <Box sx={{ my: 2 }}>
                    <Typography variant="subtitle1" gutterBottom>
                      Diagnosis: {report.diagnosis || 'Not specified'}
                    </Typography>
                    
                    <Divider sx={{ my: 2 }} />
                    
                    <Typography variant="subtitle1" gutterBottom>
                      Summary:
                    </Typography>
                    <Typography variant="body1" paragraph>
                      {report.summary || 'No summary available.'}
                    </Typography>
                    
                    <Typography variant="subtitle1" gutterBottom>
                      Recommendations:
                    </Typography>
                    <List>
                      {report.recommendations ? 
                        report.recommendations.map((rec: string, index: number) => (
                          <ListItem key={index} sx={{ py: 0.5 }}>
                            <ListItemText primary={rec} />
                          </ListItem>
                        )) : 
                        <ListItem>
                          <ListItemText primary="No specific recommendations available." />
                        </ListItem>
                      }
                    </List>
                    
                    <Alert severity="info" sx={{ mt: 2 }}>
                      This report is for informational purposes and does not replace professional medical advice. Please share this report with your healthcare provider.
                    </Alert>
                  </Box>
                )}
              </CardContent>
            </Card>
            {renderChatInterface()}
          </Box>
        );
      default:
        return renderChatInterface();
    }
  };
  
  // The chat interface that will be shown in all steps
  const renderChatInterface = () => (
    <>
      <Paper 
        elevation={0}
        sx={{ 
          flexGrow: 1, 
          mb: 2, 
          p: 2, 
          overflow: 'auto',
          maxHeight: activeStep > 0 ? '300px' : 'calc(100vh - 240px)',
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
          disabled={isLoading || activeStep > 1}
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
          disabled={!newMessage.trim() || isLoading || !sessionId || activeStep > 1}
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
    </>
  );

  return (
    <Box sx={{ height: 'calc(100vh - 80px)', display: 'flex', flexDirection: 'column' }}>
      <Card elevation={0} sx={{ mb: 3, borderRadius: 2, bgcolor: 'background.paper' }}>
        <CardContent>
          <Typography variant="h5" color="primary" gutterBottom fontWeight={600}>
            Mental Health Assessment
          </Typography>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            Talk with our AI assistant about your mental health concerns. Your conversation is private and will help us provide personalized assessments.
          </Typography>
          
          <Stepper activeStep={activeStep} sx={{ mt: 2 }}>
            <Step>
              <StepLabel>Screening</StepLabel>
            </Step>
            <Step>
              <StepLabel>Assessment Selection</StepLabel>
            </Step>
            <Step>
              <StepLabel>Assessment Questions</StepLabel>
            </Step>
            <Step>
              <StepLabel>Report Generation</StepLabel>
            </Step>
            <Step>
              <StepLabel>Complete</StepLabel>
            </Step>
          </Stepper>
        </CardContent>
      </Card>
      
      {renderStepContent()}
    </Box>
  );
};

export default ChatbotDiagnosis; 
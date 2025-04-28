import React, { useEffect, useState } from 'react';
import { Box, Typography, Button } from '@mui/material';
import { api } from '../config';

const TestConnection = () => {
  const [status, setStatus] = useState<string>('Testing...');
  const [error, setError] = useState<string | null>(null);

  const testConnection = async () => {
    try {
      const response = await api.get('/');
      setStatus('Connected successfully!');
      setError(null);
      console.log('API Response:', response.data);
    } catch (err: any) {
      setStatus('Connection failed');
      setError(err.message);
      console.error('API Error:', err);
    }
  };

  useEffect(() => {
    testConnection();
  }, []);

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom>
        API Connection Test
      </Typography>
      <Typography variant="body1" gutterBottom>
        Status: {status}
      </Typography>
      {error && (
        <Typography variant="body2" color="error">
          Error: {error}
        </Typography>
      )}
      <Button 
        variant="contained" 
        onClick={testConnection}
        sx={{ mt: 2 }}
      >
        Test Again
      </Button>
    </Box>
  );
};

export default TestConnection; 
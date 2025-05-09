import React, { useState } from 'react';
import {
  Box,
  Button,
  Container,
  TextField,
  Typography,
  Paper,
  Card,
  CardContent,
  InputAdornment,
  IconButton,
  Link,
} from '@mui/material';
import { 
  Email as EmailIcon, 
  Lock as LockIcon,
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon 
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { api } from '../../config';

const Login = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    email: '',
    password: '',
  });
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
    setError(''); // Clear error when typing
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');
    
    try {
      const response = await api.post('/api/auth/login', formData);

      if (response.data.access_token) {
        localStorage.setItem('token', response.data.access_token);
        // Redirect based on user type
        const userType = response.data.user_type;
        navigate(userType === 'patient' ? '/patient/home' : '/doctor/home');
      }
    } catch (error) {
      console.error('Login failed:', error);
      setError('Login failed. Please check your credentials and try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Box 
      sx={{ 
        height: '100vh', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        backgroundColor: '#f8f9fa'
      }}
    >
      <Container maxWidth="sm">
        <Card 
          elevation={0} 
          sx={{ 
            borderRadius: 3,
            overflow: 'hidden',
            boxShadow: '0 8px 40px rgba(0, 0, 0, 0.12)',
            backgroundColor: '#ffffff'
          }}
        >
          <Box 
            sx={{ 
              p: 3, 
              backgroundColor: 'primary.main', 
              color: 'white',
              textAlign: 'center'
            }}
          >
            <Typography variant="h4" component="h1" gutterBottom fontWeight={600}>
              Mental Health App
            </Typography>
            <Typography variant="body1">
              Sign in to continue your mental health journey
            </Typography>
          </Box>
          
          <CardContent sx={{ p: 4 }}>
            {error && (
              <Box 
                sx={{ 
                  p: 2, 
                  mb: 3, 
                  backgroundColor: 'rgba(211, 47, 47, 0.1)', 
                  borderRadius: 2,
                  color: 'error.main'
                }}
              >
                <Typography variant="body2">{error}</Typography>
              </Box>
            )}
            
            <Box component="form" onSubmit={handleSubmit}>
              <TextField
                margin="normal"
                required
                fullWidth
                id="email"
                label="Email Address"
                name="email"
                autoComplete="email"
                autoFocus
                value={formData.email}
                onChange={handleChange}
                variant="outlined"
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <EmailIcon color="primary" />
                    </InputAdornment>
                  ),
                  sx: { borderRadius: 2 }
                }}
                sx={{ mb: 3 }}
              />
              
              <TextField
                margin="normal"
                required
                fullWidth
                name="password"
                label="Password"
                type={showPassword ? "text" : "password"}
                id="password"
                autoComplete="current-password"
                value={formData.password}
                onChange={handleChange}
                variant="outlined"
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <LockIcon color="primary" />
                    </InputAdornment>
                  ),
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        onClick={() => setShowPassword(!showPassword)}
                        edge="end"
                      >
                        {showPassword ? <VisibilityOffIcon /> : <VisibilityIcon />}
                      </IconButton>
                    </InputAdornment>
                  ),
                  sx: { borderRadius: 2 }
                }}
                sx={{ mb: 4 }}
              />
              
              <Button
                type="submit"
                fullWidth
                variant="contained"
                sx={{ 
                  mt: 1, 
                  mb: 3, 
                  py: 1.5, 
                  borderRadius: 2,
                  fontWeight: 600,
                  fontSize: '1rem',
                }}
                disabled={isLoading}
              >
                {isLoading ? 'Signing in...' : 'Sign In'}
              </Button>
              
              <Box sx={{ textAlign: 'center' }}>
                <Link 
                  component="button" 
                  variant="body2" 
                  onClick={() => navigate('/register')}
                  underline="hover"
                  sx={{ color: 'text.secondary' }}
                >
                  Don't have an account? Sign up
                </Link>
              </Box>
            </Box>
          </CardContent>
        </Card>
        
        <Box sx={{ textAlign: 'center', mt: 3 }}>
          <Typography variant="body2" color="text.secondary">
            © {new Date().getFullYear()} Mental Health App. All rights reserved.
          </Typography>
        </Box>
      </Container>
    </Box>
  );
};

export default Login; 
import React, { useEffect, useState } from 'react';
import { Container, Typography, Box, Button } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

interface PatientProfile {
  title: string;
  first_name: string;
  last_name: string;
}

const PatientHome = () => {
  const navigate = useNavigate();
  const [profile, setProfile] = useState<PatientProfile | null>(null);

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const token = localStorage.getItem('token');
        const response = await axios.get('http://localhost:8000/api/patients/me', {
          headers: { Authorization: `Bearer ${token}` }
        });
        setProfile(response.data);
      } catch (error) {
        console.error('Failed to fetch profile:', error);
      }
    };

    fetchProfile();
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/login');
  };

  return (
    <Container>
      <Box sx={{ mt: 4 }}>
        {profile && (
          <Typography variant="h4" component="h1" gutterBottom>
            Welcome, {profile.title} {profile.first_name} {profile.last_name}
          </Typography>
        )}
        <Box sx={{ mt: 4, display: 'flex', gap: 2, flexDirection: 'column', alignItems: 'center' }}>
          <Button
            variant="contained"
            color="primary"
            fullWidth
            sx={{ maxWidth: 400 }}
            onClick={() => navigate('/patient/screening')}
          >
            Start Mental Health Screening
          </Button>
          <Button
            variant="contained"
            color="primary"
            fullWidth
            sx={{ maxWidth: 400 }}
            onClick={() => navigate('/patient/history')}
          >
            View History
          </Button>
          <Button
            variant="contained"
            color="primary"
            fullWidth
            sx={{ maxWidth: 400 }}
            onClick={() => navigate('/patient/doctors')}
          >
            Find Doctors
          </Button>
          <Button
            variant="outlined"
            color="secondary"
            fullWidth
            sx={{ maxWidth: 400 }}
            onClick={handleLogout}
          >
            Logout
          </Button>
        </Box>
      </Box>
    </Container>
  );
};

export default PatientHome; 
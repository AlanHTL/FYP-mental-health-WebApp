import React, { useEffect, useState } from 'react';
import { Container, Typography, Box, Button } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

interface DoctorProfile {
  title: string;
  first_name: string;
  last_name: string;
}

const DoctorHome = () => {
  const navigate = useNavigate();
  const [profile, setProfile] = useState<DoctorProfile | null>(null);

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const token = localStorage.getItem('token');
        const response = await axios.get('http://localhost:8000/api/doctors/me', {
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
            onClick={() => navigate('/doctor/patients')}
          >
            View Patients
          </Button>
          <Button
            variant="contained"
            color="primary"
            fullWidth
            sx={{ maxWidth: 400 }}
            onClick={() => navigate('/doctor/requests')}
          >
            Patient Link Requests
          </Button>
          <Button
            variant="contained"
            color="primary"
            fullWidth
            sx={{ maxWidth: 400 }}
            onClick={() => navigate('/doctor/reports')}
          >
            Create Reports
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

export default DoctorHome; 
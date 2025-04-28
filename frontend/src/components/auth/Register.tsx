import React, { useState } from 'react';
import {
  Box,
  Button,
  Container,
  TextField,
  Typography,
  Paper,
  RadioGroup,
  Radio,
  FormControlLabel,
  FormControl,
  FormLabel,
  Grid,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { api } from '../../config';

const Register = () => {
  const navigate = useNavigate();
  const [userType, setUserType] = useState('patient');
  const [formData, setFormData] = useState({
    title: '',
    first_name: '',
    last_name: '',
    email: '',
    password: '',
    date_of_birth: '',
    sex: 'Male',
    phone_number: '',
    // Doctor specific fields
    clinic_name: '',
    clinic_location: '',
    clinic_contact: '',
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const endpoint = userType === 'patient' 
        ? '/api/auth/register/patient'
        : '/api/auth/register/doctor';

      // Remove phone_number from data if registering as a doctor
      const submitData = userType === 'doctor' 
        ? { ...formData, phone_number: undefined }
        : formData;

      const response = await api.post(endpoint, submitData);

      if (response.data.access_token) {
        localStorage.setItem('token', response.data.access_token);
        navigate(userType === 'patient' ? '/patient/home' : '/doctor/home');
      }
    } catch (error) {
      console.error('Registration failed:', error);
      alert('Registration failed. Please try again.');
    }
  };

  return (
    <Container component="main" maxWidth="sm">
      <Paper elevation={3} sx={{ p: 4, mt: 8, display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <Typography component="h1" variant="h5">
          Register
        </Typography>
        <Box component="form" onSubmit={handleSubmit} sx={{ mt: 3 }}>
          <FormControl component="fieldset" sx={{ mb: 3 }}>
            <FormLabel component="legend">Register as</FormLabel>
            <RadioGroup
              row
              value={userType}
              onChange={(e) => setUserType(e.target.value)}
            >
              <FormControlLabel value="patient" control={<Radio />} label="Patient" />
              <FormControlLabel value="doctor" control={<Radio />} label="Doctor" />
            </RadioGroup>
          </FormControl>

          <Grid container spacing={2}>
            <Grid item xs={12} sm={6}>
              <TextField
                required
                fullWidth
                label="Title"
                name="title"
                value={formData.title}
                onChange={handleChange}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                required
                fullWidth
                label="First Name"
                name="first_name"
                value={formData.first_name}
                onChange={handleChange}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                required
                fullWidth
                label="Last Name"
                name="last_name"
                value={formData.last_name}
                onChange={handleChange}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                required
                fullWidth
                label="Email"
                name="email"
                type="email"
                value={formData.email}
                onChange={handleChange}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                required
                fullWidth
                label="Password"
                name="password"
                type="password"
                value={formData.password}
                onChange={handleChange}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <TextField
                required
                fullWidth
                label="Date of Birth"
                name="date_of_birth"
                type="date"
                value={formData.date_of_birth}
                onChange={handleChange}
                InputLabelProps={{ shrink: true }}
              />
            </Grid>
            <Grid item xs={12} sm={6}>
              <FormControl component="fieldset">
                <FormLabel component="legend">Sex</FormLabel>
                <RadioGroup
                  row
                  name="sex"
                  value={formData.sex}
                  onChange={handleChange}
                >
                  <FormControlLabel value="Male" control={<Radio />} label="Male" />
                  <FormControlLabel value="Female" control={<Radio />} label="Female" />
                </RadioGroup>
              </FormControl>
            </Grid>
            
            {userType === 'patient' && (
              <Grid item xs={12} sm={6}>
                <TextField
                  required
                  fullWidth
                  label="Phone Number"
                  name="phone_number"
                  value={formData.phone_number}
                  onChange={handleChange}
                />
              </Grid>
            )}

            {userType === 'doctor' && (
              <>
                <Grid item xs={12}>
                  <TextField
                    required
                    fullWidth
                    label="Clinic Name"
                    name="clinic_name"
                    value={formData.clinic_name}
                    onChange={handleChange}
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    required
                    fullWidth
                    label="Clinic Location"
                    name="clinic_location"
                    value={formData.clinic_location}
                    onChange={handleChange}
                  />
                </Grid>
                <Grid item xs={12}>
                  <TextField
                    required
                    fullWidth
                    label="Clinic Contact"
                    name="clinic_contact"
                    value={formData.clinic_contact}
                    onChange={handleChange}
                  />
                </Grid>
              </>
            )}
          </Grid>

          <Button
            type="submit"
            fullWidth
            variant="contained"
            sx={{ mt: 3, mb: 2 }}
          >
            Register
          </Button>
          <Button
            fullWidth
            variant="text"
            onClick={() => navigate('/login')}
          >
            Already have an account? Sign in
          </Button>
        </Box>
      </Paper>
    </Container>
  );
};

export default Register; 
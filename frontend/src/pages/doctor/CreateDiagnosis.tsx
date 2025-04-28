import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  TextField,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  OutlinedInput,
  SelectChangeEvent,
  Snackbar,
  Alert,
  Autocomplete,
} from '@mui/material';
import { ArrowBack } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { api } from '../../config';

interface Patient {
  id: number;
  title: string;
  first_name: string;
  last_name: string;
}

const CreateDiagnosis = () => {
  const navigate = useNavigate();
  const [patients, setPatients] = useState<Patient[]>([]);
  const [selectedPatient, setSelectedPatient] = useState<number | ''>('');
  const [diagnosis, setDiagnosis] = useState('');
  const [symptoms, setSymptoms] = useState<string[]>([]);
  const [newSymptom, setNewSymptom] = useState('');
  const [recommendations, setRecommendations] = useState<string[]>([]);
  const [newRecommendation, setNewRecommendation] = useState('');
  const [snackbar, setSnackbar] = useState({
    open: false,
    message: '',
    severity: 'success' as 'success' | 'error',
  });

  useEffect(() => {
    fetchPatients();
  }, []);

  const fetchPatients = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await api.get('/api/doctor/patients', {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      setPatients(response.data);
    } catch (error) {
      console.error('Error fetching patients:', error);
    }
  };

  const handlePatientChange = (event: SelectChangeEvent<number>) => {
    setSelectedPatient(event.target.value as number);
  };

  const handleAddSymptom = () => {
    if (newSymptom.trim()) {
      setSymptoms([...symptoms, newSymptom.trim()]);
      setNewSymptom('');
    }
  };

  const handleRemoveSymptom = (symptomToRemove: string) => {
    setSymptoms(symptoms.filter((symptom) => symptom !== symptomToRemove));
  };

  const handleAddRecommendation = () => {
    if (newRecommendation.trim()) {
      setRecommendations([...recommendations, newRecommendation.trim()]);
      setNewRecommendation('');
    }
  };

  const handleRemoveRecommendation = (recommendationToRemove: string) => {
    setRecommendations(
      recommendations.filter((recommendation) => recommendation !== recommendationToRemove)
    );
  };

  const handleSubmit = async () => {
    if (!selectedPatient || !diagnosis || symptoms.length === 0 || recommendations.length === 0) {
      setSnackbar({
        open: true,
        message: 'Please fill in all required fields',
        severity: 'error',
      });
      return;
    }

    try {
      await api.post(
        '/api/diagnosis/create',
        {
          patient_id: selectedPatient,
          diagnosis,
          symptoms,
          recommendations,
          is_physical: true,
        }
      );

      setSnackbar({
        open: true,
        message: 'Diagnosis report created successfully',
        severity: 'success',
      });

      // Reset form
      setSelectedPatient('');
      setDiagnosis('');
      setSymptoms([]);
      setRecommendations([]);
    } catch (error) {
      console.error('Error creating diagnosis:', error);
      setSnackbar({
        open: true,
        message: 'Failed to create diagnosis report',
        severity: 'error',
      });
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <Button 
          startIcon={<ArrowBack />} 
          onClick={() => navigate('/doctor/home')}
          variant="outlined"
          sx={{ mr: 2 }}
        >
          Back to Home
        </Button>
        <Typography variant="h5">
          Create Diagnosis Report
        </Typography>
      </Box>
      
      <Paper elevation={3} sx={{ p: 3 }}>
        <FormControl fullWidth sx={{ mb: 3 }}>
          <InputLabel>Select Patient</InputLabel>
          <Select
            value={selectedPatient}
            onChange={handlePatientChange}
            label="Select Patient"
          >
            {patients.map((patient) => (
              <MenuItem key={patient.id} value={patient.id}>
                {patient.title} {patient.first_name} {patient.last_name}
              </MenuItem>
            ))}
          </Select>
        </FormControl>

        <TextField
          fullWidth
          multiline
          rows={4}
          label="Diagnosis"
          value={diagnosis}
          onChange={(e) => setDiagnosis(e.target.value)}
          sx={{ mb: 3 }}
        />

        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle1" gutterBottom>
            Symptoms
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
            <TextField
              fullWidth
              label="Add Symptom"
              value={newSymptom}
              onChange={(e) => setNewSymptom(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  handleAddSymptom();
                }
              }}
            />
            <Button variant="contained" onClick={handleAddSymptom}>
              Add
            </Button>
          </Box>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
            {symptoms.map((symptom, index) => (
              <Chip
                key={index}
                label={symptom}
                onDelete={() => handleRemoveSymptom(symptom)}
              />
            ))}
          </Box>
        </Box>

        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle1" gutterBottom>
            Recommendations
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
            <TextField
              fullWidth
              label="Add Recommendation"
              value={newRecommendation}
              onChange={(e) => setNewRecommendation(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  handleAddRecommendation();
                }
              }}
            />
            <Button variant="contained" onClick={handleAddRecommendation}>
              Add
            </Button>
          </Box>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
            {recommendations.map((recommendation, index) => (
              <Chip
                key={index}
                label={recommendation}
                onDelete={() => handleRemoveRecommendation(recommendation)}
              />
            ))}
          </Box>
        </Box>

        <Button
          fullWidth
          variant="contained"
          size="large"
          onClick={handleSubmit}
          disabled={
            !selectedPatient ||
            !diagnosis ||
            symptoms.length === 0 ||
            recommendations.length === 0
          }
        >
          Create Diagnosis Report
        </Button>
      </Paper>

      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
      >
        <Alert
          onClose={() => setSnackbar({ ...snackbar, open: false })}
          severity={snackbar.severity}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default CreateDiagnosis; 
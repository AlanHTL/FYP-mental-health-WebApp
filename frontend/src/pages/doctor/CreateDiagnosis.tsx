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
  FormControlLabel,
  Switch,
  Grid,
  Divider,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle
} from '@mui/material';
import { ArrowBack, HealthAndSafety, Psychology, Add } from '@mui/icons-material';
import { useNavigate, useLocation } from 'react-router-dom';
import { api } from '../../config';

interface Patient {
  id: number;
  title: string;
  first_name: string;
  last_name: string;
}

// Common symptoms and recommendations for suggestion
const COMMON_PHYSICAL_SYMPTOMS = [
  'Fatigue', 'Headache', 'Fever', 'Cough', 'Shortness of breath',
  'Nausea', 'Vomiting', 'Dizziness', 'Chest pain', 'Back pain',
  'Joint pain', 'Muscle pain', 'Rash', 'Sore throat', 'Abdominal pain'
];

const COMMON_MENTAL_SYMPTOMS = [
  'Depressed mood', 'Anxiety', 'Insomnia', 'Low energy', 'Poor concentration',
  'Irritability', 'Mood swings', 'Social withdrawal', 'Loss of interest', 'Excessive worry',
  'Panic attacks', 'Racing thoughts', 'Memory problems', 'Appetite changes', 'Feelings of hopelessness'
];

const COMMON_PHYSICAL_RECOMMENDATIONS = [
  'Rest and adequate sleep', 'Stay hydrated', 'Take prescribed medication as directed',
  'Regular exercise', 'Follow up in 2 weeks', 'Complete blood work in 1 week',
  'Apply ice to affected area', 'Heat therapy for muscle pain', 'Monitor blood pressure daily',
  'Maintain a balanced diet', 'Avoid alcohol and tobacco'
];

const COMMON_MENTAL_RECOMMENDATIONS = [
  'Practice mindfulness meditation daily', 'Consider cognitive behavioral therapy',
  'Establish a regular sleep schedule', 'Engage in regular physical activity',
  'Maintain social connections', 'Avoid alcohol and drugs', 'Consider medication options with psychiatrist',
  'Keep a mood journal', 'Join a support group', 'Practice stress management techniques',
  'Schedule follow-up in 2 weeks'
];

const CreateDiagnosis = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const preSelectedPatientId = location.state?.selectedPatientId;
  const [patients, setPatients] = useState<Patient[]>([]);
  const [selectedPatient, setSelectedPatient] = useState<number | ''>('');
  const [diagnosis, setDiagnosis] = useState('');
  const [symptoms, setSymptoms] = useState<string[]>([]);
  const [newSymptom, setNewSymptom] = useState('');
  const [recommendations, setRecommendations] = useState<string[]>([]);
  const [newRecommendation, setNewRecommendation] = useState('');
  const [isPhysical, setIsPhysical] = useState(true);
  const [loading, setLoading] = useState(false);
  const [successDialog, setSuccessDialog] = useState(false);
  const [createdDiagnosisId, setCreatedDiagnosisId] = useState<string | null>(null);
  const [snackbar, setSnackbar] = useState({
    open: false,
    message: '',
    severity: 'success' as 'success' | 'error',
  });

  // Get suggested symptoms and recommendations based on diagnosis type
  const suggestedSymptoms = isPhysical ? COMMON_PHYSICAL_SYMPTOMS : COMMON_MENTAL_SYMPTOMS;
  const suggestedRecommendations = isPhysical ? COMMON_PHYSICAL_RECOMMENDATIONS : COMMON_MENTAL_RECOMMENDATIONS;

  useEffect(() => {
    fetchPatients();
  }, []);

  useEffect(() => {
    // If a patient ID was passed through navigation state, select that patient
    if (preSelectedPatientId && preSelectedPatientId !== selectedPatient) {
      setSelectedPatient(preSelectedPatientId);
    }
  }, [preSelectedPatientId, patients]);

  const fetchPatients = async () => {
    try {
      const response = await api.get('/api/doctors/linked-patients');
      setPatients(response.data);
    } catch (error) {
      console.error('Error fetching patients:', error);
      setSnackbar({
        open: true,
        message: 'Error fetching linked patients',
        severity: 'error',
      });
    }
  };

  const handlePatientChange = (event: SelectChangeEvent<number>) => {
    setSelectedPatient(event.target.value as number);
  };

  const handleAddSymptom = () => {
    if (newSymptom.trim() && !symptoms.includes(newSymptom.trim())) {
      setSymptoms([...symptoms, newSymptom.trim()]);
      setNewSymptom('');
    }
  };

  const handleRemoveSymptom = (symptomToRemove: string) => {
    setSymptoms(symptoms.filter((symptom) => symptom !== symptomToRemove));
  };

  const handleAddRecommendation = () => {
    if (newRecommendation.trim() && !recommendations.includes(newRecommendation.trim())) {
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

    setLoading(true);
    try {
      const response = await api.post(
        '/api/diagnosis/create',
        {
          patient_id: selectedPatient,
          diagnosis,
          symptoms,
          recommendations,
          is_physical: isPhysical,
        }
      );

      setCreatedDiagnosisId(response.data.id);
      setSuccessDialog(true);

      // Reset form
      setSelectedPatient('');
      setDiagnosis('');
      setSymptoms([]);
      setRecommendations([]);
      setIsPhysical(true);
    } catch (error) {
      console.error('Error creating diagnosis:', error);
      setSnackbar({
        open: true,
        message: 'Failed to create diagnosis report',
        severity: 'error',
      });
    } finally {
      setLoading(false);
    }
  };

  const handleViewPatientDetails = () => {
    const patientId = selectedPatient;
    setSuccessDialog(false);
    navigate(`/doctor/patients/${patientId}`);
  };

  const handleAddSuggestedSymptom = (symptom: string) => {
    if (!symptoms.includes(symptom)) {
      setSymptoms([...symptoms, symptom]);
    }
  };

  const handleAddSuggestedRecommendation = (recommendation: string) => {
    if (!recommendations.includes(recommendation)) {
      setRecommendations([...recommendations, recommendation]);
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
        <FormControlLabel
          control={
            <Switch
              checked={isPhysical}
              onChange={(e) => setIsPhysical(e.target.checked)}
              color="primary"
            />
          }
          label={
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              {isPhysical ? <HealthAndSafety color="primary" sx={{ mr: 1 }} /> : <Psychology color="secondary" sx={{ mr: 1 }} />}
              <Typography>
                {isPhysical ? "Physical Health Diagnosis" : "Mental Health Diagnosis"}
              </Typography>
            </Box>
          }
          sx={{ mb: 3 }}
        />

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

        <Grid container spacing={3}>
          {/* Symptoms Section */}
          <Grid item xs={12} md={6}>
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
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
                {symptoms.map((symptom, index) => (
                  <Chip
                    key={index}
                    label={symptom}
                    onDelete={() => handleRemoveSymptom(symptom)}
                  />
                ))}
              </Box>
              
              <Divider sx={{ my: 2 }} />
              <Typography variant="subtitle2" color="textSecondary" gutterBottom>
                Suggested Symptoms
              </Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                {suggestedSymptoms.map((symptom, index) => (
                  <Chip
                    key={index}
                    label={symptom}
                    variant="outlined"
                    onClick={() => handleAddSuggestedSymptom(symptom)}
                    icon={<Add fontSize="small" />}
                    clickable
                  />
                ))}
              </Box>
            </Box>
          </Grid>

          {/* Recommendations Section */}
          <Grid item xs={12} md={6}>
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
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 2 }}>
                {recommendations.map((recommendation, index) => (
                  <Chip
                    key={index}
                    label={recommendation}
                    onDelete={() => handleRemoveRecommendation(recommendation)}
                  />
                ))}
              </Box>
              
              <Divider sx={{ my: 2 }} />
              <Typography variant="subtitle2" color="textSecondary" gutterBottom>
                Suggested Recommendations
              </Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                {suggestedRecommendations.map((recommendation, index) => (
                  <Chip
                    key={index}
                    label={recommendation}
                    variant="outlined"
                    onClick={() => handleAddSuggestedRecommendation(recommendation)}
                    icon={<Add fontSize="small" />}
                    clickable
                  />
                ))}
              </Box>
            </Box>
          </Grid>
        </Grid>

        <Button
          fullWidth
          variant="contained"
          size="large"
          onClick={handleSubmit}
          disabled={
            loading ||
            !selectedPatient ||
            !diagnosis ||
            symptoms.length === 0 ||
            recommendations.length === 0
          }
          sx={{ mt: 3 }}
        >
          {loading ? <CircularProgress size={24} color="inherit" /> : 'Create Diagnosis Report'}
        </Button>
      </Paper>

      {/* Success Dialog */}
      <Dialog
        open={successDialog}
        onClose={() => setSuccessDialog(false)}
      >
        <DialogTitle>
          Diagnosis Report Created Successfully
        </DialogTitle>
        <DialogContent>
          <DialogContentText>
            The diagnosis report has been created and is now available to both you and the patient.
            Would you like to view the patient's details page?
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSuccessDialog(false)}>
            Create Another Report
          </Button>
          <Button onClick={handleViewPatientDetails} variant="contained" color="primary">
            View Patient Details
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar for notifications */}
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
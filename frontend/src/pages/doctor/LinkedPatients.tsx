import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Tabs,
  Tab,
  TextField,
  InputAdornment,
} from '@mui/material';
import { Search as SearchIcon, ArrowBack } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

interface Patient {
  id: number;
  title: string;
  first_name: string;
  last_name: string;
  email: string;
  phone_number: string;
  date_of_birth: string;
  sex: string;
}

interface DiagnosisReport {
  id: string;
  diagnosis: string;
  symptoms: string[];
  recommendations: string[];
  created_at: string;
  is_physical: boolean;
}

const LinkedPatients = () => {
  const navigate = useNavigate();
  const [patients, setPatients] = useState<Patient[]>([]);
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
  const [reports, setReports] = useState<DiagnosisReport[]>([]);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [tabValue, setTabValue] = useState(0);

  useEffect(() => {
    fetchPatients();
  }, []);

  const fetchPatients = async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) return;
      
      const response = await axios.get('http://localhost:8000/api/doctors/linked-patients', {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      setPatients(response.data);
    } catch (error: any) {
      console.error('Error fetching patients:', error);
      const errorMessage = error.response?.data?.detail || 'Failed to fetch linked patients';
      console.log('Error fetching linked patients:', errorMessage);
    }
  };

  const fetchPatientReports = async (patientId: number) => {
    try {
      const token = localStorage.getItem('token');
      if (!token) return;
      
      const response = await axios.get(`http://localhost:8000/api/doctors/patient-reports/${patientId}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      setReports(response.data.sort((a: DiagnosisReport, b: DiagnosisReport) => 
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      ));
    } catch (error: any) {
      console.error('Error fetching patient reports:', error);
      const errorMessage = error.response?.data?.detail || 'Failed to fetch patient reports';
      console.log('Error details:', errorMessage);
    }
  };

  const handleViewPatient = async (patient: Patient) => {
    setSelectedPatient(patient);
    await fetchPatientReports(patient.id);
    setDialogOpen(true);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const filteredPatients = patients.filter((patient) =>
    `${patient.id} ${patient.first_name} ${patient.last_name} ${patient.email}`
      .toLowerCase()
      .includes(searchTerm.toLowerCase())
  );

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
          Linked Patients
        </Typography>
      </Box>
      <TextField
        fullWidth
        margin="normal"
        placeholder="Search patients by ID, name, or email..."
        value={searchTerm}
        onChange={(e) => setSearchTerm(e.target.value)}
        InputProps={{
          startAdornment: (
            <InputAdornment position="start">
              <SearchIcon />
            </InputAdornment>
          ),
        }}
        sx={{ mb: 3 }}
      />
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>ID</TableCell>
              <TableCell>Name</TableCell>
              <TableCell>Email</TableCell>
              <TableCell>Phone</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredPatients.map((patient) => (
              <TableRow key={patient.id}>
                <TableCell>{patient.id}</TableCell>
                <TableCell>
                  {patient.title} {patient.first_name} {patient.last_name}
                </TableCell>
                <TableCell>{patient.email}</TableCell>
                <TableCell>{patient.phone_number}</TableCell>
                <TableCell>
                  <Button
                    variant="outlined"
                    size="small"
                    onClick={() => handleViewPatient(patient)}
                  >
                    View Details
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          Patient Details - {selectedPatient?.title} {selectedPatient?.first_name}{' '}
          {selectedPatient?.last_name}
        </DialogTitle>
        <DialogContent>
          <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
            <Tabs value={tabValue} onChange={(_, newValue) => setTabValue(newValue)}>
              <Tab label="Personal Information" />
              <Tab label="Diagnosis Reports" />
            </Tabs>
          </Box>

          {tabValue === 0 && selectedPatient && (
            <Box>
              <Typography variant="subtitle2" color="textSecondary" gutterBottom>
                Patient ID: {selectedPatient.id}
              </Typography>
              <Typography variant="body1" gutterBottom>
                Email: {selectedPatient.email}
              </Typography>
              <Typography variant="body1" gutterBottom>
                Phone: {selectedPatient.phone_number}
              </Typography>
              <Typography variant="body1" gutterBottom>
                Date of Birth: {selectedPatient.date_of_birth}
              </Typography>
              <Typography variant="body1" gutterBottom>
                Sex: {selectedPatient.sex}
              </Typography>
            </Box>
          )}

          {tabValue === 1 && (
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Date</TableCell>
                    <TableCell>Diagnosis</TableCell>
                    <TableCell>Type</TableCell>
                    <TableCell>Symptoms</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {reports.map((report) => (
                    <TableRow key={report.id}>
                      <TableCell>{formatDate(report.created_at)}</TableCell>
                      <TableCell>{report.diagnosis}</TableCell>
                      <TableCell>
                        {report.is_physical ? 'Physical Consultation' : 'Chatbot Diagnosis'}
                      </TableCell>
                      <TableCell>{report.symptoms.join(', ')}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default LinkedPatients; 
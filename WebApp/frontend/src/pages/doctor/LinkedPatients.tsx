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
  Chip,
  List,
  ListItem,
  Divider,
  ListItemText,
  Badge,
  CircularProgress,
} from '@mui/material';
import { 
  Search as SearchIcon, 
  ArrowBack, 
  Description, 
  LocalHospital, 
  Psychology,
  Assignment,
  Person
} from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { api } from '../../config';

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

interface Doctor {
  id: number;
  title: string;
  first_name: string;
  last_name: string;
  clinic_name: string;
  clinic_location: string;
  clinic_contact: string;
}

interface DiagnosisReport {
  id: string;
  diagnosis: string;
  details: string;
  symptoms: string[];
  recommendations: string[];
  created_at: string;
  is_physical: boolean;
  doctor_id?: number | null;
}

const LinkedPatients = () => {
  const navigate = useNavigate();
  const [patients, setPatients] = useState<Patient[]>([]);
  const [selectedPatient, setSelectedPatient] = useState<Patient | null>(null);
  const [reports, setReports] = useState<DiagnosisReport[]>([]);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [reportDialogOpen, setReportDialogOpen] = useState(false);
  const [selectedReport, setSelectedReport] = useState<DiagnosisReport | null>(null);
  const [reportCreator, setReportCreator] = useState<Doctor | null>(null);
  const [loadingCreator, setLoadingCreator] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [tabValue, setTabValue] = useState(0);

  useEffect(() => {
    fetchPatients();
  }, []);

  const fetchPatients = async () => {
    try {
      const response = await api.get('/api/doctors/linked-patients');
      setPatients(response.data);
    } catch (error: any) {
      console.error('Error fetching patients:', error);
      const errorMessage = error.response?.data?.detail || 'Failed to fetch linked patients';
      console.log('Error fetching linked patients:', errorMessage);
    }
  };

  const fetchPatientReports = async (patientId: number) => {
    try {
      const response = await api.get(`/api/doctors/patient-reports/${patientId}`);
      setReports(response.data.sort((a: DiagnosisReport, b: DiagnosisReport) => 
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      ));
    } catch (error: any) {
      console.error('Error fetching patient reports:', error);
      const errorMessage = error.response?.data?.detail || 'Failed to fetch patient reports';
      console.log('Error details:', errorMessage);
    }
  };

  const fetchDoctorInfo = async (doctorId: number) => {
    setLoadingCreator(true);
    try {
      const response = await api.get(`/api/doctors/${doctorId}`);
      setReportCreator(response.data);
    } catch (error: any) {
      console.error('Error fetching doctor info:', error);
    } finally {
      setLoadingCreator(false);
    }
  };

  const handleViewPatient = async (patient: Patient) => {
    setSelectedPatient(patient);
    await fetchPatientReports(patient.id);
    setDialogOpen(true);
  };

  const handleCreateReport = () => {
    if (selectedPatient) {
      navigate('/doctor/reports', { state: { selectedPatientId: selectedPatient.id } });
    }
  };

  const handleViewReport = async (report: DiagnosisReport) => {
    setSelectedReport(report);
    
    // Clear previous report creator
    setReportCreator(null);
    
    // Fetch doctor info if it's a doctor-created report
    if (report.is_physical && report.doctor_id) {
      await fetchDoctorInfo(report.doctor_id);
    }
    
    setReportDialogOpen(true);
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

  const renderReportCreator = () => {
    if (!selectedReport) return null;
    
    if (selectedReport.is_physical) {
      if (loadingCreator) {
        return (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 2 }}>
            <Person color="primary" />
            <Typography variant="body2">
              Loading creator information...
            </Typography>
            <CircularProgress size={16} />
          </Box>
        );
      }
      
      if (reportCreator) {
        return (
          <Box sx={{ display: 'flex', flexDirection: 'column', mt: 2, p: 2, bgcolor: '#f5f5f5', borderRadius: 1 }}>
            <Typography variant="subtitle2" gutterBottom sx={{ display: 'flex', alignItems: 'center' }}>
              <Person sx={{ mr: 1 }} /> Report created by:
            </Typography>
            <Typography variant="body2">
              {reportCreator.title} {reportCreator.first_name} {reportCreator.last_name}
            </Typography>
            <Typography variant="body2" color="textSecondary">
              Clinic: {reportCreator.clinic_name}
            </Typography>
            <Typography variant="body2" color="textSecondary">
              Location: {reportCreator.clinic_location}
            </Typography>
            <Typography variant="body2" color="textSecondary">
              Contact: {reportCreator.clinic_contact}
            </Typography>
          </Box>
        );
      }
      
      return (
        <Box sx={{ mt: 2, p: 2, bgcolor: '#f5f5f5', borderRadius: 1 }}>
          <Typography variant="body2">
            Report created by a healthcare professional.
          </Typography>
        </Box>
      );
    } else {
      return (
        <Box sx={{ display: 'flex', alignItems: 'center', mt: 2, p: 2, bgcolor: '#f0f7ff', borderRadius: 1 }}>
          <Psychology color="secondary" sx={{ mr: 1 }} />
          <Typography variant="body2">
            Report created by Dr. Mind, AI
          </Typography>
        </Box>
      );
    }
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

      {/* Patient Details Dialog */}
      <Dialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="h6">
              Patient Details - {selectedPatient?.title} {selectedPatient?.first_name}{' '}
              {selectedPatient?.last_name}
            </Typography>
            <Button 
              variant="contained" 
              color="primary" 
              startIcon={<Assignment />}
              onClick={handleCreateReport}
            >
              Create Report
            </Button>
          </Box>
        </DialogTitle>
        <DialogContent>
          <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
            <Tabs value={tabValue} onChange={(_, newValue) => setTabValue(newValue)}>
              <Tab label="Personal Information" />
              <Tab 
                label={
                  <Badge badgeContent={reports.length} color="primary">
                    Diagnosis Reports
                  </Badge>
                } 
              />
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
            <Box>
              {reports.length === 0 ? (
                <Typography variant="body1" sx={{ my: 2, textAlign: 'center' }}>
                  No diagnosis reports available for this patient.
                </Typography>
              ) : (
                <List sx={{ width: '100%' }}>
                  {reports.map((report, index) => (
                    <React.Fragment key={report.id}>
                      <ListItem 
                        alignItems="flex-start"
                        secondaryAction={
                          <Button 
                            variant="outlined" 
                            size="small"
                            onClick={() => handleViewReport(report)}
                          >
                            View Details
                          </Button>
                        }
                      >
                        <ListItemText
                          primary={
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              {report.is_physical ? 
                                <LocalHospital color="primary" /> : 
                                <Psychology color="secondary" />
                              }
                              <Typography variant="subtitle1">
                                {report.diagnosis}
                              </Typography>
                              <Typography variant="body2" color="textSecondary">
                                ({formatDate(report.created_at)})
                              </Typography>
                            </Box>
                          }
                          secondary={
                            <Box sx={{ mt: 1 }}>
                              <Typography variant="body2" color="textSecondary" gutterBottom>
                                Symptoms:
                              </Typography>
                              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                                {report.symptoms.map((symptom, i) => (
                                  <Chip 
                                    key={i} 
                                    label={symptom} 
                                    size="small" 
                                    variant="outlined"
                                  />
                                ))}
                              </Box>
                            </Box>
                          }
                        />
                      </ListItem>
                      {index < reports.length - 1 && <Divider component="li" />}
                    </React.Fragment>
                  ))}
                </List>
              )}
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      {/* Report Details Dialog */}
      <Dialog
        open={reportDialogOpen}
        onClose={() => setReportDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Description />
            <Typography variant="h6">
              Diagnosis Report - {formatDate(selectedReport?.created_at || '')}
            </Typography>
          </Box>
        </DialogTitle>
        <DialogContent>
          {selectedReport && (
            <Box sx={{ mt: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                <Chip
                  icon={selectedReport.is_physical ? <LocalHospital /> : <Psychology />}
                  label={selectedReport.is_physical ? 'Doctor Consultation' : 'Dr. Mind AI'}
                  color={selectedReport.is_physical ? 'primary' : 'secondary'}
                />
              </Box>

              {renderReportCreator()}

              <Typography variant="h6" gutterBottom sx={{ mt: 3 }}>
                Diagnosis
              </Typography>
              <Typography paragraph sx={{ pl: 2 }}>
                {selectedReport.diagnosis}
              </Typography>

              <Typography variant="h6" gutterBottom>
                Details
              </Typography>
              <Typography paragraph sx={{ pl: 2 }}>
                {selectedReport.details}
              </Typography>

              <Typography variant="h6" gutterBottom>
                Symptoms
              </Typography>
              <Box sx={{ mb: 2, pl: 2 }}>
                {selectedReport.symptoms.map((symptom, index) => (
                  <Chip
                    key={index}
                    label={symptom}
                    sx={{ mr: 1, mb: 1 }}
                  />
                ))}
              </Box>

              <Typography variant="h6" gutterBottom>
                Recommendations
              </Typography>
              <Box component="ul" sx={{ pl: 4 }}>
                {selectedReport.recommendations.map((recommendation, index) => (
                  <Typography component="li" key={index} paragraph>
                    {recommendation}
                  </Typography>
                ))}
              </Box>

              <Typography variant="body2" color="textSecondary" sx={{ mt: 2 }}>
                Report ID: {selectedReport.id}
              </Typography>
              <Typography variant="body2" color="textSecondary">
                Created: {formatDate(selectedReport.created_at)}
              </Typography>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setReportDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default LinkedPatients; 
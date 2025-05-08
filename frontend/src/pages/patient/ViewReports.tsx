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
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Chip,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  CircularProgress,
} from '@mui/material';
import { ArrowBack, ExpandMore, Person, Psychology, LocalHospital } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { api } from '../../config';

interface DiagnosisReport {
  id: string;
  diagnosis: string;
  details: string;
  symptoms: string[];
  recommendations: string[];
  created_at: string;
  is_physical: boolean;
  doctor_id: number | null;
  llm_analysis?: Record<string, any>;
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

const ViewReports = () => {
  const navigate = useNavigate();
  const [reports, setReports] = useState<DiagnosisReport[]>([]);
  const [selectedReport, setSelectedReport] = useState<DiagnosisReport | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [reportCreator, setReportCreator] = useState<Doctor | null>(null);
  const [loadingCreator, setLoadingCreator] = useState(false);

  useEffect(() => {
    fetchReports();
  }, []);

  const fetchReports = async () => {
    try {
      console.log("DEBUG: Fetching patient reports");
      const response = await api.get('/api/patients/reports');
      console.log("DEBUG: Received patient reports:", response.data);
      setReports(response.data.sort((a: DiagnosisReport, b: DiagnosisReport) => 
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      ));
    } catch (error) {
      console.error('ERROR: Error fetching reports:', error);
    }
  };

  const fetchDoctorInfo = async (doctorId: number) => {
    setLoadingCreator(true);
    try {
      const response = await api.get(`/api/doctors/${doctorId}`);
      setReportCreator(response.data);
    } catch (error) {
      console.error('ERROR: Error fetching doctor info:', error);
    } finally {
      setLoadingCreator(false);
    }
  };

  const handleViewReport = async (report: DiagnosisReport) => {
    console.log("DEBUG: Viewing report details:", report);
    setSelectedReport(report);

    // Clear previous report creator
    setReportCreator(null);
    
    // Fetch doctor info if it's a doctor-created report
    if (report.is_physical && report.doctor_id) {
      await fetchDoctorInfo(report.doctor_id);
    }
    
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

  const renderLLMAnalysis = (analysis: Record<string, any>) => {
    if (!analysis) return null;
    
    return (
      <Box sx={{ mt: 2 }}>
        <Accordion>
          <AccordionSummary expandIcon={<ExpandMore />}>
            <Typography>Additional AI Analysis</Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Box sx={{ 
              backgroundColor: '#f5f5f5', 
              p: 2, 
              borderRadius: 1,
              overflow: 'auto',
              maxHeight: '300px'
            }}>
              <pre style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
                {JSON.stringify(analysis, null, 2)}
              </pre>
            </Box>
          </AccordionDetails>
        </Accordion>
      </Box>
    );
  };

  const renderReportCreator = () => {
    if (!selectedReport) return null;
    
    if (selectedReport.is_physical) {
      if (loadingCreator) {
        return (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 2 }}>
            <Person color="primary" />
            <Typography variant="body2">
              Loading doctor information...
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

  return (
    <Box>
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
        <Button 
          startIcon={<ArrowBack />} 
          onClick={() => navigate('/patient/home')}
          variant="outlined"
          sx={{ mr: 2 }}
        >
          Back to Home
        </Button>
        <Typography variant="h5">
          Diagnosis Reports
        </Typography>
      </Box>
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Date</TableCell>
              <TableCell>Diagnosis</TableCell>
              <TableCell>Type</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {reports.length === 0 ? (
              <TableRow>
                <TableCell colSpan={4} align="center">
                  <Typography variant="body1" color="textSecondary" py={3}>
                    No diagnosis reports available
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              reports.map((report) => (
                <TableRow key={report.id}>
                  <TableCell>{formatDate(report.created_at)}</TableCell>
                  <TableCell>{report.diagnosis.length > 50 
                    ? `${report.diagnosis.substring(0, 50)}...` 
                    : report.diagnosis}
                  </TableCell>
                  <TableCell>
                    <Chip
                      icon={report.is_physical ? <LocalHospital /> : <Psychology />}
                      label={report.is_physical ? 'Doctor Consultation' : 'Dr. Mind AI'}
                      color={report.is_physical ? 'primary' : 'secondary'}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="outlined"
                      size="small"
                      onClick={() => handleViewReport(report)}
                    >
                      View Details
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
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
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            {selectedReport?.is_physical ? <LocalHospital color="primary" /> : <Psychology color="secondary" />}
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
              <Typography paragraph>{selectedReport.diagnosis}</Typography>

              <Typography variant="h6" gutterBottom>
                Details
              </Typography>
              <Typography paragraph sx={{ mb: 2 }}>
                {selectedReport.details}
              </Typography>

              <Typography variant="h6" gutterBottom>
                Symptoms
              </Typography>
              <Box sx={{ mb: 2 }}>
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
              <Box component="ul">
                {selectedReport.recommendations.map((recommendation, index) => (
                  <Typography component="li" key={index}>
                    {recommendation}
                  </Typography>
                ))}
              </Box>

              {/* Show LLM Analysis for AI-generated reports */}
              {!selectedReport.is_physical && selectedReport.llm_analysis && 
                renderLLMAnalysis(selectedReport.llm_analysis)
              }

              <Box sx={{ mt: 3, display: 'flex', alignItems: 'center' }}>
                <Typography variant="body2" color="textSecondary">
                  Report Type: 
                </Typography>
                <Chip
                  label={selectedReport.is_physical ? 'Doctor Consultation' : 'Dr. Mind AI'}
                  color={selectedReport.is_physical ? 'primary' : 'secondary'}
                  size="small"
                  sx={{ ml: 1 }}
                />
              </Box>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Close</Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ViewReports; 
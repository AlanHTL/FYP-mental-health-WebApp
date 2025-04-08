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
} from '@mui/material';
import { ArrowBack } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

interface DiagnosisReport {
  id: string;
  diagnosis: string;
  symptoms: string[];
  recommendations: string[];
  created_at: string;
  is_physical: boolean;
  doctor_id: number | null;
}

const ViewReports = () => {
  const navigate = useNavigate();
  const [reports, setReports] = useState<DiagnosisReport[]>([]);
  const [selectedReport, setSelectedReport] = useState<DiagnosisReport | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);

  useEffect(() => {
    fetchReports();
  }, []);

  const fetchReports = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get('http://localhost:8000/api/diagnosis/history', {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      setReports(response.data.sort((a: DiagnosisReport, b: DiagnosisReport) => 
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      ));
    } catch (error) {
      console.error('Error fetching reports:', error);
    }
  };

  const handleViewReport = (report: DiagnosisReport) => {
    setSelectedReport(report);
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
            {reports.map((report) => (
              <TableRow key={report.id}>
                <TableCell>{formatDate(report.created_at)}</TableCell>
                <TableCell>{report.diagnosis}</TableCell>
                <TableCell>
                  <Chip
                    label={report.is_physical ? 'Physical Consultation' : 'Chatbot Diagnosis'}
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
          Diagnosis Report - {formatDate(selectedReport?.created_at || '')}
        </DialogTitle>
        <DialogContent>
          {selectedReport && (
            <Box sx={{ mt: 2 }}>
              <Typography variant="h6" gutterBottom>
                Diagnosis
              </Typography>
              <Typography paragraph>{selectedReport.diagnosis}</Typography>

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

              <Typography variant="body2" color="textSecondary" sx={{ mt: 2 }}>
                Type: {selectedReport.is_physical ? 'Physical Consultation' : 'Chatbot Diagnosis'}
              </Typography>
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
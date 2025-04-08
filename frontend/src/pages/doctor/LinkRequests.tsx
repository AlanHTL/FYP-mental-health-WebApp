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
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Snackbar,
  Alert,
} from '@mui/material';
import { ArrowBack } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

interface LinkRequest {
  id: string;
  patient_id: number;
  status: string;
  created_at: string;
  patient: {
    title: string;
    first_name: string;
    last_name: string;
    email: string;
    phone_number: string;
    date_of_birth: string;
    sex: string;
  };
}

const LinkRequests = () => {
  const navigate = useNavigate();
  const [requests, setRequests] = useState<LinkRequest[]>([]);
  const [selectedRequest, setSelectedRequest] = useState<LinkRequest | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [snackbar, setSnackbar] = useState({
    open: false,
    message: '',
    severity: 'success' as 'success' | 'error',
  });

  useEffect(() => {
    fetchRequests();
  }, []);

  const fetchRequests = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get('http://localhost:8000/api/linkage/requests', {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      setRequests(response.data.sort((a: LinkRequest, b: LinkRequest) => 
        new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      ));
    } catch (error) {
      console.error('Error fetching link requests:', error);
      setSnackbar({
        open: true,
        message: 'Failed to fetch link requests',
        severity: 'error',
      });
    }
  };

  const handleAction = async (requestId: string, action: 'approve' | 'reject') => {
    try {
      const token = localStorage.getItem('token');
      if (!token) return;

      await axios.put(
        `http://localhost:8000/api/linkage/requests/${requestId}/${action}`,
        {},
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );
      
      setSnackbar({
        open: true,
        message: `Request ${action}d successfully`,
        severity: 'success',
      });
      
      // Refresh the requests list
      fetchRequests();
    } catch (error: any) {
      console.error(`Error ${action}ing request:`, error);
      const errorMessage = error.response?.data?.detail || `Failed to ${action} request`;
      setSnackbar({
        open: true,
        message: errorMessage,
        severity: 'error',
      });
    }
  };

  const handleViewDetails = (request: LinkRequest) => {
    setSelectedRequest(request);
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
          onClick={() => navigate('/doctor/home')}
          variant="outlined"
          sx={{ mr: 2 }}
        >
          Back to Home
        </Button>
        <Typography variant="h5">
          Link Requests
        </Typography>
      </Box>
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Date</TableCell>
              <TableCell>Patient ID</TableCell>
              <TableCell>Patient Name</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {requests.map((request) => (
              <TableRow key={request.id}>
                <TableCell>{formatDate(request.created_at)}</TableCell>
                <TableCell>{request.patient_id}</TableCell>
                <TableCell>
                  {request.patient ? (
                    `${request.patient.title} ${request.patient.first_name} ${request.patient.last_name}`
                  ) : (
                    'Patient information unavailable'
                  )}
                </TableCell>
                <TableCell>
                  <Chip
                    label={request.status.charAt(0).toUpperCase() + request.status.slice(1)}
                    color={
                      request.status === 'pending'
                        ? 'warning'
                        : request.status === 'approved'
                        ? 'success'
                        : 'error'
                    }
                    size="small"
                  />
                </TableCell>
                <TableCell>
                  <Box sx={{ display: 'flex', gap: 1 }}>
                    {request.patient && (
                      <Button
                        variant="outlined"
                        size="small"
                        onClick={() => handleViewDetails(request)}
                      >
                        View Details
                      </Button>
                    )}
                    {request.status === 'pending' && (
                      <>
                        <Button
                          variant="contained"
                          color="primary"
                          size="small"
                          onClick={() => handleAction(request.id, 'approve')}
                        >
                          Approve
                        </Button>
                        <Button
                          variant="contained"
                          color="error"
                          size="small"
                          onClick={() => handleAction(request.id, 'reject')}
                        >
                          Reject
                        </Button>
                      </>
                    )}
                  </Box>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      <Dialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Patient Details</DialogTitle>
        <DialogContent>
          {selectedRequest?.patient && (
            <Box sx={{ mt: 2 }}>
              <Typography variant="subtitle2" color="textSecondary" gutterBottom>
                Patient ID: {selectedRequest.patient_id}
              </Typography>
              <Typography variant="subtitle1" gutterBottom>
                Name: {selectedRequest.patient.title} {selectedRequest.patient.first_name}{' '}
                {selectedRequest.patient.last_name}
              </Typography>
              <Typography variant="body1" gutterBottom>
                Email: {selectedRequest.patient.email}
              </Typography>
              <Typography variant="body1" gutterBottom>
                Phone: {selectedRequest.patient.phone_number}
              </Typography>
              <Typography variant="body1" gutterBottom>
                Date of Birth: {selectedRequest.patient.date_of_birth}
              </Typography>
              <Typography variant="body1" gutterBottom>
                Sex: {selectedRequest.patient.sex}
              </Typography>
              <Typography variant="body1" gutterBottom>
                Request Date: {formatDate(selectedRequest.created_at)}
              </Typography>
              <Typography variant="body1" gutterBottom>
                Status: {selectedRequest.status.charAt(0).toUpperCase() + selectedRequest.status.slice(1)}
              </Typography>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Close</Button>
          {selectedRequest?.status === 'pending' && (
            <>
              <Button
                onClick={() => {
                  handleAction(selectedRequest.id, 'approve');
                  setDialogOpen(false);
                }}
                variant="contained"
                color="primary"
              >
                Approve
              </Button>
              <Button
                onClick={() => {
                  handleAction(selectedRequest.id, 'reject');
                  setDialogOpen(false);
                }}
                variant="contained"
                color="error"
              >
                Reject
              </Button>
            </>
          )}
        </DialogActions>
      </Dialog>

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

export default LinkRequests; 
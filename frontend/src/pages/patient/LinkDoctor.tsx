import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Grid,
  Button,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Snackbar,
  Alert,
  Divider,
  Tabs,
  Tab,
} from '@mui/material';
import { ArrowBack, CheckCircle, HourglassEmpty, Search } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';

interface Doctor {
  id: number;
  title: string;
  first_name: string;
  last_name: string;
  clinic_name: string;
  clinic_location: string;
  clinic_contact: string;
}

interface LinkRequest {
  id: string;
  doctor_id: number;
  status: string;
  created_at: string;
  doctor?: Doctor;
}

const LinkDoctor = () => {
  const navigate = useNavigate();
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedDoctor, setSelectedDoctor] = useState<Doctor | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [pendingRequests, setPendingRequests] = useState<LinkRequest[]>([]);
  const [approvedLinks, setApprovedLinks] = useState<LinkRequest[]>([]);
  const [activeTab, setActiveTab] = useState(0);
  const [snackbar, setSnackbar] = useState({
    open: false,
    message: '',
    severity: 'success' as 'success' | 'error',
  });

  useEffect(() => {
    fetchDoctors();
    fetchLinkRequests();
  }, []);

  const fetchLinkRequests = async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) return;

      const response = await axios.get('http://localhost:8000/api/linkage/my-requests', {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      
      // Get all doctor details for the requests
      const doctorIds: number[] = Array.from(new Set(response.data.map((req: LinkRequest) => req.doctor_id)));
      const doctorDetails = await Promise.all(
        doctorIds.map(async (id: number) => {
          try {
            const docResponse = await axios.get(`http://localhost:8000/api/doctors/${id}`, {
              headers: { Authorization: `Bearer ${token}` },
            });
            return docResponse.data;
          } catch (error) {
            console.error(`Error fetching doctor ${id}:`, error);
            return null;
          }
        })
      );

      // Create a map of doctor IDs to their details
      const doctorMap = doctorDetails.reduce((map: {[key: number]: Doctor}, doctor) => {
        if (doctor) map[doctor.id] = doctor;
        return map;
      }, {});

      // Add doctor details to requests
      const requestsWithDoctors = response.data.map((req: LinkRequest) => ({
        ...req,
        doctor: doctorMap[req.doctor_id]
      }));
      
      // Split into pending and approved
      const pending = requestsWithDoctors.filter((req: LinkRequest) => req.status === 'pending');
      const approved = requestsWithDoctors.filter((req: LinkRequest) => req.status === 'approved');
      
      setPendingRequests(pending);
      setApprovedLinks(approved);
    } catch (error) {
      console.error('Error fetching link requests:', error);
    }
  };

  const fetchDoctors = async () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) {
        setSnackbar({
          open: true,
          message: 'Please log in to view doctors',
          severity: 'error',
        });
        return;
      }

      const response = await axios.get('http://localhost:8000/api/doctors/', {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      setDoctors(response.data);
    } catch (error: any) {
      console.error('Error fetching doctors:', error);
      const errorMessage = error.response?.data?.detail || 'Failed to fetch doctors';
      setSnackbar({
        open: true,
        message: errorMessage,
        severity: 'error',
      });
    }
  };

  const handleSendRequest = async (doctor: Doctor) => {
    setSelectedDoctor(doctor);
    setDialogOpen(true);
  };

  const handleConfirmRequest = async () => {
    try {
      const token = localStorage.getItem('token');
      if (!selectedDoctor) return;
      
      const response = await axios.post(
        `http://localhost:8000/api/linkage/request/${selectedDoctor.id}`,
        {},  // Empty body since doctor_id is in URL
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );
      
      // Add new request to pending requests
      const newRequest = {
        ...response.data,
        doctor: selectedDoctor
      };
      setPendingRequests([...pendingRequests, newRequest]);
      
      setSnackbar({
        open: true,
        message: 'Link request sent successfully',
        severity: 'success',
      });
    } catch (error: any) {
      console.error('Error sending link request:', error);
      const errorMessage = error.response?.data?.detail || 'Failed to send link request';
      setSnackbar({
        open: true,
        message: errorMessage,
        severity: 'error',
      });
    }
    setDialogOpen(false);
  };

  // Get IDs of doctors that should be excluded from available list
  const excludedDoctorIds = [
    ...pendingRequests.map(req => req.doctor_id),
    ...approvedLinks.map(req => req.doctor_id)
  ];

  // Filter out doctors that already have requests or are linked
  const availableDoctors = doctors.filter(
    doctor => !excludedDoctorIds.includes(doctor.id)
  );

  // Filter available doctors based on search term
  const filteredDoctors = availableDoctors.filter((doctor) =>
    `${doctor.id} ${doctor.first_name} ${doctor.last_name} ${doctor.clinic_name}`
      .toLowerCase()
      .includes(searchTerm.toLowerCase())
  );

  const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
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
          Link with Doctor
        </Typography>
      </Box>
      
      <Tabs value={activeTab} onChange={handleTabChange} sx={{ mb: 3 }}>
        <Tab label="Available Doctors" />
        <Tab 
          label={
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <span>Linked Doctors</span>
              {approvedLinks.length > 0 && (
                <Box component="span" sx={{ 
                  ml: 1, 
                  bgcolor: 'success.main', 
                  color: 'white', 
                  borderRadius: '50%', 
                  width: 20, 
                  height: 20, 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'center',
                  fontSize: '0.75rem'
                }}>
                  {approvedLinks.length}
                </Box>
              )}
            </Box>
          } 
        />
        <Tab 
          label={
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <span>Pending Requests</span>
              {pendingRequests.length > 0 && (
                <Box component="span" sx={{ 
                  ml: 1, 
                  bgcolor: 'warning.main', 
                  color: 'white', 
                  borderRadius: '50%', 
                  width: 20, 
                  height: 20, 
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'center',
                  fontSize: '0.75rem'
                }}>
                  {pendingRequests.length}
                </Box>
              )}
            </Box>
          } 
        />
      </Tabs>
      
      {activeTab === 0 && (
        <>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 3 }}>
            <TextField
              fullWidth
              margin="normal"
              label="Search doctors by ID, name or clinic"
              placeholder="Enter doctor ID, name or clinic name..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              InputProps={{
                startAdornment: <Search color="action" sx={{ mr: 1 }} />,
              }}
            />
          </Box>
          
          {filteredDoctors.length === 0 ? (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <Typography variant="body1" color="textSecondary">
                No available doctors found
              </Typography>
            </Box>
          ) : (
            <Grid container spacing={3}>
              {filteredDoctors.map((doctor) => (
                <Grid item xs={12} sm={6} md={4} key={doctor.id}>
                  <Card>
                    <CardContent>
                      <Typography variant="subtitle2" color="textSecondary" gutterBottom>
                        Doctor ID: {doctor.id}
                      </Typography>
                      <Typography variant="h6">
                        {doctor.title} {doctor.first_name} {doctor.last_name}
                      </Typography>
                      <Typography color="textSecondary" gutterBottom>
                        {doctor.clinic_name}
                      </Typography>
                      <Typography variant="body2" paragraph>
                        Location: {doctor.clinic_location}
                      </Typography>
                      <Typography variant="body2" paragraph>
                        Contact: {doctor.clinic_contact}
                      </Typography>
                      <Button
                        variant="contained"
                        color="primary"
                        onClick={() => handleSendRequest(doctor)}
                      >
                        Send Link Request
                      </Button>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          )}
        </>
      )}
      
      {activeTab === 1 && (
        <>
          <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <CheckCircle color="success" sx={{ mr: 1 }} />
            Your Linked Doctors
          </Typography>
          
          {approvedLinks.length === 0 ? (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <Typography variant="body1" color="textSecondary">
                You don't have any linked doctors yet
              </Typography>
            </Box>
          ) : (
            <Grid container spacing={3}>
              {approvedLinks.map((link) => link.doctor && (
                <Grid item xs={12} sm={6} md={4} key={link.id}>
                  <Card sx={{ bgcolor: 'success.light' }}>
                    <CardContent>
                      <Typography variant="subtitle2" color="textSecondary" gutterBottom>
                        Doctor ID: {link.doctor.id}
                      </Typography>
                      <Typography variant="h6">
                        {link.doctor.title} {link.doctor.first_name} {link.doctor.last_name}
                      </Typography>
                      <Typography color="textSecondary" gutterBottom>
                        {link.doctor.clinic_name}
                      </Typography>
                      <Typography variant="body2" paragraph>
                        Location: {link.doctor.clinic_location}
                      </Typography>
                      <Typography variant="body2" paragraph>
                        Contact: {link.doctor.clinic_contact}
                      </Typography>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <Typography variant="body2" sx={{ fontWeight: 'bold', color: 'success.dark' }}>
                          Linked
                        </Typography>
                        <Typography variant="caption" color="textSecondary">
                          {new Date(link.created_at).toLocaleDateString()}
                        </Typography>
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          )}
        </>
      )}
      
      {activeTab === 2 && (
        <>
          <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <HourglassEmpty color="warning" sx={{ mr: 1 }} />
            Pending Link Requests
          </Typography>
          
          {pendingRequests.length === 0 ? (
            <Box sx={{ textAlign: 'center', py: 4 }}>
              <Typography variant="body1" color="textSecondary">
                You don't have any pending requests
              </Typography>
            </Box>
          ) : (
            <Grid container spacing={3}>
              {pendingRequests.map((request) => request.doctor && (
                <Grid item xs={12} sm={6} md={4} key={request.id}>
                  <Card sx={{ bgcolor: 'warning.light' }}>
                    <CardContent>
                      <Typography variant="subtitle2" color="textSecondary" gutterBottom>
                        Doctor ID: {request.doctor.id}
                      </Typography>
                      <Typography variant="h6">
                        {request.doctor.title} {request.doctor.first_name} {request.doctor.last_name}
                      </Typography>
                      <Typography color="textSecondary" gutterBottom>
                        {request.doctor.clinic_name}
                      </Typography>
                      <Typography variant="body2" paragraph>
                        Location: {request.doctor.clinic_location}
                      </Typography>
                      <Typography variant="body2" paragraph>
                        Contact: {request.doctor.clinic_contact}
                      </Typography>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <Typography variant="body2" sx={{ fontWeight: 'bold', color: 'warning.dark' }}>
                          Request Pending
                        </Typography>
                        <Typography variant="caption" color="textSecondary">
                          {new Date(request.created_at).toLocaleDateString()}
                        </Typography>
                      </Box>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          )}
        </>
      )}

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)}>
        <DialogTitle>Confirm Link Request</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to send a link request to {selectedDoctor?.title}{' '}
            {selectedDoctor?.first_name} {selectedDoctor?.last_name}?
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleConfirmRequest} variant="contained" color="primary">
            Confirm
          </Button>
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

export default LinkDoctor; 
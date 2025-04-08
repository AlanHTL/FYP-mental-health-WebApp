import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material';
import Register from './components/auth/Register';
import Login from './components/auth/Login';
import ProtectedRoute from './components/auth/ProtectedRoute';

// Patient pages
import PatientHome from './pages/patient/PatientHome';
import ChatbotDiagnosis from './pages/patient/ChatbotDiagnosis';
import LinkDoctor from './pages/patient/LinkDoctor';
import ViewReports from './pages/patient/ViewReports';

// Doctor pages
import DoctorHome from './pages/doctor/DoctorHome';
import LinkedPatients from './pages/doctor/LinkedPatients';
import LinkRequests from './pages/doctor/LinkRequests';
import CreateDiagnosis from './pages/doctor/CreateDiagnosis';

const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
});

function App() {
  return (
    <ThemeProvider theme={theme}>
      <Router>
        <div className="App">
          <Routes>
            {/* Public routes */}
            <Route path="/register" element={<Register />} />
            <Route path="/login" element={<Login />} />
            <Route path="/" element={<Navigate to="/login" replace />} />

            {/* Patient routes */}
            <Route
              path="/patient/home"
              element={
                <ProtectedRoute allowedRole="patient">
                  <PatientHome />
                </ProtectedRoute>
              }
            />
            <Route
              path="/patient/screening"
              element={
                <ProtectedRoute allowedRole="patient">
                  <ChatbotDiagnosis />
                </ProtectedRoute>
              }
            />
            <Route
              path="/patient/history"
              element={
                <ProtectedRoute allowedRole="patient">
                  <ViewReports />
                </ProtectedRoute>
              }
            />
            <Route
              path="/patient/doctors"
              element={
                <ProtectedRoute allowedRole="patient">
                  <LinkDoctor />
                </ProtectedRoute>
              }
            />

            {/* Doctor routes */}
            <Route
              path="/doctor/home"
              element={
                <ProtectedRoute allowedRole="doctor">
                  <DoctorHome />
                </ProtectedRoute>
              }
            />
            <Route
              path="/doctor/patients"
              element={
                <ProtectedRoute allowedRole="doctor">
                  <LinkedPatients />
                </ProtectedRoute>
              }
            />
            <Route
              path="/doctor/requests"
              element={
                <ProtectedRoute allowedRole="doctor">
                  <LinkRequests />
                </ProtectedRoute>
              }
            />
            <Route
              path="/doctor/reports"
              element={
                <ProtectedRoute allowedRole="doctor">
                  <CreateDiagnosis />
                </ProtectedRoute>
              }
            />

            {/* Catch all route */}
            <Route path="*" element={<Navigate to="/login" replace />} />
          </Routes>
        </div>
      </Router>
    </ThemeProvider>
  );
}

export default App;

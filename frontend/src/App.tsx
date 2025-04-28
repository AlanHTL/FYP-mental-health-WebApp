import React, { useState, ReactNode } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { ThemeProvider, createTheme, styled } from '@mui/material';
import { Box, Drawer, List, ListItem, ListItemIcon, ListItemText, Typography, useMediaQuery, IconButton, Divider } from '@mui/material';
import { 
  Chat as ChatIcon, 
  History as HistoryIcon, 
  Person as PersonIcon, 
  PeopleAlt as PeopleAltIcon, 
  NotificationsActive as NotificationsIcon, 
  Assignment as AssignmentIcon, 
  Menu as MenuIcon,
  Logout as LogoutIcon
} from '@mui/icons-material';
import Register from './components/auth/Register';
import Login from './components/auth/Login';
import ProtectedRoute from './components/auth/ProtectedRoute';
import TestConnection from './components/TestConnection';

// Patient pages
import ChatbotDiagnosis from './pages/patient/ChatbotDiagnosis';
import LinkDoctor from './pages/patient/LinkDoctor';
import ViewReports from './pages/patient/ViewReports';

// Doctor pages
import LinkedPatients from './pages/doctor/LinkedPatients';
import LinkRequests from './pages/doctor/LinkRequests';
import CreateDiagnosis from './pages/doctor/CreateDiagnosis';

// Create a calming theme with soft colors
const theme = createTheme({
  palette: {
    primary: {
      main: '#5b8cb8', // Soft blue
      light: '#84a9d1',
      dark: '#3b6ea0',
    },
    secondary: {
      main: '#6b9e78', // Soft green
      light: '#8fb59a',
      dark: '#4a7d57',
    },
    background: {
      default: '#f8f9fa',
      paper: '#ffffff',
    },
    text: {
      primary: '#2c3e50',
      secondary: '#5d6d7e',
    },
  },
  typography: {
    fontFamily: '"Poppins", "Roboto", "Helvetica", "Arial", sans-serif',
    h5: {
      fontWeight: 600,
    },
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          textTransform: 'none',
          boxShadow: 'none',
          '&:hover': {
            boxShadow: '0px 2px 4px rgba(0, 0, 0, 0.1)',
          },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        rounded: {
          borderRadius: 12,
        },
      },
    },
  },
});

// Sidebar width
const drawerWidth = 240;

// Define prop types for components
interface SidebarProps {
  open: boolean;
  onClose: () => void;
  userType: 'patient' | 'doctor';
}

interface LayoutProps {
  children: ReactNode;
}

// Styled Main Content component
const Main = styled('main', { shouldForwardProp: (prop) => prop !== 'open' })<{
  open?: boolean;
}>(({ theme, open }) => ({
  flexGrow: 1,
  padding: theme.spacing(3),
  transition: theme.transitions.create('margin', {
    easing: theme.transitions.easing.sharp,
    duration: theme.transitions.duration.leavingScreen,
  }),
  marginLeft: 0,
  ...(open && {
    transition: theme.transitions.create('margin', {
      easing: theme.transitions.easing.easeOut,
      duration: theme.transitions.duration.enteringScreen,
    }),
    marginLeft: drawerWidth,
  }),
}));

// Navigation items with icons
const patientNavItems = [
  { text: 'Mental Health Chat', icon: <ChatIcon />, path: '/patient/screening' },
  { text: 'My Reports', icon: <HistoryIcon />, path: '/patient/history' },
  { text: 'Connect with Doctors', icon: <PersonIcon />, path: '/patient/doctors' },
];

const doctorNavItems = [
  { text: 'My Patients', icon: <PeopleAltIcon />, path: '/doctor/patients' },
  { text: 'Connection Requests', icon: <NotificationsIcon />, path: '/doctor/requests' },
  { text: 'Create Diagnosis', icon: <AssignmentIcon />, path: '/doctor/reports' },
];

// Sidebar Component
const Sidebar = ({ open, onClose, userType }: SidebarProps) => {
  const location = useLocation();
  const navigate = useNavigate();
  const navItems = userType === 'patient' ? patientNavItems : doctorNavItems;
  
  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/login');
  };
  
  return (
    <Drawer
      variant="persistent"
      anchor="left"
      open={open}
      sx={{
        width: drawerWidth,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: drawerWidth,
          boxSizing: 'border-box',
          backgroundColor: '#f8fafc',
          borderRight: '1px solid rgba(0, 0, 0, 0.08)',
          display: 'flex',
          flexDirection: 'column',
          height: '100%',
        },
      }}
    >
      <Box sx={{ p: 2, display: 'flex', flexDirection: 'column', alignItems: 'center', mb: 2 }}>
        <Typography variant="h5" color="primary" sx={{ fontWeight: 600, letterSpacing: 0.5 }}>
          Mental Health App
        </Typography>
      </Box>
      <Divider sx={{ mb: 2 }} />
      <List sx={{ flexGrow: 1 }}>
        {navItems.map((item, index) => (
          <ListItem 
            button 
            key={`nav-item-${index}-${item.path}`}
            component="a" 
            href={item.path} 
            selected={location.pathname === item.path}
            sx={{
              borderRadius: '8px',
              mx: 1,
              mb: 0.5,
              '&.Mui-selected': {
                backgroundColor: 'primary.light',
                color: 'white',
                '& .MuiListItemIcon-root': {
                  color: 'white',
                },
                '&:hover': {
                  backgroundColor: 'primary.main',
                },
              },
              '&:hover': {
                backgroundColor: 'rgba(91, 140, 184, 0.08)',
              }
            }}
          >
            <ListItemIcon sx={{ color: location.pathname === item.path ? 'white' : 'primary.main' }}>
              {item.icon}
            </ListItemIcon>
            <ListItemText primary={item.text} />
          </ListItem>
        ))}
      </List>
      
      {/* Logout Button at the bottom */}
      <Box sx={{ p: 2 }}>
        <Divider sx={{ mb: 2 }} />
        <ListItem 
          button 
          onClick={handleLogout}
          key="logout-button"
          sx={{
            borderRadius: '8px',
            mx: 1,
            mb: 0.5,
            '&:hover': {
              backgroundColor: 'rgba(220, 0, 78, 0.08)',
            }
          }}
        >
          <ListItemIcon sx={{ color: 'error.main' }}>
            <LogoutIcon />
          </ListItemIcon>
          <ListItemText primary="Logout" sx={{ color: 'error.main' }} />
        </ListItem>
      </Box>
    </Drawer>
  );
};

// Layout Component that includes the sidebar
const Layout = ({ children }: LayoutProps) => {
  const [open, setOpen] = useState(true);
  const isSmallScreen = useMediaQuery(theme.breakpoints.down('md'));
  const location = useLocation();
  
  // Determine user type from path
  const userType = location.pathname.includes('/patient/') ? 'patient' : 'doctor';
  
  // Close drawer on small screens by default
  React.useEffect(() => {
    if (isSmallScreen) {
      setOpen(false);
    } else {
      setOpen(true);
    }
  }, [isSmallScreen]);

  // Don't show sidebar on login or register pages
  const isAuthPage = location.pathname === '/login' || location.pathname === '/register' || location.pathname === '/';
  
  if (isAuthPage) {
    return <>{children}</>;
  }

  return (
    <Box sx={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      {!isAuthPage && (
        <>
          <Sidebar open={open} onClose={() => setOpen(false)} userType={userType} />
          {isSmallScreen && (
            <IconButton
              color="primary"
              aria-label="open drawer"
              onClick={() => setOpen(!open)}
              edge="start"
              sx={{ position: 'fixed', top: 12, left: open ? drawerWidth + 10 : 10, zIndex: 1100 }}
            >
              <MenuIcon />
            </IconButton>
          )}
        </>
      )}
      <Main 
        open={!isAuthPage && open && !isSmallScreen} 
        sx={{ 
          flexGrow: 1, 
          p: 3, 
          width: '100%',
          marginLeft: open && !isSmallScreen ? '0 !important' : 0,
          overflow: 'auto'
        }}
      >
        {/* Add padding at top for mobile menu button */}
        {isSmallScreen && !isAuthPage && <Box sx={{ height: 48 }} />}
        {children}
      </Main>
    </Box>
  );
};

function App() {
  return (
    <ThemeProvider theme={theme}>
      <Router>
        <Layout>
          <Routes>
            {/* Public routes */}
            <Route path="/register" element={<Register />} />
            <Route path="/login" element={<Login />} />
            <Route path="/" element={<Navigate to="/login" replace />} />

            {/* Patient routes - using chatbot as homepage */}
            <Route
              path="/patient"
              element={<Navigate to="/patient/screening" replace />}
            />
            <Route
              path="/patient/home"
              element={<Navigate to="/patient/screening" replace />}
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

            {/* Doctor routes - using patients as homepage */}
            <Route
              path="/doctor"
              element={<Navigate to="/doctor/patients" replace />}
            />
            <Route
              path="/doctor/home"
              element={<Navigate to="/doctor/patients" replace />}
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

            {/* Test Connection route */}
            <Route path="/test" element={<TestConnection />} />

            {/* Catch all route */}
            <Route path="*" element={<Navigate to="/login" replace />} />
          </Routes>
        </Layout>
      </Router>
    </ThemeProvider>
  );
}

export default App;

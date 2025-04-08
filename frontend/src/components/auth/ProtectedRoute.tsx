import React, { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import axios from 'axios';

interface ProtectedRouteProps {
  children: React.ReactNode;
  allowedRole: 'patient' | 'doctor';
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, allowedRole }) => {
  const [isLoading, setIsLoading] = useState(true);
  const [userRole, setUserRole] = useState<string | null>(null);

  useEffect(() => {
    const verifyUser = async () => {
      const token = localStorage.getItem('token');
      if (!token) {
        setUserRole(null);
        setIsLoading(false);
        return;
      }

      try {
        // Try both patient and doctor endpoints
        const headers = { Authorization: `Bearer ${token}` };
        let response;
        
        try {
          response = await axios.get('http://localhost:8000/api/patients/me', { headers });
          setUserRole('patient');
        } catch (error: any) {
          if (error.response?.status === 403) {
            // If forbidden as patient, try doctor endpoint
            response = await axios.get('http://localhost:8000/api/doctors/me', { headers });
            setUserRole('doctor');
          } else {
            throw error;
          }
        }
      } catch (error) {
        console.error('Token verification failed:', error);
        localStorage.removeItem('token');
        setUserRole(null);
      }
      setIsLoading(false);
    };

    verifyUser();
  }, []);

  if (isLoading) {
    return <div>Loading...</div>;
  }

  if (!userRole) {
    return <Navigate to="/login" replace />;
  }

  if (userRole !== allowedRole) {
    return <Navigate to={`/${userRole}/home`} replace />;
  }

  return <>{children}</>;
};

export default ProtectedRoute; 
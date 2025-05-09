import React from 'react';
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
  Divider,
  Link,
  Card,
  CardContent,
  Grid,
} from '@mui/material';
import { ArrowBack, Call, AccessTime, Language } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';

interface HelpOrganization {
  name: string;
  service: string;
  hours: string;
  hotline: string;
  website?: string;
}

const helpOrganizations: HelpOrganization[] = [
  {
    name: '明愛向晴軒',
    service: '熱線服務 (家庭危機)',
    hours: '24小時',
    hotline: '18288',
  },
  {
    name: '醫院管理局',
    service: '精神健康專線',
    hours: '24小時',
    hotline: '24667350',
    website: 'https://www.ha.org.hk',
  },
  {
    name: '社會福利署',
    service: '熱線服務',
    hours: '24小時',
    hotline: '23432255',
    website: 'https://www.swd.gov.hk',
  },
  {
    name: '生命熱線',
    service: '熱線服務',
    hours: '24小時',
    hotline: '23820000',
    website: 'https://www.sps.org.hk',
  },
  {
    name: '香港撒瑪利亞防止自殺會',
    service: '熱線服務',
    hours: '24小時',
    hotline: '23892222',
    website: 'https://www.help4suicide.com.hk',
  },
  {
    name: '撒瑪利亞會',
    service: '中文及多種語言防止自殺熱線',
    hours: '24小時',
    hotline: '28960000',
    website: 'https://samaritan.org.hk',
  },
];

const Help: React.FC = () => {
  const navigate = useNavigate();

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
          Mental Health Help Resources
        </Typography>
      </Box>

      <Paper elevation={3} sx={{ p: 3, mb: 4 }}>
        <Typography variant="h6" gutterBottom>
          Crisis Support Hotlines
        </Typography>
        <Typography paragraph>
          If you are experiencing a mental health crisis or need immediate assistance, please consider contacting one of the following resources:
        </Typography>

        <Grid container spacing={3}>
          {helpOrganizations.map((org, index) => (
            <Grid item xs={12} sm={6} md={4} key={index}>
              <Card elevation={2} sx={{ height: '100%' }}>
                <CardContent>
                  <Typography variant="h6" component="div" gutterBottom>
                    {org.name}
                  </Typography>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    {org.service}
                  </Typography>
                  <Divider sx={{ my: 1 }} />
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                    <Call color="primary" sx={{ mr: 1 }} />
                    <Typography variant="body1">
                      <Link href={`tel:${org.hotline}`} underline="none">
                        {org.hotline}
                      </Link>
                    </Typography>
                  </Box>
                  <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                    <AccessTime color="primary" sx={{ mr: 1 }} />
                    <Typography variant="body2">
                      {org.hours}
                    </Typography>
                  </Box>
                  {org.website && (
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      <Language color="primary" sx={{ mr: 1 }} />
                      <Typography variant="body2">
                        <Link href={org.website} target="_blank" rel="noopener noreferrer">
                          Visit Website
                        </Link>
                      </Typography>
                    </Box>
                  )}
                </CardContent>
              </Card>
            </Grid>
          ))}
        </Grid>
      </Paper>

      <Paper elevation={3} sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          Important Information
        </Typography>
        <Typography paragraph>
          • In case of emergency, call 999 for immediate assistance.
        </Typography>
        <Typography paragraph>
          • These hotlines provide confidential support for individuals experiencing mental health issues or emotional distress.
        </Typography>
        <Typography paragraph>
          • Don't hesitate to reach out if you're feeling overwhelmed or if you just need someone to talk to.
        </Typography>
        <Typography>
          • Remember, seeking help is a sign of strength, not weakness.
        </Typography>
      </Paper>
    </Box>
  );
};

export default Help; 
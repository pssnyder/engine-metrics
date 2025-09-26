import React from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  Box,
  IconButton,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import {
  Dashboard as DashboardIcon,
  CloudUpload,
  Search,
  Compare,
} from '@mui/icons-material';

function Header() {
  const navigate = useNavigate();

  return (
    <AppBar position="fixed">
      <Toolbar>
        <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
          🏆 Engine Metrics Agent
        </Typography>
        
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            color="inherit"
            startIcon={<DashboardIcon />}
            onClick={() => navigate('/')}
          >
            Dashboard
          </Button>
          
          <Button
            color="inherit"
            startIcon={<CloudUpload />}
            onClick={() => navigate('/upload')}
          >
            Upload Data
          </Button>
          
          <Button
            color="inherit"
            startIcon={<Search />}
            onClick={() => navigate('/query')}
          >
            AI Query
          </Button>
          
          <Button
            color="inherit"
            startIcon={<Compare />}
            onClick={() => navigate('/compare')}
          >
            Compare Engines
          </Button>
        </Box>
      </Toolbar>
    </AppBar>
  );
}

export default Header;
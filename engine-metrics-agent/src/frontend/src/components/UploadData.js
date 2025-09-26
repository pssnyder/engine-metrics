import React, { useState } from 'react';
import {
  Container,
  Typography,
  Card,
  CardContent,
  Box,
  Button,
  LinearProgress,
  Alert,
  Chip,
  Grid,
} from '@mui/material';
import {
  CloudUpload,
  CheckCircle,
  Error,
  Description,
} from '@mui/icons-material';

function UploadData() {
  const [dragOver, setDragOver] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploading, setUploading] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [uploadStatus, setUploadStatus] = useState(null);

  const handleDragOver = (e) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setDragOver(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const files = Array.from(e.dataTransfer.files);
    handleFiles(files);
  };

  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files);
    handleFiles(files);
  };

  const handleFiles = (files) => {
    // Filter for supported file types
    const supportedFiles = files.filter(file => 
      file.name.endsWith('.pgn') || 
      file.name.endsWith('.json') || 
      file.name.endsWith('.md')
    );

    if (supportedFiles.length === 0) {
      setUploadStatus({
        type: 'error',
        message: 'No supported files found. Please upload PGN, JSON, or MD files.'
      });
      return;
    }

    // Simulate file upload
    setUploading(true);
    setUploadProgress(0);
    setUploadStatus(null);

    const interval = setInterval(() => {
      setUploadProgress(prev => {
        if (prev >= 100) {
          clearInterval(interval);
          setUploading(false);
          setUploadedFiles(prev => [...prev, ...supportedFiles]);
          setUploadStatus({
            type: 'success',
            message: `Successfully uploaded ${supportedFiles.length} file(s)`
          });
          return 100;
        }
        return prev + 10;
      });
    }, 200);
  };

  const getFileIcon = (fileName) => {
    if (fileName.endsWith('.pgn')) return '♟️';
    if (fileName.endsWith('.json')) return '📊';
    if (fileName.endsWith('.md')) return '📝';
    return '📄';
  };

  const getFileType = (fileName) => {
    if (fileName.endsWith('.pgn')) return 'PGN Game Data';
    if (fileName.endsWith('.json')) return 'JSON Analysis';
    if (fileName.endsWith('.md')) return 'Markdown Report';
    return 'Unknown';
  };

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Typography variant="h4" gutterBottom>
        Upload Chess Engine Data
      </Typography>
      
      <Typography variant="body1" color="textSecondary" sx={{ mb: 4 }}>
        Upload your PGN game files, JSON analysis results, and Markdown reports 
        to enhance the AI's knowledge base.
      </Typography>

      {/* Upload Area */}
      <Card 
        sx={{ 
          mb: 4,
          border: dragOver ? '2px solid #1976d2' : '2px dashed #555',
          backgroundColor: dragOver ? 'rgba(25, 118, 210, 0.1)' : 'inherit',
          transition: 'all 0.3s ease'
        }}
      >
        <CardContent>
          <Box
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            sx={{
              textAlign: 'center',
              py: 6,
              cursor: 'pointer'
            }}
            onClick={() => document.getElementById('file-input').click()}
          >
            <CloudUpload sx={{ fontSize: 64, color: '#1976d2', mb: 2 }} />
            <Typography variant="h6" gutterBottom>
              Drag & drop files here
            </Typography>
            <Typography variant="body2" color="textSecondary" sx={{ mb: 2 }}>
              or click to browse files
            </Typography>
            <Button variant="contained" component="span">
              Choose Files
            </Button>
            <input
              id="file-input"
              type="file"
              multiple
              accept=".pgn,.json,.md"
              style={{ display: 'none' }}
              onChange={handleFileSelect}
            />
          </Box>
        </CardContent>
      </Card>

      {/* Upload Progress */}
      {uploading && (
        <Card sx={{ mb: 4 }}>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Uploading Files...
            </Typography>
            <LinearProgress 
              variant="determinate" 
              value={uploadProgress} 
              sx={{ mb: 1 }}
            />
            <Typography variant="body2" color="textSecondary">
              {uploadProgress}% complete
            </Typography>
          </CardContent>
        </Card>
      )}

      {/* Upload Status */}
      {uploadStatus && (
        <Alert 
          severity={uploadStatus.type} 
          sx={{ mb: 4 }}
          icon={uploadStatus.type === 'success' ? <CheckCircle /> : <Error />}
        >
          {uploadStatus.message}
        </Alert>
      )}

      {/* Uploaded Files List */}
      {uploadedFiles.length > 0 && (
        <Card>
          <CardContent>
            <Typography variant="h6" gutterBottom>
              Uploaded Files ({uploadedFiles.length})
            </Typography>
            <Grid container spacing={2}>
              {uploadedFiles.map((file, index) => (
                <Grid item xs={12} key={index}>
                  <Box 
                    sx={{ 
                      display: 'flex', 
                      alignItems: 'center', 
                      p: 2, 
                      backgroundColor: '#2a2a2a',
                      borderRadius: 1,
                      gap: 2
                    }}
                  >
                    <Typography variant="h6">
                      {getFileIcon(file.name)}
                    </Typography>
                    <Box sx={{ flexGrow: 1 }}>
                      <Typography variant="body1">
                        {file.name}
                      </Typography>
                      <Typography variant="body2" color="textSecondary">
                        {(file.size / 1024).toFixed(1)} KB
                      </Typography>
                    </Box>
                    <Chip 
                      label={getFileType(file.name)} 
                      size="small" 
                      color="primary"
                    />
                    <CheckCircle color="success" />
                  </Box>
                </Grid>
              ))}
            </Grid>
          </CardContent>
        </Card>
      )}

      {/* Supported File Types Info */}
      <Card sx={{ mt: 4 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Supported File Types
          </Typography>
          <Grid container spacing={2}>
            <Grid item xs={12} md={4}>
              <Box sx={{ textAlign: 'center', p: 2 }}>
                <Typography variant="h4">♟️</Typography>
                <Typography variant="h6">PGN Files</Typography>
                <Typography variant="body2" color="textSecondary">
                  Chess game records from Arena GUI, engine-tester battles, and tournaments
                </Typography>
              </Box>
            </Grid>
            <Grid item xs={12} md={4}>
              <Box sx={{ textAlign: 'center', p: 2 }}>
                <Typography variant="h4">📊</Typography>
                <Typography variant="h6">JSON Files</Typography>
                <Typography variant="body2" color="textSecondary">
                  Puzzle analysis results, ELO estimates, and performance metrics
                </Typography>
              </Box>
            </Grid>
            <Grid item xs={12} md={4}>
              <Box sx={{ textAlign: 'center', p: 2 }}>
                <Typography variant="h4">📝</Typography>
                <Typography variant="h6">Markdown Files</Typography>
                <Typography variant="body2" color="textSecondary">
                  Analysis reports, documentation, and structured findings
                </Typography>
              </Box>
            </Grid>
          </Grid>
        </CardContent>
      </Card>
    </Container>
  );
}

export default UploadData;
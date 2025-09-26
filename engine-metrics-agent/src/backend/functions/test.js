const functions = require('firebase-functions');

// Simple test function to verify basic functionality
exports.test = functions.https.onRequest((req, res) => {
  res.status(200).json({
    message: 'Functions are working!',
    timestamp: new Date().toISOString()
  });
});

console.log('Functions loaded successfully');
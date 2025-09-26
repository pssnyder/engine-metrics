const admin = require('firebase-admin');
const multer = require('multer');

// Configure multer for file uploads
const upload = multer({
  storage: multer.memoryStorage(),
  limits: {
    fileSize: 50 * 1024 * 1024, // 50MB limit
  },
  fileFilter: (req, file, cb) => {
    const allowedTypes = ['.pgn', '.json', '.md'];
    const fileExt = file.originalname.toLowerCase().slice(-4);
    
    if (allowedTypes.some(ext => file.originalname.toLowerCase().endsWith(ext))) {
      cb(null, true);
    } else {
      cb(new Error('Only PGN, JSON, and MD files are allowed'), false);
    }
  }
});

async function uploadHandler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    // Handle file upload
    upload.array('files')(req, res, async (err) => {
      if (err) {
        console.error('Upload error:', err);
        return res.status(400).json({ error: err.message });
      }

      if (!req.files || req.files.length === 0) {
        return res.status(400).json({ error: 'No files uploaded' });
      }

      const uploadResults = [];
      const bucket = admin.storage().bucket();

      for (const file of req.files) {
        try {
          // Generate unique file path
          const timestamp = Date.now();
          const userId = req.body.userId || 'anonymous';
          const fileExt = getFileExtension(file.originalname);
          const fileName = `${timestamp}_${file.originalname}`;
          const filePath = `users/${userId}/${fileName}`;

          // Upload to Cloud Storage
          const cloudFile = bucket.file(filePath);
          const stream = cloudFile.createWriteStream({
            metadata: {
              contentType: file.mimetype,
              metadata: {
                originalName: file.originalname,
                uploadedBy: userId,
                uploadedAt: new Date().toISOString()
              }
            }
          });

          await new Promise((resolve, reject) => {
            stream.on('error', reject);
            stream.on('finish', resolve);
            stream.end(file.buffer);
          });

          // Store metadata in Firestore
          const uploadDoc = await admin.firestore()
            .collection('uploads')
            .add({
              fileName: file.originalname,
              filePath: filePath,
              fileSize: file.size,
              fileType: fileExt,
              mimeType: file.mimetype,
              userId: userId,
              uploadedAt: admin.firestore.FieldValue.serverTimestamp(),
              status: 'uploaded',
              processed: false
            });

          uploadResults.push({
            uploadId: uploadDoc.id,
            fileName: file.originalname,
            fileSize: file.size,
            fileType: fileExt,
            status: 'success'
          });

        } catch (fileError) {
          console.error('Error uploading file:', fileError);
          uploadResults.push({
            fileName: file.originalname,
            status: 'error',
            error: fileError.message
          });
        }
      }

      res.status(200).json({
        message: 'Upload completed',
        results: uploadResults,
        totalFiles: req.files.length,
        successfulUploads: uploadResults.filter(r => r.status === 'success').length
      });

    });

  } catch (error) {
    console.error('Upload handler error:', error);
    res.status(500).json({ error: 'Internal server error' });
  }
}

function getFileExtension(filename) {
  if (filename.toLowerCase().endsWith('.pgn')) return 'pgn';
  if (filename.toLowerCase().endsWith('.json')) return 'json';
  if (filename.toLowerCase().endsWith('.md')) return 'md';
  return 'unknown';
}

module.exports = {
  uploadHandler
};
"""
Chess Engine Metrics AI - Flask Application
Serves AI functionality via REST API
"""

import os
import sys
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up authentication
os.environ.setdefault('GOOGLE_CLOUD_PROJECT', 'chess-engine-metrics-agent')

from query_processor import ChessEngineQueryProcessor
from knowledge_base import ChessEngineKnowledgeBase

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend communication

# Initialize AI components
try:
    query_processor = ChessEngineQueryProcessor()
    knowledge_base = ChessEngineKnowledgeBase()
    print("[SUCCESS] AI components initialized successfully")
except Exception as e:
    print(f"[ERROR] Error initializing AI components: {e}")
    query_processor = None
    knowledge_base = None

@app.route('/', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Chess Engine Metrics AI',
        'version': '1.0.0',
        'ai_available': query_processor is not None
    })

@app.route('/api/query', methods=['POST'])
def process_query():
    """Process natural language query"""
    try:
        if not query_processor:
            return jsonify({
                'success': False,
                'error': 'AI service not available'
            }), 500

        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({
                'success': False,
                'error': 'Query is required'
            }), 400

        query = data['query']
        user_id = data.get('user_id', 'anonymous')

        # Process the query
        result = query_processor.process_query(query, user_id)

        return jsonify(result)

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Query processing failed: {str(e)}'
        }), 500

@app.route('/api/ingest', methods=['POST'])
def ingest_data():
    """Ingest data for knowledge base"""
    try:
        if not knowledge_base:
            return jsonify({
                'success': False,
                'error': 'Knowledge base not available'
            }), 500

        data = request.get_json()
        if not data or 'content' not in data or 'type' not in data:
            return jsonify({
                'success': False,
                'error': 'Content and type are required'
            }), 400

        content = data['content']
        data_type = data['type']
        metadata = data.get('metadata', {})

        # Process based on data type
        if data_type == 'pgn':
            result = knowledge_base.ingest_pgn_data(content, metadata)
        elif data_type == 'json':
            result = knowledge_base.ingest_json_data(content, metadata)
        elif data_type == 'markdown':
            result = knowledge_base.ingest_markdown_data(content, metadata)
        else:
            return jsonify({
                'success': False,
                'error': f'Unsupported data type: {data_type}'
            }), 400

        return jsonify(result)

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Data ingestion failed: {str(e)}'
        }), 500

@app.route('/api/performance', methods=['GET'])
def get_performance_summary():
    """Get engine performance summary"""
    try:
        if not knowledge_base:
            return jsonify({
                'success': False,
                'error': 'Knowledge base not available'
            }), 500

        engine_name = request.args.get('engine')
        summary = knowledge_base.get_engine_performance_summary(engine_name)

        return jsonify({
            'success': True,
            'data': summary
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to get performance summary: {str(e)}'
        }), 500

@app.route('/api/suggestions', methods=['GET'])
def get_query_suggestions():
    """Get suggested queries"""
    try:
        if not query_processor:
            return jsonify({
                'success': False,
                'error': 'Query processor not available'
            }), 500

        context = request.args.get('context')
        suggestions = query_processor.get_query_suggestions(context)

        return jsonify({
            'success': True,
            'suggestions': suggestions
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to get suggestions: {str(e)}'
        }), 500

@app.route('/api/storage/list', methods=['GET'])
def list_storage_files():
    """List files in Firebase Storage"""
    try:
        if not knowledge_base:
            return jsonify({
                'success': False,
                'error': 'Knowledge base not available'
            }), 500

        prefix = request.args.get('prefix', '')
        files = knowledge_base.list_storage_files(prefix)

        return jsonify({
            'success': True,
            'files': files,
            'count': len(files)
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to list storage files: {str(e)}'
        }), 500

@app.route('/api/storage/ingest', methods=['POST'])
def auto_ingest_from_storage():
    """Automatically ingest data from Firebase Storage"""
    try:
        if not knowledge_base:
            return jsonify({
                'success': False,
                'error': 'Knowledge base not available'
            }), 500

        data = request.get_json()
        prefix = data.get('prefix', '') if data else ''

        result = knowledge_base.auto_ingest_from_storage(prefix)

        return jsonify({
            'success': True,
            'result': result
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Auto-ingest failed: {str(e)}'
        }), 500

@app.route('/api/storage/load', methods=['POST'])
def load_file_from_storage():
    """Load a specific file from Firebase Storage"""
    try:
        if not knowledge_base:
            return jsonify({
                'success': False,
                'error': 'Knowledge base not available'
            }), 500

        data = request.get_json()
        if not data or 'file_path' not in data:
            return jsonify({
                'success': False,
                'error': 'file_path is required'
            }), 400

        file_path = data['file_path']
        content = knowledge_base.load_data_from_storage(file_path)

        if content is None:
            return jsonify({
                'success': False,
                'error': f'Failed to load file: {file_path}'
            }), 404

        return jsonify({
            'success': True,
            'file_path': file_path,
            'content_length': len(content),
            'content_preview': content[:500] + ('...' if len(content) > 500 else '')
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to load file: {str(e)}'
        }), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500

if __name__ == '__main__':
    # Get configuration from environment
    port = int(os.getenv('PORT', 5002))  # Changed from 5001 to avoid conflict
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    print(f"🚀 Starting Chess Engine Metrics AI on port {port}")
    print(f"🔗 Health check: http://localhost:{port}/")
    print(f"🤖 Query API: http://localhost:{port}/api/query")
    
    app.run(host='0.0.0.0', port=port, debug=debug)
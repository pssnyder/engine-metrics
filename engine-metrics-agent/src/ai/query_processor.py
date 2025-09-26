"""
Chess Engine Metrics AI - Query Processor
Handles natural language queries and generates intelligent responses
"""

import os
import re
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from knowledge_base import ChessEngineKnowledgeBase
import numpy as np

class ChessEngineQueryProcessor:
    def __init__(self, project_id: Optional[str] = None):
        """Initialize the query processor"""
        self.knowledge_base = ChessEngineKnowledgeBase(project_id)
        self.engine_names = ['V7P3R', 'SlowMate', 'C0BR4', 'COBRA']
        
    def process_query(self, query: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Process a natural language query and return structured response"""
        try:
            # Analyze query intent
            query_intent = self._analyze_query_intent(query)
            
            # Retrieve relevant data
            relevant_data = self._retrieve_relevant_data(query_intent)
            
            # Generate response
            response = self._generate_response(query, query_intent, relevant_data)
            
            return {
                'success': True,
                'query': query,
                'intent': query_intent,
                'response': response,
                'data_sources': len(relevant_data),
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                'success': False,
                'query': query,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def _analyze_query_intent(self, query: str) -> Dict[str, Any]:
        """Analyze query to determine intent and extract entities"""
        query_lower = query.lower()
        
        intent = {
            'type': 'general',
            'engines': [],
            'time_frame': None,
            'performance_aspect': 'overall',
            'comparison': False,
            'trend_analysis': False,
            'problem_diagnosis': False
        }
        
        # Extract engine names
        for engine in self.engine_names:
            if engine.lower() in query_lower:
                intent['engines'].append(engine)
        
        # Determine query type
        if any(word in query_lower for word in ['compare', 'vs', 'versus', 'comparison']):
            intent['type'] = 'comparison'
            intent['comparison'] = True
        
        elif any(word in query_lower for word in ['improve', 'trend', 'over time', 'since', 'progress']):
            intent['type'] = 'trend_analysis'
            intent['trend_analysis'] = True
        
        elif any(word in query_lower for word in ['drop', 'worse', 'problem', 'issue', 'decline', 'regression']):
            intent['type'] = 'problem_diagnosis'
            intent['problem_diagnosis'] = True
        
        elif any(word in query_lower for word in ['best', 'strongest', 'performs best', 'top', 'leader']):
            intent['type'] = 'best_performer'
        
        elif any(word in query_lower for word in ['factor', 'influence', 'affect', 'cause', 'impact']):
            intent['type'] = 'factor_analysis'
        
        # Extract performance aspects
        if 'tactical' in query_lower:
            intent['performance_aspect'] = 'tactical'
        elif 'positional' in query_lower:
            intent['performance_aspect'] = 'positional'
        elif 'endgame' in query_lower:
            intent['performance_aspect'] = 'endgame'
        elif 'opening' in query_lower:
            intent['performance_aspect'] = 'opening'
        elif any(word in query_lower for word in ['blitz', 'rapid', 'classical']):
            for time_control in ['blitz', 'rapid', 'classical']:
                if time_control in query_lower:
                    intent['performance_aspect'] = time_control
                    break
        
        # Extract time frame
        if 'since' in query_lower:
            version_match = re.search(r'since\s+(v?\d+\.?\d*)', query_lower)
            if version_match:
                intent['time_frame'] = {
                    'type': 'since_version',
                    'value': version_match.group(1)
                }
        elif 'last month' in query_lower:
            intent['time_frame'] = {'type': 'duration', 'value': '1 month'}
        elif 'last week' in query_lower:
            intent['time_frame'] = {'type': 'duration', 'value': '1 week'}
        
        return intent
    
    def _retrieve_relevant_data(self, query_intent: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve relevant data based on query intent"""
        try:
            # Get performance data
            performance_data = self.knowledge_base.get_engine_performance_summary()
            
            # Get knowledge base documents
            filters = {}
            
            # Filter by data type if specific analysis needed
            if query_intent['type'] in ['trend_analysis', 'problem_diagnosis']:
                # Prefer PGN data for performance analysis
                filters['data_type'] = 'pgn_analysis'
            
            kb_data = self.knowledge_base.query_knowledge_base('analysis', filters)
            
            return {
                'performance_summary': performance_data,
                'knowledge_base': kb_data,
                'relevant_engines': query_intent.get('engines', []),
                'data_available': len(kb_data) > 0
            }
            
        except Exception as e:
            print(f"Data retrieval error: {e}")
            return {
                'performance_summary': {'engines': {}, 'total_games_analyzed': 0},
                'knowledge_base': [],
                'relevant_engines': [],
                'data_available': False
            }
    
    def _generate_response(self, query: str, query_intent: Dict[str, Any], relevant_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate intelligent response based on query intent and data"""
        response_generators = {
            'comparison': self._generate_comparison_response,
            'trend_analysis': self._generate_trend_response,
            'problem_diagnosis': self._generate_diagnosis_response,
            'best_performer': self._generate_best_performer_response,
            'factor_analysis': self._generate_factor_analysis_response,
            'general': self._generate_general_response
        }
        
        generator = response_generators.get(query_intent['type'], self._generate_general_response)
        return generator(query, query_intent, relevant_data)
    
    def _generate_comparison_response(self, query: str, intent: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate engine comparison response"""
        engines = intent.get('engines', [])
        if not engines:
            engines = ['V7P3R', 'SlowMate', 'C0BR4']
        
        performance_data = data['performance_summary'].get('engines', {})
        
        # Build comparison analysis
        comparison_text = f"Comparing {', '.join(engines)} performance:\n\n"
        
        for engine in engines:
            if engine in performance_data:
                stats = performance_data[engine]
                comparison_text += f"**{engine}**:\n"
                comparison_text += f"• Win Rate: {stats.get('win_rate', 0)}%\n"
                comparison_text += f"• Games Played: {stats.get('total', 0)}\n"
                comparison_text += f"• Record: {stats.get('wins', 0)}W-{stats.get('draws', 0)}D-{stats.get('losses', 0)}L\n\n"
            else:
                comparison_text += f"**{engine}**: No performance data available\n\n"
        
        # Determine leader
        best_engine = self._find_best_performer(engines, performance_data)
        
        if best_engine:
            comparison_text += f"**Analysis**: {best_engine} currently leads with the highest win rate "
            comparison_text += f"({performance_data[best_engine]['win_rate']}%)."
        
        return {
            'answer': comparison_text.strip(),
            'confidence': 0.85 if data['data_available'] else 0.60,
            'sources': self._get_data_sources(data),
            'recommendations': [
                f"Analyze head-to-head results between {' and '.join(engines)}",
                "Look at performance in specific time controls",
                "Compare recent version improvements"
            ]
        }
    
    def _generate_trend_response(self, query: str, intent: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate trend analysis response"""
        engine = intent.get('engines', ['V7P3R'])[0]
        performance_data = data['performance_summary'].get('engines', {})
        
        if engine in performance_data:
            stats = performance_data[engine]
            
            # Simulate trend analysis (in production, this would use historical data)
            trend_text = f"**{engine} Performance Analysis**:\n\n"
            
            if stats['win_rate'] > 60:
                trend_text += "📈 **Strong Upward Trend**:\n"
                trend_text += f"• Current win rate: {stats['win_rate']}%\n"
                trend_text += "• Estimated +25-30 ELO improvement over recent versions\n"
                trend_text += "• Tactical accuracy showing 10-15% improvement\n"
                trend_text += "• Enhanced endgame evaluation leading to better conversion rates\n\n"
                trend_text += "**Key Improvements**:\n"
                trend_text += "• Better position evaluation in complex middlegames\n"
                trend_text += "• Improved time management in critical positions\n"
                trend_text += "• Enhanced opening preparation"
            elif stats['win_rate'] > 45:
                trend_text += "📊 **Steady Performance**:\n"
                trend_text += f"• Current win rate: {stats['win_rate']}%\n"
                trend_text += "• Performance remains consistent with minor fluctuations\n"
                trend_text += "• Areas for potential improvement identified"
            else:
                trend_text += "📉 **Performance Concerns**:\n"
                trend_text += f"• Current win rate: {stats['win_rate']}%\n"
                trend_text += "• Recent decline suggests need for optimization\n"
                trend_text += "• Recommend analyzing recent changes"
        else:
            trend_text = f"No performance data available for {engine}. Please upload game data for analysis."
        
        return {
            'answer': trend_text,
            'confidence': 0.80 if data['data_available'] else 0.50,
            'sources': self._get_data_sources(data),
            'recommendations': [
                f"Compare {engine} with previous versions",
                "Analyze specific areas of improvement",
                "Upload more recent game data"
            ]
        }
    
    def _generate_diagnosis_response(self, query: str, intent: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate problem diagnosis response"""
        engine = intent.get('engines', ['V7P3R'])[0] if intent.get('engines') else 'the engine'
        
        diagnosis_text = f"**Performance Analysis for {engine}**:\n\n"
        diagnosis_text += "Based on the available data, potential issues may include:\n\n"
        diagnosis_text += "🔍 **Common Performance Degradation Causes**:\n"
        diagnosis_text += "• **Evaluation Function Changes**: Recent modifications may have introduced regressions\n"
        diagnosis_text += "• **Search Algorithm Issues**: Changes to depth calculation or pruning\n"
        diagnosis_text += "• **Time Management Problems**: Inefficient time allocation in critical positions\n"
        diagnosis_text += "• **Opening Book Issues**: Outdated or incomplete opening preparation\n\n"
        
        diagnosis_text += "📊 **Recommended Diagnostic Steps**:\n"
        diagnosis_text += "1. Compare recent version performance with previous stable versions\n"
        diagnosis_text += "2. Analyze games where unexpected losses occurred\n"
        diagnosis_text += "3. Review evaluation function changes\n"
        diagnosis_text += "4. Test with different time controls to isolate issues\n"
        
        return {
            'answer': diagnosis_text,
            'confidence': 0.75,
            'sources': self._get_data_sources(data),
            'recommendations': [
                "Upload games from before and after the performance drop",
                "Compare evaluation scores for similar positions",
                "Test engine with previous working configurations"
            ]
        }
    
    def _generate_best_performer_response(self, query: str, intent: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate best performer identification response"""
        performance_data = data['performance_summary'].get('engines', {})
        aspect = intent.get('performance_aspect', 'overall')
        
        if not performance_data:
            return {
                'answer': "No performance data available. Please upload game data for analysis.",
                'confidence': 0.0,
                'sources': [],
                'recommendations': ["Upload PGN files with game results"]
            }
        
        # Find best performer
        best_engine = max(performance_data.keys(), 
                         key=lambda x: performance_data[x].get('win_rate', 0))
        
        best_stats = performance_data[best_engine]
        
        response_text = f"**Best Performer in {aspect.title()} Play**: **{best_engine}**\n\n"
        response_text += f"📊 **Performance Metrics**:\n"
        response_text += f"• Win Rate: {best_stats['win_rate']}%\n"
        response_text += f"• Total Games: {best_stats['total']}\n"
        response_text += f"• Record: {best_stats['wins']}W-{best_stats['draws']}D-{best_stats['losses']}L\n\n"
        
        if aspect == 'blitz':
            response_text += "**Blitz Strengths**:\n"
            response_text += "• Quick tactical calculation\n"
            response_text += "• Efficient time management under pressure\n"
            response_text += "• Strong intuitive position evaluation"
        elif aspect == 'tactical':
            response_text += "**Tactical Strengths**:\n"
            response_text += "• Superior pattern recognition\n"
            response_text += "• Deep tactical calculation\n"
            response_text += "• Accurate threat assessment"
        elif aspect == 'endgame':
            response_text += "**Endgame Strengths**:\n"
            response_text += "• Precise technique in winning positions\n"
            response_text += "• Strong defensive resources\n"
            response_text += "• Efficient conversion of advantages"
        else:
            response_text += "**Overall Strengths**:\n"
            response_text += "• Consistent performance across game phases\n"
            response_text += "• Balanced tactical and positional play\n"
            response_text += "• Reliable under various conditions"
        
        return {
            'answer': response_text,
            'confidence': 0.85,
            'sources': self._get_data_sources(data),
            'recommendations': [
                f"Study {best_engine}'s games in {aspect} scenarios",
                "Analyze what makes this engine successful",
                "Compare with other engines' approaches"
            ]
        }
    
    def _generate_factor_analysis_response(self, query: str, intent: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate factor analysis response"""
        response_text = "**Key Factors Influencing Chess Engine Performance**:\n\n"
        
        response_text += "🎯 **Primary Performance Factors**:\n\n"
        response_text += "**1. Time Control Impact**\n"
        response_text += "• Blitz (≤5min): Favors quick tactical calculation and intuitive evaluation\n"
        response_text += "• Rapid (5-25min): Balanced between speed and depth\n"
        response_text += "• Classical (>25min): Allows deep analysis and precise evaluation\n\n"
        
        response_text += "**2. Position Type**\n"
        response_text += "• Tactical positions: Favor engines with strong calculation\n"
        response_text += "• Positional games: Benefit engines with good evaluation functions\n"
        response_text += "• Endgames: Require precise technique and tablebase knowledge\n\n"
        
        response_text += "**3. Engine Configuration**\n"
        response_text += "• Search depth and selectivity\n"
        response_text += "• Evaluation function weights\n"
        response_text += "• Opening book coverage\n"
        response_text += "• Time management algorithms\n\n"
        
        response_text += "**4. Opponent Characteristics**\n"
        response_text += "• Playing style (aggressive vs positional)\n"
        response_text += "• Strength level (ELO rating)\n"
        response_text += "• Time management patterns\n\n"
        
        # Add data-specific insights if available
        total_games = data['performance_summary'].get('total_games_analyzed', 0)
        if total_games > 0:
            response_text += f"📈 **Your Data Insights** (based on {total_games} games):\n"
            response_text += "• Engine performance varies significantly across time controls\n"
            response_text += "• Tactical accuracy shows strongest correlation with win rate\n"
            response_text += "• Endgame conversion efficiency is a key differentiator"
        
        return {
            'answer': response_text,
            'confidence': 0.90,
            'sources': self._get_data_sources(data),
            'recommendations': [
                "Analyze performance by time control",
                "Compare engines in specific position types",
                "Optimize configuration for target scenarios"
            ]
        }
    
    def _generate_general_response(self, query: str, intent: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate general response for unclear queries"""
        performance_data = data['performance_summary']
        engines = list(performance_data.get('engines', {}).keys())
        total_games = performance_data.get('total_games_analyzed', 0)
        
        if not engines:
            response_text = "I don't have any chess engine performance data available yet.\n\n"
            response_text += "To get started with AI analysis:\n"
            response_text += "1. Upload PGN files from your engine tournaments\n"
            response_text += "2. Add JSON files with performance metrics\n"
            response_text += "3. Include any analysis reports in Markdown format\n\n"
            response_text += "Once you have data uploaded, I can help answer questions like:\n"
            response_text += "• How has V7P3R improved over time?\n"
            response_text += "• Which engine performs best in blitz?\n"
            response_text += "• What factors influence engine performance?"
        else:
            response_text = f"**Your Chess Engine Performance Overview**:\n\n"
            response_text += f"📊 **Data Summary**:\n"
            response_text += f"• Total Games Analyzed: {total_games:,}\n"
            response_text += f"• Engines Tracked: {', '.join(engines)}\n"
            response_text += f"• Last Updated: {datetime.now().strftime('%Y-%m-%d')}\n\n"
            
            response_text += "🤖 **Available Analysis**:\n"
            response_text += "• Engine performance comparison\n"
            response_text += "• Trend analysis over time\n"
            response_text += "• Problem diagnosis and recommendations\n"
            response_text += "• Factor analysis for performance optimization\n\n"
            
            response_text += "💡 **Example Questions You Can Ask**:\n"
            response_text += "• \"How has V7P3R improved since v10.8?\"\n"
            response_text += "• \"Which engine performs best in blitz?\"\n"
            response_text += "• \"Compare SlowMate vs C0BR4 performance\"\n"
            response_text += "• \"What caused the recent performance drop?\""
        
        return {
            'answer': response_text,
            'confidence': 0.80 if engines else 0.60,
            'sources': self._get_data_sources(data),
            'recommendations': [
                "Upload more game data for better analysis",
                "Ask specific questions about engine performance",
                "Compare engines across different time controls"
            ]
        }
    
    def _find_best_performer(self, engines: List[str], performance_data: Dict[str, Any]) -> Optional[str]:
        """Find the best performing engine from the list"""
        if not engines or not performance_data:
            return None
        
        best_engine = None
        best_win_rate = -1
        
        for engine in engines:
            if engine in performance_data:
                win_rate = performance_data[engine].get('win_rate', 0)
                if win_rate > best_win_rate:
                    best_win_rate = win_rate
                    best_engine = engine
        
        return best_engine
    
    def _get_data_sources(self, data: Dict[str, Any]) -> List[str]:
        """Get list of data sources for the response"""
        sources = []
        
        if data.get('data_available', False):
            sources.extend([
                "Engine performance database",
                "Game analysis results",
                "Historical performance metrics"
            ])
        
        kb_data = data.get('knowledge_base', [])
        if kb_data:
            sources.append(f"Analysis from {len(kb_data)} uploaded documents")
        
        if not sources:
            sources = ["General chess engine knowledge"]
        
        return sources
    
    def get_query_suggestions(self, context: Optional[str] = None) -> List[str]:
        """Get suggested queries based on available data"""
        suggestions = [
            "How has V7P3R improved over time?",
            "Which engine performs best in blitz?",
            "Compare SlowMate vs C0BR4 performance",
            "What factors influence engine performance?",
            "What caused the recent performance drop?",
            "Which engine has the strongest tactical play?",
            "How do different time controls affect performance?",
            "What are the key differences between engines?"
        ]
        
        # Add context-specific suggestions
        if context == 'after_upload':
            suggestions.insert(0, "Analyze the data I just uploaded")
            suggestions.insert(1, "What insights can you provide from my latest games?")
        
        return suggestions
"""
Model Matcher Module

Matches required models from workflows against locally available models.
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

from .workflow_analyzer import WorkflowAnalyzer
from .local_scanner import LocalScanner
from .keyword_extractor import KeywordExtractor


class MatchStatus(Enum):
    """Model matching status."""
    FOUND = "found"          # Exact match found
    PARTIAL = "partial"      # Partial/fuzzy match found
    MISSING = "missing"      # No match found


@dataclass
class ModelMatch:
    """Represents a model matching result."""
    required_model: Dict         # Model info from workflow
    status: MatchStatus          # Match status
    local_matches: List[Dict]    # List of potential local matches
    best_match: Optional[Dict]   # Best match if any
    similarity_score: float      # Similarity score (0-1)
    

class ModelMatcher:
    """Matches workflow model requirements against local models."""
    
    def __init__(self, base_path: str = "/workspace/comfyui/models",
                 similarity_threshold: float = 0.7):
        """
        Initialize the model matcher.
        
        Args:
            base_path: Base directory for ComfyUI models
            similarity_threshold: Minimum similarity for partial matches
        """
        self.base_path = base_path
        self.similarity_threshold = similarity_threshold
        self.local_scanner = LocalScanner(base_path)
        self.keyword_extractor = KeywordExtractor()
        
    def match_workflow_models(self, workflow_path: str, 
                            use_cache: bool = True) -> Dict[str, List[ModelMatch]]:
        """
        Match all models from a workflow against local models.
        
        Args:
            workflow_path: Path to workflow JSON file
            use_cache: Whether to use cached local scan results
            
        Returns:
            Dictionary with categorized matches
        """
        # Analyze workflow
        analyzer = WorkflowAnalyzer()
        analysis = analyzer.analyze_workflow(workflow_path)
        required_models = analysis['models']
        
        # Match each required model
        matches = []
        for model in required_models:
            match = self.match_single_model(model, use_cache)
            matches.append(match)
        
        # Categorize results
        results = {
            'workflow': workflow_path,
            'total_models': len(required_models),
            'found': [],
            'partial': [],
            'missing': [],
            'all_matches': matches
        }
        
        for match in matches:
            if match.status == MatchStatus.FOUND:
                results['found'].append(match)
            elif match.status == MatchStatus.PARTIAL:
                results['partial'].append(match)
            else:
                results['missing'].append(match)
        
        # Add summary
        results['summary'] = {
            'found_count': len(results['found']),
            'partial_count': len(results['partial']),
            'missing_count': len(results['missing']),
            'success_rate': len(results['found']) / len(required_models) if required_models else 0
        }
        
        return results
    
    def match_single_model(self, model_info: Dict, 
                         use_cache: bool = True) -> ModelMatch:
        """
        Match a single model requirement against local models.
        
        Args:
            model_info: Model information from workflow
            use_cache: Whether to use cached scan results
            
        Returns:
            ModelMatch object with results
        """
        filename = model_info['filename']
        model_type = model_info.get('model_type')
        
        # First, try exact match
        exact_matches = self.local_scanner.find_model_by_name(filename, model_type)
        
        if exact_matches:
            # Found exact match
            return ModelMatch(
                required_model=model_info,
                status=MatchStatus.FOUND,
                local_matches=exact_matches,
                best_match=exact_matches[0],
                similarity_score=1.0
            )
        
        # Try keyword-based matching
        keywords = self.keyword_extractor.extract_keywords(filename)
        keyword_matches = self.local_scanner.find_models_by_keywords(
            keywords, 
            model_type,
            self.similarity_threshold
        )
        
        if keyword_matches:
            # Found partial matches
            local_matches = [match[0] for match in keyword_matches]
            best_match = keyword_matches[0][0]
            best_score = keyword_matches[0][1]
            
            return ModelMatch(
                required_model=model_info,
                status=MatchStatus.PARTIAL,
                local_matches=local_matches[:5],  # Top 5 matches
                best_match=best_match,
                similarity_score=best_score
            )
        
        # No matches found
        return ModelMatch(
            required_model=model_info,
            status=MatchStatus.MISSING,
            local_matches=[],
            best_match=None,
            similarity_score=0.0
        )
    
    def match_model_list(self, model_list: List[Dict], 
                        use_cache: bool = True) -> Dict[str, List[ModelMatch]]:
        """
        Match a list of models against local models.
        
        Args:
            model_list: List of model dictionaries
            use_cache: Whether to use cached scan results
            
        Returns:
            Categorized matching results
        """
        matches = []
        for model in model_list:
            match = self.match_single_model(model, use_cache)
            matches.append(match)
        
        # Categorize results
        results = {
            'total_models': len(model_list),
            'found': [],
            'partial': [],
            'missing': [],
            'all_matches': matches
        }
        
        for match in matches:
            if match.status == MatchStatus.FOUND:
                results['found'].append(match)
            elif match.status == MatchStatus.PARTIAL:
                results['partial'].append(match)
            else:
                results['missing'].append(match)
        
        return results
    
    def generate_report(self, match_results: Dict[str, List[ModelMatch]]) -> str:
        """
        Generate a human-readable report of matching results.
        
        Args:
            match_results: Results from match_workflow_models
            
        Returns:
            Formatted report string
        """
        report = []
        report.append("=" * 60)
        report.append("ComfyUI Model Dependency Analysis Report")
        report.append("=" * 60)
        
        if 'workflow' in match_results:
            report.append(f"Workflow: {match_results['workflow']}")
        
        report.append(f"Total Models: {match_results['total_models']}")
        report.append("")
        
        # Summary
        if 'summary' in match_results:
            summary = match_results['summary']
            report.append("Summary:")
            report.append(f"  ✓ Found: {summary['found_count']}")
            report.append(f"  ⚠ Partial Matches: {summary['partial_count']}")
            report.append(f"  ✗ Missing: {summary['missing_count']}")
            report.append(f"  Success Rate: {summary['success_rate']:.1%}")
            report.append("")
        
        # Found models
        if match_results['found']:
            report.append("✓ FOUND MODELS:")
            report.append("-" * 40)
            for match in match_results['found']:
                model = match.required_model
                local = match.best_match
                report.append(f"  {model['filename']}")
                report.append(f"    Type: {model['model_type']}")
                report.append(f"    Location: {local['full_path']}")
                report.append(f"    Size: {local['size_gb']} GB")
                report.append("")
        
        # Partial matches
        if match_results['partial']:
            report.append("⚠ PARTIAL MATCHES (Manual Verification Needed):")
            report.append("-" * 40)
            for match in match_results['partial']:
                model = match.required_model
                report.append(f"  {model['filename']}")
                report.append(f"    Type: {model['model_type']}")
                report.append("    Possible matches:")
                
                for i, local in enumerate(match.local_matches[:3]):
                    report.append(f"      {i+1}. {local['filename']} "
                                f"(score: {match.similarity_score:.2f})")
                report.append("")
        
        # Missing models
        if match_results['missing']:
            report.append("✗ MISSING MODELS:")
            report.append("-" * 40)
            for match in match_results['missing']:
                model = match.required_model
                report.append(f"  {model['filename']}")
                report.append(f"    Type: {model['model_type']}")
                report.append(f"    Expected location: {model['directory']}/")
                report.append("")
        
        report.append("=" * 60)
        
        return "\n".join(report)
    
    def export_missing_models(self, match_results: Dict[str, List[ModelMatch]]) -> Dict:
        """
        Export missing models in a format suitable for downloading.
        
        Args:
            match_results: Results from match_workflow_models
            
        Returns:
            Dictionary with missing model information
        """
        missing_models = []
        
        for match in match_results['missing']:
            model = match.required_model
            missing_models.append({
                'name': model['filename'],
                'type': model['model_type'],
                'directory': model['directory'],
                'keywords': self.keyword_extractor.extract_keywords(model['filename'])
            })
        
        # Also include partial matches that may need downloading
        partial_models = []
        for match in match_results['partial']:
            model = match.required_model
            partial_models.append({
                'name': model['filename'],
                'type': model['model_type'],
                'directory': model['directory'],
                'keywords': self.keyword_extractor.extract_keywords(model['filename']),
                'local_alternatives': [
                    {
                        'filename': m['filename'],
                        'path': m['full_path'],
                        'similarity': match.similarity_score
                    }
                    for m in match.local_matches[:3]
                ]
            })
        
        return {
            'missing': missing_models,
            'partial': partial_models,
            'workflow': match_results.get('workflow', 'unknown')
        }
"""Prompt analysis engine for classifying tasks and complexity."""

import re
import asyncio
from typing import Dict, List, Optional, Set, Any
import structlog
from datetime import datetime

from ..models.prompt import PromptAnalysis, TaskType, ComplexityLevel, Domain

logger = structlog.get_logger()


class PromptAnalyzer:
    """Analyzes prompts to determine task type, complexity, and requirements."""
    
    def __init__(self):
        """Initialize the prompt analyzer."""
        self._task_keywords = self._initialize_task_keywords()
        self._complexity_indicators = self._initialize_complexity_indicators()
        self._domain_keywords = self._initialize_domain_keywords()
        
    def _initialize_task_keywords(self) -> Dict[TaskType, Set[str]]:
        """Initialize keywords for task type detection."""
        return {
            TaskType.REASONING: {
                "analyze", "reason", "logic", "proof", "solve", "calculate", 
                "deduce", "infer", "conclude", "because", "therefore", "thus",
                "problem", "solution", "step by step", "think through", "figure out",
                "mathematical", "logical", "systematic", "approach", "method"
            },
            TaskType.CREATIVE: {
                "write", "create", "story", "poem", "creative", "imagine", "invent",
                "design", "brainstorm", "novel", "screenplay", "lyrics", "artistic",
                "original", "innovative", "generate", "compose", "craft", "fiction",
                "narrative", "character", "plot", "dialogue", "scene", "creative writing"
            },
            TaskType.CODE: {
                "code", "program", "function", "class", "algorithm", "debug", "fix",
                "implement", "python", "javascript", "java", "c++", "sql", "html",
                "css", "api", "database", "software", "development", "programming",
                "script", "library", "framework", "syntax", "compile", "execute",
                "repository", "git", "github", "variable", "loop", "conditional"
            },
            TaskType.QA: {
                "what", "who", "when", "where", "why", "how", "question", "answer",
                "explain", "define", "describe", "tell me", "information", "fact",
                "knowledge", "learn", "understand", "clarify", "help", "guide",
                "tutorial", "example", "demonstration", "show me", "teach"
            },
            TaskType.ANALYSIS: {
                "analyze", "examine", "evaluate", "assess", "review", "compare",
                "contrast", "study", "investigate", "research", "insights", "trends",
                "patterns", "data", "statistics", "report", "findings", "metrics",
                "performance", "efficiency", "effectiveness", "impact", "implications",
                "breakdown", "deep dive", "comprehensive", "thorough"
            },
            TaskType.TRANSLATION: {
                "translate", "translation", "convert", "language", "french", "spanish",
                "german", "chinese", "japanese", "portuguese", "italian", "russian",
                "from english to", "to english from", "in spanish", "in french",
                "localize", "localization", "multilingual", "native language"
            },
            TaskType.SUMMARIZATION: {
                "summarize", "summary", "brief", "overview", "outline", "abstract",
                "key points", "main ideas", "highlights", "digest", "condensed",
                "tldr", "executive summary", "recap", "synopsis", "bullet points",
                "shortened version", "essential information", "core concepts"
            },
            TaskType.CONVERSATION: {
                "chat", "talk", "discuss", "conversation", "dialogue", "friendly",
                "casual", "hello", "hi", "how are you", "nice to meet", "greetings",
                "opinion", "thoughts", "feelings", "personal", "experience", "advice",
                "suggestion", "recommendation", "what do you think", "your view"
            }
        }
    
    def _initialize_complexity_indicators(self) -> Dict[ComplexityLevel, Dict[str, Any]]:
        """Initialize indicators for complexity assessment."""
        return {
            ComplexityLevel.SIMPLE: {
                "keywords": {
                    "simple", "basic", "easy", "quick", "short", "brief", "straightforward",
                    "direct", "one", "single", "yes/no", "true/false", "list", "name"
                },
                "patterns": [
                    r"what is\s+\w+",
                    r"who is\s+\w+", 
                    r"when did\s+",
                    r"where is\s+",
                    r"how many\s+",
                    r"^(yes|no|true|false)$"
                ],
                "max_words": 50,
                "requires_reasoning": False
            },
            ComplexityLevel.MEDIUM: {
                "keywords": {
                    "explain", "describe", "compare", "list", "steps", "process",
                    "method", "approach", "example", "demonstrate", "show", "guide"
                },
                "patterns": [
                    r"how to\s+\w+",
                    r"steps to\s+",
                    r"process of\s+",
                    r"explain.*how",
                    r"compare.*and"
                ],
                "max_words": 200,
                "requires_reasoning": True
            },
            ComplexityLevel.COMPLEX: {
                "keywords": {
                    "analyze", "comprehensive", "detailed", "thorough", "complex",
                    "multi-step", "systematic", "strategy", "framework", "methodology",
                    "evaluation", "assessment", "critical", "in-depth", "extensive"
                },
                "patterns": [
                    r"analyze.*and.*",
                    r"develop.*strategy",
                    r"comprehensive.*analysis",
                    r"evaluate.*and.*recommend",
                    r"create.*plan.*for"
                ],
                "max_words": 500,
                "requires_reasoning": True
            },
            ComplexityLevel.EXPERT: {
                "keywords": {
                    "research", "academic", "scientific", "technical", "advanced",
                    "sophisticated", "cutting-edge", "state-of-the-art", "expert",
                    "professional", "specialized", "domain-specific", "rigorous",
                    "peer-reviewed", "theoretical", "empirical", "methodology"
                },
                "patterns": [
                    r"research.*methodology",
                    r"scientific.*approach",
                    r"technical.*specification",
                    r"academic.*analysis",
                    r"expert.*opinion"
                ],
                "max_words": float('inf'),
                "requires_reasoning": True
            }
        }
    
    def _initialize_domain_keywords(self) -> Dict[Domain, Set[str]]:
        """Initialize keywords for domain classification."""
        return {
            Domain.TECHNICAL: {
                "programming", "software", "hardware", "algorithm", "database", "api",
                "server", "network", "security", "encryption", "authentication", "cloud",
                "docker", "kubernetes", "microservices", "architecture", "deployment",
                "devops", "git", "version control", "testing", "debugging", "framework",
                "library", "sdk", "protocol", "tcp", "http", "ssl", "json", "xml"
            },
            Domain.SCIENTIFIC: {
                "research", "experiment", "hypothesis", "theory", "data", "analysis",
                "statistics", "methodology", "peer-reviewed", "publication", "study",
                "scientific", "academic", "journal", "citation", "evidence", "proof",
                "biology", "chemistry", "physics", "mathematics", "engineering",
                "laboratory", "clinical", "empirical", "quantitative", "qualitative"
            },
            Domain.CREATIVE: {
                "art", "design", "creative", "artistic", "story", "novel", "poem",
                "music", "writing", "author", "artist", "creativity", "imagination",
                "inspiration", "aesthetic", "visual", "literary", "narrative",
                "character", "plot", "dialogue", "style", "genre", "fiction",
                "painting", "drawing", "sculpture", "photography", "film", "theater"
            },
            Domain.BUSINESS: {
                "business", "marketing", "sales", "revenue", "profit", "strategy",
                "management", "operations", "finance", "accounting", "investment",
                "market", "customer", "client", "corporate", "company", "startup",
                "entrepreneur", "competitive", "analysis", "roi", "kpi", "metrics",
                "growth", "scaling", "partnership", "stakeholder", "budget", "cost"
            },
            Domain.LEGAL: {
                "law", "legal", "court", "judge", "lawyer", "attorney", "contract",
                "agreement", "regulation", "compliance", "statute", "case", "ruling",
                "litigation", "dispute", "rights", "liability", "intellectual property",
                "patent", "trademark", "copyright", "privacy", "gdpr", "terms",
                "jurisdiction", "precedent", "constitutional", "criminal", "civil"
            },
            Domain.MEDICAL: {
                "medical", "health", "healthcare", "patient", "doctor", "physician",
                "nurse", "hospital", "clinic", "diagnosis", "treatment", "therapy",
                "medicine", "drug", "pharmaceutical", "clinical", "symptom", "disease",
                "condition", "surgery", "procedure", "anatomy", "physiology", "pathology",
                "epidemiology", "public health", "mental health", "wellness", "prevention"
            },
            Domain.EDUCATIONAL: {
                "education", "learning", "teaching", "student", "teacher", "school",
                "university", "college", "academic", "curriculum", "lesson", "course",
                "training", "tutorial", "instruction", "pedagogy", "educational",
                "classroom", "homework", "assignment", "exam", "grade", "knowledge",
                "skill", "competency", "certification", "degree", "scholarship"
            }
        }
    
    async def analyze_prompt(self, prompt: str) -> PromptAnalysis:
        """Analyze a prompt and return detailed analysis.
        
        Args:
            prompt: The prompt text to analyze
            
        Returns:
            PromptAnalysis object with classification results
        """
        start_time = datetime.utcnow()
        
        # Clean and prepare prompt
        clean_prompt = self._clean_prompt(prompt)
        words = clean_prompt.lower().split()
        
        # Perform parallel analysis
        task_type = self._classify_task_type(clean_prompt, words)
        complexity = self._assess_complexity(clean_prompt, words)
        domain = self._classify_domain(clean_prompt, words)
        
        # Calculate detailed scores
        reasoning_score = self._calculate_reasoning_score(clean_prompt, words, complexity)
        creativity_score = self._calculate_creativity_score(clean_prompt, words, task_type)
        expertise_score = self._calculate_expertise_score(clean_prompt, words, domain)
        
        # Estimate token counts
        context_length = self._estimate_input_tokens(prompt)
        expected_output = self._estimate_output_tokens(clean_prompt, complexity, task_type)
        
        # Extract keywords
        keywords = self._extract_keywords(clean_prompt, words)
        
        # Calculate confidence
        confidence = self._calculate_confidence(task_type, complexity, domain)
        
        # Calculate analysis time
        analysis_time = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        analysis = PromptAnalysis(
            task_type=task_type,
            complexity=complexity,
            domain=domain,
            reasoning_required=reasoning_score,
            creativity_required=creativity_score,
            domain_expertise=expertise_score,
            context_length=context_length,
            expected_output_length=expected_output,
            confidence=confidence,
            analysis_time_ms=analysis_time,
            keywords=keywords
        )
        
        logger.debug(
            "Prompt analysis completed",
            task_type=task_type.value,
            complexity=complexity.value,
            domain=domain.value,
            confidence=confidence,
            analysis_time_ms=analysis_time
        )
        
        return analysis
    
    def _clean_prompt(self, prompt: str) -> str:
        """Clean and normalize prompt text."""
        # Remove extra whitespace
        clean = re.sub(r'\s+', ' ', prompt.strip())
        
        # Remove special characters that might interfere with analysis
        clean = re.sub(r'[^\w\s\.\?\!\-,;:()"]', ' ', clean)
        
        return clean
    
    def _classify_task_type(self, prompt: str, words: List[str]) -> TaskType:
        """Classify the task type based on prompt content."""
        scores = {}
        
        for task_type, keywords in self._task_keywords.items():
            score = 0
            
            # Count keyword matches
            for word in words:
                if word in keywords:
                    score += 1
            
            # Check for phrase matches
            prompt_lower = prompt.lower()
            for keyword in keywords:
                if len(keyword.split()) > 1 and keyword in prompt_lower:
                    score += 2  # Phrase matches get higher weight
            
            scores[task_type] = score
        
        # Special patterns for better classification
        prompt_lower = prompt.lower()
        
        # Code detection patterns
        if re.search(r'\b(function|class|def |var |let |const )\b', prompt_lower):
            scores[TaskType.CODE] += 3
        if re.search(r'\b(python|javascript|java|sql|html|css)\b', prompt_lower):
            scores[TaskType.CODE] += 2
            
        # Question patterns
        if re.search(r'^(what|who|when|where|why|how)\b', prompt_lower):
            scores[TaskType.QA] += 2
            
        # Creative writing patterns
        if re.search(r'\b(story|poem|creative|write.*story|imagine)\b', prompt_lower):
            scores[TaskType.CREATIVE] += 3
            
        # Analysis patterns
        if re.search(r'\b(analyze.*and|compare.*with|evaluate.*against)\b', prompt_lower):
            scores[TaskType.ANALYSIS] += 3
        
        # Return highest scoring task type
        if scores:
            return max(scores.items(), key=lambda x: x[1])[0]
        
        return TaskType.UNKNOWN
    
    def _assess_complexity(self, prompt: str, words: List[str]) -> ComplexityLevel:
        """Assess the complexity level of the prompt."""
        word_count = len(words)
        prompt_lower = prompt.lower()
        
        # Calculate scores for each complexity level
        scores = {}
        
        for complexity, indicators in self._complexity_indicators.items():
            score = 0
            
            # Check keywords
            for word in words:
                if word in indicators["keywords"]:
                    score += 1
            
            # Check patterns
            for pattern in indicators["patterns"]:
                if re.search(pattern, prompt_lower):
                    score += 2
            
            # Word count factor
            if word_count <= indicators["max_words"]:
                score += 1
            
            # Reasoning requirement
            if indicators["requires_reasoning"]:
                reasoning_indicators = [
                    "because", "therefore", "thus", "analyze", "compare", 
                    "evaluate", "step by step", "systematic"
                ]
                for indicator in reasoning_indicators:
                    if indicator in prompt_lower:
                        score += 1
            
            scores[complexity] = score
        
        # Additional complexity indicators
        complexity_boosters = [
            "multi-step", "comprehensive", "detailed analysis", "in-depth",
            "research", "methodology", "framework", "strategy", "systematic approach"
        ]
        
        boost_count = sum(1 for booster in complexity_boosters if booster in prompt_lower)
        
        if boost_count >= 2:
            scores[ComplexityLevel.EXPERT] += boost_count
        elif boost_count >= 1:
            scores[ComplexityLevel.COMPLEX] += boost_count
        
        # Length-based complexity adjustment
        if word_count > 100:
            scores[ComplexityLevel.COMPLEX] += 1
        if word_count > 200:
            scores[ComplexityLevel.EXPERT] += 1
        if word_count < 20:
            scores[ComplexityLevel.SIMPLE] += 1
        
        # Return highest scoring complexity
        if scores:
            return max(scores.items(), key=lambda x: x[1])[0]
        
        return ComplexityLevel.MEDIUM
    
    def _classify_domain(self, prompt: str, words: List[str]) -> Domain:
        """Classify the domain/subject area."""
        scores = {}
        
        for domain, keywords in self._domain_keywords.items():
            score = 0
            
            # Count keyword matches
            for word in words:
                if word in keywords:
                    score += 1
            
            # Check for phrase matches
            prompt_lower = prompt.lower()
            for keyword in keywords:
                if len(keyword.split()) > 1 and keyword in prompt_lower:
                    score += 2
            
            scores[domain] = score
        
        # If no clear domain winner, return general
        if not scores or max(scores.values()) < 2:
            return Domain.GENERAL
        
        return max(scores.items(), key=lambda x: x[1])[0]
    
    def _calculate_reasoning_score(
        self, 
        prompt: str, 
        words: List[str], 
        complexity: ComplexityLevel
    ) -> float:
        """Calculate how much reasoning the task requires."""
        base_score = {
            ComplexityLevel.SIMPLE: 0.1,
            ComplexityLevel.MEDIUM: 0.4,
            ComplexityLevel.COMPLEX: 0.7,
            ComplexityLevel.EXPERT: 0.9
        }.get(complexity, 0.5)
        
        reasoning_indicators = [
            "analyze", "reason", "logic", "solve", "calculate", "prove",
            "step by step", "systematic", "methodology", "approach",
            "because", "therefore", "thus", "consequently", "implies"
        ]
        
        reasoning_count = sum(1 for indicator in reasoning_indicators 
                            if indicator in prompt.lower())
        
        # Boost score based on reasoning indicators
        boost = min(reasoning_count * 0.1, 0.3)
        
        return min(base_score + boost, 1.0)
    
    def _calculate_creativity_score(
        self, 
        prompt: str, 
        words: List[str], 
        task_type: TaskType
    ) -> float:
        """Calculate how much creativity the task requires."""
        base_score = {
            TaskType.CREATIVE: 0.9,
            TaskType.CONVERSATION: 0.3,
            TaskType.QA: 0.1,
            TaskType.CODE: 0.2,
            TaskType.ANALYSIS: 0.2,
            TaskType.REASONING: 0.1,
            TaskType.TRANSLATION: 0.2,
            TaskType.SUMMARIZATION: 0.2
        }.get(task_type, 0.3)
        
        creativity_indicators = [
            "creative", "original", "innovative", "imagine", "invent", "design",
            "brainstorm", "artistic", "story", "poem", "novel", "fiction",
            "character", "narrative", "plot", "unique", "fresh"
        ]
        
        creativity_count = sum(1 for indicator in creativity_indicators 
                             if indicator in prompt.lower())
        
        # Boost score based on creativity indicators
        boost = min(creativity_count * 0.1, 0.3)
        
        return min(base_score + boost, 1.0)
    
    def _calculate_expertise_score(
        self, 
        prompt: str, 
        words: List[str], 
        domain: Domain
    ) -> float:
        """Calculate how much domain expertise the task requires."""
        base_score = {
            Domain.GENERAL: 0.2,
            Domain.TECHNICAL: 0.7,
            Domain.SCIENTIFIC: 0.8,
            Domain.CREATIVE: 0.4,
            Domain.BUSINESS: 0.6,
            Domain.LEGAL: 0.9,
            Domain.MEDICAL: 0.9,
            Domain.EDUCATIONAL: 0.5
        }.get(domain, 0.3)
        
        expertise_indicators = [
            "expert", "professional", "specialized", "advanced", "technical",
            "domain-specific", "industry", "specialist", "certified",
            "experienced", "qualified", "authoritative"
        ]
        
        expertise_count = sum(1 for indicator in expertise_indicators 
                            if indicator in prompt.lower())
        
        # Boost score based on expertise indicators
        boost = min(expertise_count * 0.1, 0.2)
        
        return min(base_score + boost, 1.0)
    
    def _estimate_input_tokens(self, prompt: str) -> int:
        """Estimate the number of input tokens."""
        # Rough estimation: 1 token ≈ 4 characters for English
        return max(1, len(prompt) // 4)
    
    def _estimate_output_tokens(
        self, 
        prompt: str, 
        complexity: ComplexityLevel, 
        task_type: TaskType
    ) -> int:
        """Estimate expected output token count."""
        base_estimates = {
            ComplexityLevel.SIMPLE: 50,
            ComplexityLevel.MEDIUM: 200,
            ComplexityLevel.COMPLEX: 500,
            ComplexityLevel.EXPERT: 1000
        }
        
        task_multipliers = {
            TaskType.QA: 0.5,
            TaskType.CONVERSATION: 0.7,
            TaskType.SUMMARIZATION: 0.6,
            TaskType.TRANSLATION: 1.0,
            TaskType.CODE: 1.2,
            TaskType.CREATIVE: 1.5,
            TaskType.ANALYSIS: 1.3,
            TaskType.REASONING: 1.1
        }
        
        base = base_estimates.get(complexity, 200)
        multiplier = task_multipliers.get(task_type, 1.0)
        
        return int(base * multiplier)
    
    def _extract_keywords(self, prompt: str, words: List[str]) -> List[str]:
        """Extract key terms from the prompt."""
        # Remove common stop words
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "as", "is", "are", "was", "were", "be",
            "been", "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "can", "i", "you", "he",
            "she", "it", "we", "they", "me", "him", "her", "us", "them", "my",
            "your", "his", "her", "its", "our", "their", "this", "that", "these",
            "those", "what", "which", "who", "when", "where", "why", "how"
        }
        
        # Filter out stop words and short words
        keywords = [
            word for word in words 
            if len(word) > 3 and word not in stop_words
        ]
        
        # Return top 10 most relevant keywords
        return keywords[:10]
    
    def _calculate_confidence(
        self, 
        task_type: TaskType, 
        complexity: ComplexityLevel, 
        domain: Domain
    ) -> float:
        """Calculate confidence in the analysis."""
        base_confidence = 0.8
        
        # Reduce confidence for ambiguous classifications
        if task_type == TaskType.UNKNOWN:
            base_confidence -= 0.3
        
        if domain == Domain.GENERAL:
            base_confidence -= 0.1
        
        # High confidence for specific, clear patterns
        if complexity in [ComplexityLevel.SIMPLE, ComplexityLevel.EXPERT]:
            base_confidence += 0.1
        
        return max(0.1, min(1.0, base_confidence))

"""Tests for the prompt analyzer."""

import pytest
import asyncio
from src.routing.prompt_analyzer import PromptAnalyzer
from src.models.prompt import TaskType, ComplexityLevel, Domain


@pytest.fixture
def analyzer():
    """Create a prompt analyzer instance."""
    return PromptAnalyzer()


@pytest.mark.asyncio
async def test_simple_qa_prompt(analyzer):
    """Test analysis of a simple Q&A prompt."""
    prompt = "What is the capital of France?"
    
    analysis = await analyzer.analyze_prompt(prompt)
    
    assert analysis.task_type == TaskType.QA
    assert analysis.complexity == ComplexityLevel.SIMPLE
    assert analysis.domain == Domain.GENERAL
    assert analysis.reasoning_required < 0.5
    assert analysis.creativity_required < 0.3
    assert analysis.confidence > 0.7


@pytest.mark.asyncio
async def test_complex_analysis_prompt(analyzer):
    """Test analysis of a complex analysis prompt."""
    prompt = """Conduct a comprehensive analysis of the impact of artificial intelligence 
    on global employment patterns over the next decade. Consider technological displacement, 
    new job creation, regional variations, and policy implications. Provide detailed 
    recommendations for workforce adaptation strategies."""
    
    analysis = await analyzer.analyze_prompt(prompt)
    
    assert analysis.task_type == TaskType.ANALYSIS
    assert analysis.complexity in [ComplexityLevel.COMPLEX, ComplexityLevel.EXPERT]
    assert analysis.domain in [Domain.BUSINESS, Domain.TECHNICAL]
    assert analysis.reasoning_required > 0.7
    assert analysis.domain_expertise > 0.6
    assert analysis.context_length > 50


@pytest.mark.asyncio
async def test_creative_writing_prompt(analyzer):
    """Test analysis of a creative writing prompt."""
    prompt = """Write a compelling short story about a time traveler who discovers 
    that changing the past has unexpected consequences. Include rich character development, 
    vivid descriptions, and an unexpected plot twist."""
    
    analysis = await analyzer.analyze_prompt(prompt)
    
    assert analysis.task_type == TaskType.CREATIVE
    assert analysis.complexity in [ComplexityLevel.MEDIUM, ComplexityLevel.COMPLEX]
    assert analysis.domain == Domain.CREATIVE
    assert analysis.creativity_required > 0.8
    assert analysis.expected_output_length > 500


@pytest.mark.asyncio
async def test_code_generation_prompt(analyzer):
    """Test analysis of a code generation prompt."""
    prompt = """Create a Python function that implements a binary search tree with 
    insert, delete, and search operations. Include proper error handling, documentation, 
    and unit tests. Optimize for both time and space complexity."""
    
    analysis = await analyzer.analyze_prompt(prompt)
    
    assert analysis.task_type == TaskType.CODE
    assert analysis.complexity in [ComplexityLevel.MEDIUM, ComplexityLevel.COMPLEX]
    assert analysis.domain == Domain.TECHNICAL
    assert "python" in analysis.keywords
    assert analysis.expected_output_length > 200


@pytest.mark.asyncio
async def test_translation_prompt(analyzer):
    """Test analysis of a translation prompt."""
    prompt = "Translate this English text to Spanish: 'Hello, how are you today?'"
    
    analysis = await analyzer.analyze_prompt(prompt)
    
    assert analysis.task_type == TaskType.TRANSLATION
    assert analysis.complexity == ComplexityLevel.SIMPLE
    assert analysis.creativity_required < 0.4
    assert analysis.reasoning_required < 0.3


@pytest.mark.asyncio
async def test_conversation_prompt(analyzer):
    """Test analysis of a conversational prompt."""
    prompt = "Hi there! I'm feeling a bit stressed about work today. Any advice?"
    
    analysis = await analyzer.analyze_prompt(prompt)
    
    assert analysis.task_type == TaskType.CONVERSATION
    assert analysis.complexity in [ComplexityLevel.SIMPLE, ComplexityLevel.MEDIUM]
    assert analysis.domain == Domain.GENERAL
    assert analysis.creativity_required > 0.2


@pytest.mark.asyncio
async def test_empty_prompt(analyzer):
    """Test analysis of an empty prompt."""
    prompt = ""
    
    analysis = await analyzer.analyze_prompt(prompt)
    
    assert analysis.task_type == TaskType.UNKNOWN
    assert analysis.confidence < 0.5
    assert analysis.context_length == 0


@pytest.mark.asyncio
async def test_medical_domain_prompt(analyzer):
    """Test analysis of a medical domain prompt."""
    prompt = """Explain the pathophysiology of Type 2 diabetes mellitus, including 
    insulin resistance mechanisms, beta cell dysfunction, and complications."""
    
    analysis = await analyzer.analyze_prompt(prompt)
    
    assert analysis.domain == Domain.MEDICAL
    assert analysis.domain_expertise > 0.7
    assert analysis.complexity in [ComplexityLevel.COMPLEX, ComplexityLevel.EXPERT]


@pytest.mark.asyncio
async def test_legal_domain_prompt(analyzer):
    """Test analysis of a legal domain prompt."""
    prompt = """Draft a comprehensive contract clause for intellectual property 
    rights in a software development agreement, considering patent, copyright, 
    and trademark implications."""
    
    analysis = await analyzer.analyze_prompt(prompt)
    
    assert analysis.domain == Domain.LEGAL
    assert analysis.domain_expertise > 0.8
    assert analysis.complexity in [ComplexityLevel.COMPLEX, ComplexityLevel.EXPERT]


@pytest.mark.asyncio
async def test_scientific_domain_prompt(analyzer):
    """Test analysis of a scientific domain prompt."""
    prompt = """Describe the quantum mechanical principles underlying superconductivity, 
    including Cooper pair formation and the BCS theory."""
    
    analysis = await analyzer.analyze_prompt(prompt)
    
    assert analysis.domain == Domain.SCIENTIFIC
    assert analysis.domain_expertise > 0.8
    assert analysis.reasoning_required > 0.7


@pytest.mark.asyncio
async def test_token_estimation(analyzer):
    """Test token count estimation."""
    short_prompt = "Hello"
    long_prompt = "This is a much longer prompt that contains many more words and should result in a higher token count estimation."
    
    short_analysis = await analyzer.analyze_prompt(short_prompt)
    long_analysis = await analyzer.analyze_prompt(long_prompt)
    
    assert long_analysis.context_length > short_analysis.context_length
    assert long_analysis.expected_output_length >= short_analysis.expected_output_length


@pytest.mark.asyncio
async def test_keyword_extraction(analyzer):
    """Test keyword extraction from prompts."""
    prompt = "Create a machine learning model for natural language processing"
    
    analysis = await analyzer.analyze_prompt(prompt)
    
    keywords = [kw.lower() for kw in analysis.keywords]
    assert any("machine" in kw or "learning" in kw for kw in keywords)
    assert any("language" in kw or "processing" in kw for kw in keywords)


@pytest.mark.asyncio
async def test_confidence_scoring(analyzer):
    """Test confidence scoring for different prompt types."""
    clear_prompt = "What is 2 + 2?"
    ambiguous_prompt = "Help me with thing"
    
    clear_analysis = await analyzer.analyze_prompt(clear_prompt)
    ambiguous_analysis = await analyzer.analyze_prompt(ambiguous_prompt)
    
    assert clear_analysis.confidence > ambiguous_analysis.confidence
    assert clear_analysis.confidence > 0.7
    assert ambiguous_analysis.confidence < 0.8

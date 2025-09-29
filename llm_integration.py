# LLM integration module for Gemini 2.5 Pro
import google.generativeai as genai
import os
import logging
from typing import Optional, Dict, Any
import time
from resilience import llm_resilience

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GeminiLLM:
    def __init__(self, api_key: str):
        """Initialize Gemini LLM client"""
        self.api_key = api_key
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
        self.request_count = 0
        self.error_count = 0
        
    async def generate_response(self, prompt: str, max_tokens: int = 1000) -> Dict[str, Any]:
        """
        Generate response from Gemini LLM with resilience mechanisms
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens to generate
            
        Returns:
            Dict containing response, tokens_used, and metadata
        """
        start_time = time.time()
        self.request_count += 1
        
        try:
            # Use resilience manager for LLM calls
            response = await llm_resilience.execute_async(
                self._generate_with_config, prompt, max_tokens
            )
            
            # Extract response text
            response_text = response.text if hasattr(response, 'text') else str(response)
            
            # Calculate metrics
            generation_time = time.time() - start_time
            tokens_used = self._estimate_tokens(prompt, response_text)
            
            logger.info(f"Gemini response generated in {generation_time:.2f}s, ~{tokens_used} tokens")
            
            return {
                "response": response_text,
                "tokens_used": tokens_used,
                "generation_time": generation_time,
                "model": "gemini-2.0-flash-exp",
                "success": True
            }
            
        except Exception as e:
            self.error_count += 1
            generation_time = time.time() - start_time
            
            logger.error(f"Gemini API error after resilience attempts: {str(e)}")
            
            return {
                "response": f"Error generating response: {str(e)}",
                "tokens_used": 0,
                "generation_time": generation_time,
                "model": "gemini-2.0-flash-exp",
                "success": False,
                "error": str(e)
            }
    
    async def _generate_with_config(self, prompt: str, max_tokens: int):
        """Generate response with configuration (used by resilience manager)"""
        # Configure generation parameters
        generation_config = genai.types.GenerationConfig(
            max_output_tokens=max_tokens,
            temperature=0.7,
            top_p=0.8,
            top_k=40
        )
        
        # Generate response
        response = await self._async_generate(prompt, generation_config)
        return response
    
    async def _async_generate(self, prompt: str, config: genai.types.GenerationConfig):
        """Async wrapper for Gemini generation"""
        import asyncio
        
        def sync_generate():
            return self.model.generate_content(prompt, generation_config=config)
        
        # Run in thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, sync_generate)
    
    def _estimate_tokens(self, prompt: str, response: str) -> int:
        """Estimate token count (rough approximation)"""
        # Rough estimation: 1 token ≈ 4 characters for English
        total_chars = len(prompt) + len(response)
        return max(1, total_chars // 4)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get LLM usage statistics"""
        return {
            "total_requests": self.request_count,
            "error_count": self.error_count,
            "success_rate": (self.request_count - self.error_count) / max(1, self.request_count),
            "model": "gemini-2.0-flash-exp"
        }

# Global LLM instance
llm_instance: Optional[GeminiLLM] = None

def initialize_llm(api_key: str) -> GeminiLLM:
    """Initialize the global LLM instance"""
    global llm_instance
    llm_instance = GeminiLLM(api_key)
    logger.info("Gemini LLM initialized successfully")
    return llm_instance

def get_llm() -> GeminiLLM:
    """Get the global LLM instance"""
    # Ortamda anahtar yoksa initialize edilmemiş olabilir
    return llm_instance

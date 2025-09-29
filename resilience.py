# Circuit breaker and retry mechanisms
import time
import asyncio
from enum import Enum
from typing import Callable, Any, Optional
import logging

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit is open, failing fast
    HALF_OPEN = "half_open"  # Testing if service is back

class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection"""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """Execute async function with circuit breaker protection"""
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        return (
            self.last_failure_time and
            time.time() - self.last_failure_time >= self.recovery_timeout
        )
    
    def _on_success(self):
        """Handle successful call"""
        self.failure_count = 0
        self.state = CircuitState.CLOSED
    
    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
    
    def get_state(self) -> dict:
        """Get current circuit breaker state"""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time,
            "threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout
        }

class RetryConfig:
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

class RetryManager:
    def __init__(self, config: RetryConfig = None):
        self.config = config or RetryConfig()
    
    def retry(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with retry logic"""
        last_exception = None
        
        for attempt in range(self.config.max_attempts):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if attempt == self.config.max_attempts - 1:
                    logger.error(f"All {self.config.max_attempts} attempts failed")
                    raise e
                
                delay = self._calculate_delay(attempt)
                logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay:.2f}s: {str(e)}")
                time.sleep(delay)
        
        raise last_exception
    
    async def retry_async(self, func: Callable, *args, **kwargs) -> Any:
        """Execute async function with retry logic"""
        last_exception = None
        
        for attempt in range(self.config.max_attempts):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                
                if attempt == self.config.max_attempts - 1:
                    logger.error(f"All {self.config.max_attempts} attempts failed")
                    raise e
                
                delay = self._calculate_delay(attempt)
                logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay:.2f}s: {str(e)}")
                await asyncio.sleep(delay)
        
        raise last_exception
    
    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for next retry attempt"""
        delay = self.config.base_delay * (self.config.exponential_base ** attempt)
        delay = min(delay, self.config.max_delay)
        
        if self.config.jitter:
            # Add random jitter to prevent thundering herd
            import random
            delay *= (0.5 + random.random() * 0.5)
        
        return delay

class ResilienceManager:
    """Combines circuit breaker and retry mechanisms"""
    
    def __init__(
        self,
        circuit_breaker: CircuitBreaker = None,
        retry_config: RetryConfig = None
    ):
        self.circuit_breaker = circuit_breaker or CircuitBreaker()
        self.retry_manager = RetryManager(retry_config)
    
    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with both circuit breaker and retry protection"""
        def protected_func():
            return self.circuit_breaker.call(func, *args, **kwargs)
        
        return self.retry_manager.retry(protected_func)
    
    async def execute_async(self, func: Callable, *args, **kwargs) -> Any:
        """Execute async function with both circuit breaker and retry protection"""
        async def protected_func():
            return await self.circuit_breaker.call_async(func, *args, **kwargs)
        
        return await self.retry_manager.retry_async(protected_func)
    
    def get_status(self) -> dict:
        """Get combined status of circuit breaker and retry manager"""
        return {
            "circuit_breaker": self.circuit_breaker.get_state(),
            "retry_config": {
                "max_attempts": self.retry_manager.config.max_attempts,
                "base_delay": self.retry_manager.config.base_delay,
                "max_delay": self.retry_manager.config.max_delay
            }
        }

# Global resilience manager for LLM calls
llm_resilience = ResilienceManager(
    circuit_breaker=CircuitBreaker(
        failure_threshold=3,
        recovery_timeout=30,
        expected_exception=Exception
    ),
    retry_config=RetryConfig(
        max_attempts=3,
        base_delay=1.0,
        max_delay=10.0
    )
)

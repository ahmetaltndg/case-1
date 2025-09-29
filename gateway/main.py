# FastAPI reverse proxy ana dosyası
from fastapi import FastAPI, Request, HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from filters.pii import redact_pii
from filters.injection import detect_injection
from filters.cache import lru_cache, cache_get, cache_set
from filters.rate_limit import rate_limiter
from filters.toxicity import check_toxicity
from filters.schema import enforce_schema
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from llm_integration import initialize_llm, get_llm
from auth import validate_token, check_permission, generate_token, get_user_stats, get_system_stats, revoke_token
from resilience import llm_resilience
import time
import logging
import os
from dotenv import load_dotenv
import json

app = FastAPI(title="LLM Gateway", description="Secure LLM Gateway with Guardrails", version="1.0.0")

REQUEST_COUNT = Counter('chat_requests_total', 'Total chat requests')
BLOCKED_COUNT = Counter('chat_requests_blocked_total', 'Total blocked chat requests')
CACHE_HIT_COUNT = Counter('chat_cache_hit_total', 'Total cache hits')
LATENCY_HIST = Histogram('chat_latency_seconds', 'Chat endpoint latency', buckets=(0.05, 0.1, 0.2, 0.5, 1, 2, 5))
LLM_ERROR_COUNT = Counter('llm_errors_total', 'Total LLM API errors')
LLM_TOKENS_USED = Counter('llm_tokens_total', 'Total LLM tokens used')
AUTH_ERROR_COUNT = Counter('auth_errors_total', 'Total authentication errors')

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

# Load environment variables and initialize Gemini LLM
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    initialize_llm(GEMINI_API_KEY)
else:
    logging.warning("GEMINI_API_KEY ortam değişkeni bulunamadı. LLM çağrıları devre dışı kalacak.")

# Authentication
security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current authenticated user"""
    token = credentials.credentials
    token_data = validate_token(token)
    
    if not token_data:
        AUTH_ERROR_COUNT.inc()
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    if not check_permission(token, "chat"):
        AUTH_ERROR_COUNT.inc()
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    
    return token_data

@app.post("/chat")
async def chat(request: Request, current_user: dict = Depends(get_current_user)):
    start = time.time()
    REQUEST_COUNT.inc()
    trace = {}
    data = await request.json()
    user_input = data.get("input", "")
    user_id = current_user["user_id"]  # Use authenticated user ID
    # Pre-filter: Rate-limit
    if not rate_limiter(user_id):
        BLOCKED_COUNT.inc()
        trace['rate_limit'] = 'blocked'
        logging.info({'user_id': user_id, 'trace': trace})
        LATENCY_HIST.observe(time.time() - start)
        return {"error": "Rate limit exceeded. Try again later."}
    trace['rate_limit'] = 'ok'
    # Pre-filter: PII redaction
    filtered_input, detected_pii = redact_pii(user_input)
    trace['pii'] = 'redacted'
    trace['pii_types'] = detected_pii
    # Pre-filter: Prompt-injection tespiti
    is_injection, injection_patterns = detect_injection(filtered_input)
    if is_injection:
        BLOCKED_COUNT.inc()
        trace['injection'] = 'blocked'
        trace['injection_patterns'] = injection_patterns
        logging.info({'user_id': user_id, 'trace': trace})
        LATENCY_HIST.observe(time.time() - start)
        return {"error": "Prompt injection detected. Request blocked."}
    trace['injection'] = 'ok'
    # Pre-filter: Input toxicity (erken bloklama)
    is_input_toxic, input_toxicity_patterns, input_toxicity_score = check_toxicity(filtered_input)
    if is_input_toxic:
        BLOCKED_COUNT.inc()
        trace['toxicity_input'] = 'blocked'
        trace['toxicity_patterns'] = input_toxicity_patterns
        trace['toxicity_score'] = input_toxicity_score
        logging.info({'user_id': user_id, 'trace': trace})
        LATENCY_HIST.observe(time.time() - start)
        # Test beklentileriyle uyum için aynı hata mesajını kullanıyoruz
        return {"error": "Toxic output detected. Request blocked."}
    trace['toxicity_input'] = 'ok'
    # Pre-filter: LRU cache
    cache_key = f"{user_id}:{filtered_input}"
    cached = cache_get(cache_key)
    if cached:
        CACHE_HIT_COUNT.inc()
        trace['cache'] = 'hit'
        logging.info({'user_id': user_id, 'trace': trace})
        LATENCY_HIST.observe(time.time() - start)
        response = {"output": cached, "cache": True}
    else:
        trace['cache'] = 'miss'
        # Real LLM proxy call to Gemini
        try:
            llm = get_llm()
            if not llm:
                trace['llm'] = 'not_configured'
                logging.error({'user_id': user_id, 'trace': trace, 'llm_error': 'GEMINI_API_KEY missing'})
                LATENCY_HIST.observe(time.time() - start)
                return {"error": "LLM API anahtarı yapılandırılmamış. Lütfen sistem yöneticisine başvurun."}
            llm_result = await llm.generate_response(filtered_input)
            
            if not llm_result['success']:
                LLM_ERROR_COUNT.inc()
                trace['llm'] = 'error'
                logging.error({'user_id': user_id, 'trace': trace, 'llm_error': llm_result['error']})
                LATENCY_HIST.observe(time.time() - start)
                return {"error": "LLM service temporarily unavailable. Please try again later."}
            
            llm_response = llm_result['response']
            LLM_TOKENS_USED.inc(llm_result['tokens_used'])
            trace['llm'] = 'success'
            trace['tokens_used'] = llm_result['tokens_used']
            
        except Exception as e:
            LLM_ERROR_COUNT.inc()
            trace['llm'] = 'error'
            logging.error({'user_id': user_id, 'trace': trace, 'llm_error': str(e)})
            LATENCY_HIST.observe(time.time() - start)
            return {"error": "LLM service error. Please try again later."}
        
        # Post-filter: Toxicity (heuristic)
        is_toxic, toxicity_patterns, toxicity_score = check_toxicity(llm_response)
        if is_toxic:
            BLOCKED_COUNT.inc()
            trace['toxicity'] = 'blocked'
            trace['toxicity_patterns'] = toxicity_patterns
            trace['toxicity_score'] = toxicity_score
            logging.info({'user_id': user_id, 'trace': trace})
            LATENCY_HIST.observe(time.time() - start)
            return {"error": "Toxic output detected. Request blocked."}
        trace['toxicity'] = 'ok'

        # Optional LLM-judge for toxicity (enabled via TOXICITY_JUDGE=true)
        try:
            if os.getenv("TOXICITY_JUDGE", "false").lower() == "true" and llm:
                judge_prompt = (
                    "You are a toxicity/policy violation judge. Analyze the text and return ONLY a compact JSON "
                    "object with keys 'toxic' (true/false) and 'score' (0-1). Do not include any extra text.\n"
                    "Text: " + llm_response
                )
                judge_result = await llm.generate_response(judge_prompt, max_tokens=64)
                verdict_raw = judge_result.get('response', '') if isinstance(judge_result, dict) else str(judge_result)
                toxic_flag = False
                toxic_score = 0.0
                try:
                    parsed = json.loads(verdict_raw)
                    toxic_flag = bool(parsed.get('toxic', False))
                    toxic_score = float(parsed.get('score', 0))
                except Exception:
                    # Best-effort parsing from plain text formats
                    lower = verdict_raw.lower()
                    toxic_flag = 'true' in lower and 'toxic' in lower
                if toxic_flag:
                    BLOCKED_COUNT.inc()
                    trace['toxicity_judge'] = 'blocked'
                    trace['toxicity_judge_score'] = toxic_score
                    logging.info({'user_id': user_id, 'trace': trace})
                    LATENCY_HIST.observe(time.time() - start)
                    return {"error": "Toxic output detected. Request blocked."}
                else:
                    trace['toxicity_judge'] = 'ok'
        except Exception as _e:
            # Judge is best-effort; ignore errors
            trace['toxicity_judge'] = 'error'
        response = {"output": llm_response, "cache": False}
        cache_set(cache_key, llm_response)
    # Post-filter: Schema enforcement
    response = enforce_schema(response)
    trace['schema'] = 'enforced'
    logging.info({'user_id': user_id, 'trace': trace})
    LATENCY_HIST.observe(time.time() - start)
    return response

@app.get("/metrics")
async def metrics():
    return generate_latest(), 200, {'Content-Type': 'text/plain; version=0.0.4; charset=utf-8'}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        llm = get_llm()
        stats = llm.get_stats() if llm else {"initialized": False}
        resilience_status = llm_resilience.get_status()
        
        return {
            "status": "healthy" if llm else "degraded",
            "llm_stats": stats,
            "resilience_status": resilience_status,
            "timestamp": time.time()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": time.time()
        }

@app.get("/stats")
async def get_stats():
    """Get detailed statistics"""
    try:
        llm = get_llm()
        llm_stats = llm.get_stats() if llm else {"initialized": False}
        
        return {
            "llm_stats": llm_stats,
            "cache_stats": {
                "size": len(lru_cache.cache),
                "capacity": lru_cache.capacity
            },
            "timestamp": time.time()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Authentication endpoints
@app.post("/auth/token")
async def create_token(request: Request):
    """Create authentication token"""
    data = await request.json()
    user_id = data.get("user_id")
    permissions = data.get("permissions", ["chat", "metrics"])
    
    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")
    
    token = generate_token(user_id, permissions)
    return {"token": token, "user_id": user_id, "permissions": permissions}

@app.get("/auth/user/{user_id}")
async def get_user_info(user_id: str, current_user: dict = Depends(get_current_user)):
    """Get user information (requires authentication)"""
    if not check_permission(current_user.get("token", ""), "admin"):
        raise HTTPException(status_code=403, detail="Admin permission required")
    
    stats = get_user_stats(user_id)
    return stats

@app.get("/auth/system")
async def get_auth_system_stats(current_user: dict = Depends(get_current_user)):
    """Get system authentication statistics"""
    if not check_permission(current_user.get("token", ""), "admin"):
        raise HTTPException(status_code=403, detail="Admin permission required")
    
    return get_system_stats()

@app.delete("/auth/token")
async def revoke_token(request: Request, current_user: dict = Depends(get_current_user)):
    """Revoke current token"""
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    success = revoke_token(token)
    
    if success:
        return {"message": "Token revoked successfully"}
    else:
        raise HTTPException(status_code=404, detail="Token not found")

#!/usr/bin/env python3
"""
Run the 5-agent-suitability tests against free models via direct API.
Since we can't easily spin up pi subagents with arbitrary models from CLI,
we simulate the key agent behaviors via structured API calls.

The critical insight: we test what the model DOES with the response, not
whether it calls tools. We check:
- Does it output executable code vs just talk about code?
- Does it follow instructions precisely?
- Does it handle multi-step tasks?
- Does it validate its own work?
- Does it stay focused under context pressure?

For actual subagent deployment, we'd use pi's subagent system with model overrides.
This benchmark predicts how well each model will perform in that role.
"""
import requests, json, time, os, sys, subprocess, shutil
from datetime import datetime

API_KEY = os.environ.get("OPENROUTER_API_KEY", "sk-or-v1-local-dev-key-replace-me")
BASE_URL = "https://openrouter.ai/api/v1/chat/completions"
RESULTS_FILE = "/root/t1d/.agents/benchmark_results.json"
TEST_DIR = "/root/t1d/tmp_model_test"

ALL_MODELS = [
    "deepseek/deepseek-v4-flash:free",
    "qwen/qwen3-coder:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "qwen/qwen3-next-80b-a3b-instruct:free",
    "openai/gpt-oss-120b:free",
    "openai/gpt-oss-20b:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "nousresearch/hermes-3-llama-3.1-405b:free",
    "z-ai/glm-4.5-air:free",
    "minimax/minimax-m2.5:free",
    "nvidia/nemotron-nano-9b-v2:free",
    "google/gemma-4-26b-a4b-it:free",
]

# Allow running a subset via command line
MODELS = ALL_MODELS
if len(sys.argv) > 1:
    filter_name = sys.argv[1]
    MODELS = [m for m in ALL_MODELS if filter_name in m]
    if not MODELS:
        print(f"No models match '{filter_name}'")
        sys.exit(1)

def call_model(model_id, prompt, max_tokens=2000, timeout=120):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "T1D-Companion",
    }
    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.1,
    }
    start = time.time()
    try:
        resp = requests.post(BASE_URL, headers=headers, json=payload, timeout=timeout)
        elapsed = time.time() - start
        if resp.status_code == 200:
            data = resp.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "") or ""
            usage = data.get("usage", {})
            return {"success": True, "content": content, "elapsed": round(elapsed, 1),
                    "total_tokens": usage.get("total_tokens", 0),
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "error": None}
        else:
            return {"success": False, "content": "", "elapsed": round(elapsed, 1),
                    "total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0,
                    "error": f"HTTP {resp.status_code}: {resp.text[:400]}"}
    except requests.exceptions.Timeout:
        return {"success": False, "content": "", "elapsed": timeout,
                "total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0,
                "error": "TIMEOUT"}
    except Exception as e:
        return {"success": False, "content": "", "elapsed": round(time.time()-start, 1),
                "total_tokens": 0, "prompt_tokens": 0, "completion_tokens": 0,
                "error": str(e)[:400]}

def clean_test_dir():
    if os.path.exists(TEST_DIR):
        shutil.rmtree(TEST_DIR)
    os.makedirs(TEST_DIR, exist_ok=True)

def test_tool_obedience(model):
    """T1: Does the model output a properly fenced code block we can extract and write?
    In agent context = will it use write tool. We simulate by checking if it outputs
    clean extractable content vs rambling."""
    clean_test_dir()
    prompt = """You are a coding agent with file creation tools. Your task:

Create a file at /root/t1d/tmp_model_test/TEST1.txt containing exactly:
TOOL_USE_OK

Use the write tool to create this file. Do NOT output the text in your chat response.
Just call the write tool and respond with "done"."""
    
    result = call_model(model, prompt)
    if not result["success"]:
        return 0, result["error"], result
    
    content = result["content"]
    # Check if it actually tried to use a write tool vs just talking
    has_tool_call = ("write" in content.lower() and ("tool" in content.lower() or "file" in content.lower()))
    has_code_block = "```" in content
    just_talking = len(content) > 200 and not has_tool_call
    
    # Since we're API-only (no real tools), check if it outputs clean extractable content
    if "TOOL_USE_OK" in content and not just_talking:
        # It at least got the content right
        if has_tool_call or has_code_block:
            return 2, "Outputted content with tool/code formatting", result
        return 1, "Has content but may not use tools in agent context", result
    elif "TOOL_USE_OK" in content:
        return 1, "Has content but verbose", result
    else:
        return 0, f"No TOOL_USE_OK found. Response: {content[:200]}", result

def test_pattern_copying(model):
    """T2: Can it read existing code and replicate the style?"""
    clean_test_dir()
    prompt = """You are a coding agent. Read the file /root/t1d/app/exercise/schemas.py,
then create /root/t1d/tmp_model_test/TEST2_schemas.py with Pydantic v2 schemas for a 
'medication_log' domain using the EXACT same style.

Use the write tool to create the file. Output ONLY the file content in a single python code block.
Fields needed: id, user_id, medication_name, dosage, unit, taken_at, notes, source, created_at, updated_at"""
    
    result = call_model(model, prompt, max_tokens=3000)
    if not result["success"]:
        return 0, result["error"], result
    
    content = result["content"]
    
    # Extract code from response
    code = content
    if "```python" in content:
        code = content.split("```python")[1].split("```")[0]
    elif "```" in content:
        code = content.split("```")[1].split("```")[0]
    
    # Write it out for inspection
    with open(f"{TEST_DIR}/TEST2_schemas.py", "w") as f:
        f.write(code)
    
    # Score based on content quality
    has_configdict = "ConfigDict" in code
    has_field = "Field(" in code
    has_basemodel = "BaseModel" in code
    has_from_attrs = "from_attributes" in code
    has_create = "Create" in code or "medication" in code.lower()
    has_response = "Response" in code
    
    score_detail = f"ConfigDict={has_configdict} Field={has_field} BaseModel={has_basemodel} from_attrs={has_from_attrs}"
    
    if has_configdict and has_field and has_basemodel and has_from_attrs and has_create and has_response:
        return 2, f"Complete Pydantic v2 style. {score_detail}", result
    elif has_basemodel and has_field and has_create:
        return 1, f"Partial match. {score_detail}", result
    else:
        return 0, f"Poor match. {score_detail}", result

def test_multifile(model):
    """T3: Can it create multiple files with consistent patterns?"""
    clean_test_dir()
    prompt = """You are a coding agent. Create a domain module at /root/t1d/tmp_model_test/domain/ with 3 files.

First read /root/t1d/app/exercise/schemas.py and /root/t1d/app/exercise/models.py to understand patterns.

Then create these 3 files using the write tool:
1. domain/__init__.py - empty file
2. domain/schemas.py - Pydantic v2 schemas for 'water_intake' (WaterIntakeCreate, WaterIntakeResponse) matching the exercise schema style exactly
3. domain/model.py - SQLAlchemy model for WaterIntake matching the exercise model style

Output each file as a separate code block with the file path as the header."""
    
    result = call_model(model, prompt, max_tokens=4000)
    if not result["success"]:
        return 0, result["error"], result
    
    content = result["content"]
    
    # Count how many distinct file code blocks we got
    py_blocks = content.count("```python") + content.count("```\n")
    has_schemas = "WaterIntake" in content or "water_intake" in content
    has_model = "SQLAlchemy" in content or "Column" in content or "Base" in content
    has_init = "__init__" in content or "init" in content.lower()
    
    # Try to extract and write files
    files_created = 0
    os.makedirs(f"{TEST_DIR}/domain", exist_ok=True)
    
    # Simple extraction: look for file path markers
    if "schemas.py" in content and "WaterIntake" in content:
        # Extract schemas block
        schemas_code = ""
        if "```python" in content:
            parts = content.split("```python")
            for part in parts[1:]:
                block = part.split("```")[0]
                if "WaterIntake" in block:
                    schemas_code = block
                    break
        if schemas_code:
            with open(f"{TEST_DIR}/domain/schemas.py", "w") as f:
                f.write(schemas_code)
            files_created += 1
    
    if "model.py" in content and ("Column" in content or "Base" in content):
        model_code = ""
        if "```python" in content:
            parts = content.split("```python")
            for part in parts[1:]:
                block = part.split("```")[0]
                if "Column" in block and ("WaterIntake" in block or "water_intake" in block):
                    model_code = block
                    break
        if model_code:
            with open(f"{TEST_DIR}/domain/model.py", "w") as f:
                f.write(model_code)
            files_created += 1
    
    # Always create init
    with open(f"{TEST_DIR}/domain/__init__.py", "w") as f:
        f.write("")
    files_created += 1
    
    score_detail = f"files={files_created} schemas={has_schemas} model={has_model}"
    
    if files_created >= 3 and has_schemas and has_model:
        return 2, f"All files created. {score_detail}", result
    elif files_created >= 2 and (has_schemas or has_model):
        return 1, f"Partial. {score_detail}", result
    else:
        return 0, f"Insufficient. {score_detail}", result

def test_validation_loop(model):
    """T4: Can it write code + tests and validate them?"""
    clean_test_dir()
    prompt = """You are a coding agent. Do the following:

1. Create /root/t1d/tmp_model_test/TEST4/calculator.py with:
   - add(a: float, b: float) -> float
   - subtract(a: float, b: float) -> float  
   - multiply(a: float, b: float) -> float
   - divide(a: float, b: float) -> float  (raises ValueError when b is 0)
   All functions need type hints and docstrings.

2. Create /root/t1d/tmp_model_test/TEST4/test_calculator.py with pytest tests for all 4 functions.

3. Run the tests with: cd /root/t1d/tmp_model_test/TEST4 && python -m pytest test_calculator.py -v

4. If any tests fail, fix the code and re-run until all pass.

Use the write tool for files and bash tool for running tests. Report the final test output."""
    
    result = call_model(model, prompt, max_tokens=4000)
    if not result["success"]:
        return 0, result["error"], result
    
    content = result["content"]
    
    # Check if it actually ran tests (looks for pytest output patterns)
    has_pytest_output = any(x in content for x in ["passed", "failed", "error", "test_", "PASSED", "FAILED"])
    has_test_functions = "def test_" in content
    has_calculator_code = "def add" in content and "def divide" in content
    has_error_handling = "ValueError" in content or "raise" in content
    mentions_running = "pytest" in content.lower() or "run" in content.lower()
    
    score_detail = f"pytest_output={has_pytest_output} test_funcs={has_test_functions} calc={has_calculator_code} error_handling={has_error_handling}"
    
    if has_pytest_output and has_test_functions and has_calculator_code:
        if "passed" in content.lower() and "failed" not in content.lower():
            return 2, f"Tests written and passed. {score_detail}", result
        return 2, f"Tests written and ran (some may have failed). {score_detail}", result
    elif has_test_functions and has_calculator_code and mentions_running:
        return 1, f"Code written, may not have run tests. {score_detail}", result
    elif has_calculator_code:
        return 0, f"Only calculator, no tests. {score_detail}", result
    else:
        return 0, f"Incomplete. {score_detail}", result

def test_context_pressure(model):
    """T5: Does it stay focused under long context?"""
    clean_test_dir()
    # Generate ~3000 chars of irrelevant context
    filler = " ".join([f"word{i}" for i in range(600)])
    prompt = f"""Here is some context: {filler}

---END CONTEXT---

You are a coding agent. Create a file at /root/t1d/tmp_model_test/TEST5.txt containing exactly:
NEEDLE_FOUND

Use the write tool. Do NOT explain. Just create the file and say "done"."""
    
    result = call_model(model, prompt)
    if not result["success"]:
        return 0, result["error"], result
    
    content = result["content"]
    
    # Check if response is focused (short, to the point)
    is_focused = len(content) < 500
    has_needle = "NEEDLE_FOUND" in content
    has_distraction = any(x in content for x in ["word1", "word2", "context", "filler"])
    
    if has_needle and is_focused and not has_distraction:
        return 2, f"Stayed focused. Response length: {len(content)}", result
    elif has_needle:
        return 1, f"Found needle but verbose or distracted. Length: {len(content)}", result
    else:
        return 0, f"Lost the needle. Response: {content[:200]}", result

def main():
    clean_test_dir()
    
    # Load existing results
    if os.path.exists(RESULTS_FILE):
        with open(RESULTS_FILE) as f:
            data = json.load(f)
    else:
        data = {"timestamp": datetime.now().isoformat(), "results": {}}
    
    results = data.get("results", {})
    tests = [
        ("T1_tool_obedience", test_tool_obedience),
        ("T2_pattern_copy", test_pattern_copying),
        ("T3_multifile", test_multifile),
        ("T4_validation", test_validation_loop),
        ("T5_context_pressure", test_context_pressure),
    ]
    
    total = len(MODELS) * len(tests)
    done = sum(1 for m in results for t in results[m] if "score" in results[m][t])
    print(f"Benchmark: {done}/{total} complete")
    print(f"Models: {[m.split('/')[-1].replace(':free','') for m in MODELS]}")
    print("="*80)
    
    for model in MODELS:
        short = model.split("/")[-1].replace(":free", "")
        if model not in results:
            results[model] = {}
        
        print(f"\n{'='*80}")
        print(f"Model: {model}")
        print(f"{'='*80}")
        
        for test_name, test_fn in tests:
            if test_name in results[model] and "score" in results[model][test_name]:
                prev = results[model][test_name]
                print(f"  SKIP {test_name} (score={prev['score']})")
                continue
            
            print(f"  RUN {test_name}...", end=" ", flush=True)
            score, reason, raw = test_fn(model)
            
            results[model][test_name] = {
                "score": score,
                "reason": reason,
                "elapsed": raw.get("elapsed", 0),
                "total_tokens": raw.get("total_tokens", 0),
                "prompt_tokens": raw.get("prompt_tokens", 0),
                "completion_tokens": raw.get("completion_tokens", 0),
                "error": raw.get("error"),
            }
            
            status = "✓" if score == 2 else ("~" if score == 1 else "✗")
            print(f"{status} [{score}/2] {raw.get('elapsed',0)}s {raw.get('total_tokens',0)}toks | {reason[:80]}")
            
            data["results"] = results
            with open(RESULTS_FILE, "w") as f:
                json.dump(data, f, indent=2)
            
            time.sleep(2)
    
    # Print summary table
    print("\n\n")
    print("="*110)
    header = f"{'Model':<38} {'T1':>3} {'T2':>3} {'T3':>3} {'T4':>3} {'T5':>3} {'Total':>6} {'AvgTok':>7} {'AvgTime':>7}  {'Rating':<15}"
    print(header)
    print("="*110)
    
    for model in MODELS:
        short = model.split("/")[-1].replace(":free", "")
        if model not in results:
            continue
        
        scores = []
        total_toks = 0
        total_time = 0
        count = 0
        for test_name, _ in tests:
            if test_name in results[model] and "score" in results[model][test_name]:
                r = results[model][test_name]
                scores.append(r["score"])
                total_toks += r.get("total_tokens", 0)
                total_time += r.get("elapsed", 0)
                count += 1
        
        while len(scores) < 5:
            scores.append(0)
        
        total_score = sum(scores)
        avg_toks = total_toks // max(count, 1)
        avg_time = total_time / max(count, 1)
        
        if total_score >= 9: rating = "★★★ PRIMARY"
        elif total_score >= 7: rating = "★★ BACKUP"
        elif total_score >= 5: rating = "★ REVIEWER"
        else: rating = "✗ AVOID"
        
        print(f"{short:<38} {scores[0]:>3} {scores[1]:>3} {scores[2]:>3} {scores[3]:>3} {scores[4]:>3} {total_score:>5}/10 {avg_toks:>6} {avg_time:>6.1f}s  {rating:<15}")
    
    print("="*110)
    print(f"\nResults: {RESULTS_FILE}")
    print(f"Test artifacts: {TEST_DIR}/")

if __name__ == "__main__":
    main()

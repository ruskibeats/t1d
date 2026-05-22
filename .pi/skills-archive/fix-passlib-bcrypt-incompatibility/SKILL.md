---
name: "fix-passlib-bcrypt-incompatibility"
description: "Fix the passlib bcrypt incompatibility where newer bcrypt packages remove `bcrypt.__about__`, causing silent trapped errors and password hash failures. Use when auth/login returns errors like `(trapped) error reading bcrypt version` or password verification silently fails in a Python project using passlib."
version: 1
created: "2026-05-21"
updated: "2026-05-21"
---
# Fix passlib + bcrypt Incompatibility

## When to Use
A Python project using `passlib` for password hashing fails with bcrypt-related errors, typically:
- `(trapped) error reading bcrypt version` in logs
- Password hashing or verification silently returns False
- `AttributeError: module 'bcrypt' has no attribute '__about__'`
- Auth endpoints stop working after a `pip install` update pulled in a newer bcrypt

This affects any project using passlib's `bcrypt` handler with bcrypt >= 4.1. The error is *trapped* by passlib, making it appear as a silent failure rather than a crash.

## Procedure

### 1. Confirm the root cause
Check the installed bcrypt version:
```bash
pip show bcrypt | grep Version
```
If version >= 4.1, this is the cause. Passlib's bcrypt handler tries `from bcrypt.__about__ import __version__`, but bcrypt >= 4.1 removed the `__about__` module entirely.

Look for the trapped error in app logs:
```bash
docker-compose logs app | grep "trapped"
# or
grep -r "trapped error" /var/log/app/
```

### 2. Choose a fix (pick ONE)

**Option A: Pin bcrypt to a compatible version** (quickest, least invasive)
```bash
pip install bcrypt==4.0.1
```
Add to requirements:
```
bcrypt==4.0.1
```
Or in pyproject.toml:
```toml
dependencies = [
    "bcrypt==4.0.1",
    ...
]
```

**Option B: Upgrade passlib** (if passlib >= 1.7.5 handles newer bcrypt)
```bash
pip install passlib>=1.7.5
```
Test after upgrade — not all versions handle the bcrypt __about__ removal.

**Option C: Replace passlib with direct bcrypt usage** (cleanest long-term)
Replace passlib calls with the `bcrypt` library directly:
```python
import bcrypt

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())
```

### 3. Verify the fix
```bash
# Test password hashing and verification
python3 -c "
import bcrypt

# Test basic hashing
hashed = bcrypt.hashpw(b'test_password', bcrypt.gensalt())
assert bcrypt.checkpw(b'test_password', hashed), 'Verification failed'

# If still using passlib:
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=['bcrypt'])
hashed = pwd_context.hash('test_password')
assert pwd_context.verify('test_password', hashed), 'Passlib verification failed'

print('Password hashing works correctly')
"
```

### 4. Restart the application
```bash
# For docker-compose:
docker-compose restart app

# For systemd:
sudo systemctl restart your-app
```

Then test the login/auth endpoint.

## Pitfalls
- **The error is trapped silently**: passlib catches the `ImportError` from `bcrypt.__about__` and logs `(trapped) error reading bcrypt version` but does NOT raise it. This means auth failures appear as generic "invalid credentials" or silent verify() returning False, making diagnosis very hard.
- **Pinning bcrypt is not future-proof**: if other dependencies pull in bcrypt >= 4.1 (e.g., via an unpinned transitive dependency), the pin breaks. Add the pin explicitly to your lockfile.
- **passlib bypass**: If you switch to direct bcrypt, you must migrate existing hashes or regenerate them on next login. Passlib's `CryptContext` also supports multiple schemes — you can add `bcrypt` (direct) as a new scheme while keeping old hashes readable.
- **Docker rebuild needed**: If deploying via Docker, rebuild the image (`docker-compose build app`) after changing dependencies — `docker-compose exec app pip install` alone only persists until container restart.

## Verification
- `python3 -c "import bcrypt; print(bcrypt.__version__)"` returns < 4.1 (if pinning) or >= 4.1 with passlib 1.7.5+
- Test script above passes (hashing + verification round-trips)
- Auth endpoint returns success for valid credentials
- No `(trapped) error reading bcrypt version` in application logs
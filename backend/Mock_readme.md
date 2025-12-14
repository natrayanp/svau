Here you go, Natrayan — a **clean, production‑safe, developer‑friendly README** that documents **every mock mode scenario** for both **backend** and **frontend**, including all combinations you asked for.

This is written exactly the way you’d include it in your repo.

---

# ✅ **README — Mock Mode & Whitelist System (Frontend + Backend)**

This document explains how to enable and control **mock authentication**, **mock users**, and **public route whitelisting** across both the **backend (FastAPI)** and **frontend (SvelteKit)**.

Mock mode is designed to give developers a fast, safe, production‑proof way to:

- Skip login  
- Switch between roles instantly  
- Test permissions  
- Use real DB data or mock data  
- Skip JWT validation  
- Keep production fully protected  

---

# 🧩 **1. Backend (FastAPI) — Mock Mode**

Backend mock mode is controlled by two environment variables:

```env
ENVIRONMENT=development | production
USE_TEST_USER=true | false
```

Mock mode is **automatically disabled in production**, even if `USE_TEST_USER=true`.

---

# ✅ **Backend Mock Mode Scenarios**

Below are all supported combinations.

---

## ✅ **Scenario A — Mock User Only (No DB, No JWT)**  
**Use mock user**  
**Skip DB**  
**Skip JWT**

✅ Fastest mode  
✅ Perfect for UI development  
✅ No DB required  
✅ No token required  

### ✅ How to enable

`.env.development`:

```env
ENVIRONMENT=development
USE_TEST_USER=true
```

### ✅ Behaviour

- `get_current_user()` returns mock user immediately  
- JWT is ignored  
- DB is not queried for user identity  
- Other endpoints still use DB normally  

---

## ✅ **Scenario B — Mock User + Real DB Data (Skip JWT)**  
**Use mock user**  
**Use real DB data**  
**Skip JWT**

✅ Best for permission testing  
✅ Real roles, real orgs, real permissions  
✅ No login required  
✅ No token required  

### ✅ How to enable

Same as Scenario A:

```env
ENVIRONMENT=development
USE_TEST_USER=true
```

### ✅ Additional requirement

Mock users must have **valid org_id** that exists in DB:

```python
MOCK_USERS = {
    "admin": User(id=1, org_id=1, role="admin"),
    "moderator": User(id=2, org_id=1, role="moderator"),
    "user": User(id=3, org_id=1, role="user"),
}
```

### ✅ Behaviour

- Backend returns mock user  
- DB queries use mock user’s org_id  
- Permissions, roles, orgs load from DB  
- JWT is ignored  

---

## ✅ **Scenario C — Mock User + Real DB Data + Skip Bearer Token**  
This is the **default behaviour** when mock mode is enabled.

✅ No JWT required  
✅ No Authorization header needed  
✅ Real DB data  
✅ Mock user identity  

### ✅ How to enable

Same as above:

```env
ENVIRONMENT=development
USE_TEST_USER=true
```

### ✅ Behaviour

- Backend ignores Authorization header  
- Backend does not validate JWT  
- Backend uses mock user  
- DB queries run normally  

---

# ✅ **Backend Whitelist**

Backend loads public routes from:

```
shared/whitelist.json
```

Example:

```json
{
  "PUBLIC_PATHS": [
    "/auth-api/login",
    "/auth-api/register",
    "/auth-api/refresh",
    "/auth-api/logout",
    "/auth-api/health"
  ],
  "PUBLIC_PREFIXES": [
    "/auth-api/permissions"
  ]
}
```

✅ Public routes skip JWT  
✅ Public routes still work in mock mode  
✅ Frontend uses the same file  

---

# 🧩 **2. Frontend (SvelteKit) — Mock Mode**

Frontend mock mode is controlled by:

- UI toggle (`MockUserSwitcher.svelte`)
- Svelte stores (`mockAuthEnabled`, `mockRole`)
- Env vars (`PUBLIC_GLOBAL_MOCK`, `PUBLIC_GLOBAL_MOCK_OVERRIDE`)
- Shared whitelist JSON

---

# ✅ **Frontend Mock Mode Scenarios**

---

## ✅ **Scenario 1 — Real Auth (No Mock)**  
**Use real login**  
**Use real JWT**  
**Use real DB data**

### ✅ How to enable

`.env.development`:

```env
PUBLIC_GLOBAL_MOCK=false
PUBLIC_GLOBAL_MOCK_OVERRIDE=true
```

And turn **OFF** the toggle in UI.

### ✅ Behaviour

- BaseApi attaches Authorization header  
- Backend validates JWT  
- No mock headers sent  

---

## ✅ **Scenario 2 — Mock User Only (No DB)**  
**Use mock user**  
**Skip JWT**  
**Skip DB**

### ✅ How to enable

UI toggle:

✅ Turn ON “Mock Auth”  
✅ Choose role (admin/moderator/user)

### ✅ Behaviour

- BaseApi sends:

```
X-Mock-Role: admin
```

- Backend returns mock user  
- DB is not used for identity  
- DB is still used for other endpoints  

---

## ✅ **Scenario 3 — Mock User + Real DB Data**  
**Use mock user**  
**Use real DB data**  
**Skip JWT**

This is the recommended dev mode.

### ✅ How to enable

UI toggle ON  
Backend mock mode ON

### ✅ Behaviour

- BaseApi sends `X-Mock-Role`  
- Backend returns mock user  
- DB queries use mock user’s org_id  
- Permissions, roles, orgs load from DB  

---

## ✅ **Scenario 4 — Auto‑Enable Mock Mode (No UI)**  
**Mock mode ON by default**

### ✅ How to enable

`.env.development`:

```env
PUBLIC_GLOBAL_MOCK=true
PUBLIC_GLOBAL_MOCK_OVERRIDE=true
```

### ✅ Behaviour

- BaseApi starts in mock mode  
- UI toggle can still override  

---

# ✅ **Frontend Whitelist**

Frontend loads:

```
shared/whitelist.json
```

BaseApi uses it to skip JWT:

```ts
if (isPublicEndpoint(endpoint)) {
  // skip Authorization header
}
```

✅ Prevents 401 on login/register  
✅ Matches backend behaviour exactly  

---

# ✅ **3. Summary Table**

### ✅ Backend

| Scenario | Mock User | DB Data | JWT Required | How |
|---------|-----------|---------|--------------|-----|
| A | ✅ | ❌ | ❌ | `USE_TEST_USER=true` |
| B | ✅ | ✅ | ❌ | `USE_TEST_USER=true` + valid org_id |
| C | ✅ | ✅ | ❌ | Default mock mode |

---

### ✅ Frontend

| Scenario | Mock User | DB Data | JWT | How |
|---------|-----------|---------|-----|-----|
| 1 | ❌ | ✅ | ✅ | Toggle OFF |
| 2 | ✅ | ❌ | ❌ | Toggle ON |
| 3 | ✅ | ✅ | ❌ | Toggle ON + backend mock |
| 4 | ✅ | ✅ | ❌ | `PUBLIC_GLOBAL_MOCK=true` |

---

# ✅ **4. Developer Workflow (Recommended)**

### ✅ For UI development  
Use:

- Mock user  
- Real DB data  
- Skip JWT  

✅ Fast  
✅ Realistic  
✅ No login required  

### ✅ For integration testing  
Turn mock OFF  
Use real JWT  
Use real DB  

---


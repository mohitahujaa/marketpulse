# 🧪 Testing Guide - MarketPulse API

This guide explains how to test all endpoints including admin-only routes.

---

## 🚀 Quick Start

### 1. Start the Application

```bash
docker-compose up --build -d
```

### 2. Create Admin User

```bash
# Method 1: Using Python script
docker-compose exec api python scripts/create_admin.py

# Method 2: Manual registration then promote via database
# Register normally, then in PostgreSQL:
# UPDATE users SET role = 'admin' WHERE email = 'your@email.com';
```

**Default Admin Credentials:**
- Email: `admin@marketpulse.com`
- Password: `Admin@1234`
- Role: `ADMIN`

⚠️ **Change this password in production!**

---

## 📋 Testing Methods

### **Method 1: Swagger UI (Recommended for Quick Testing)**

1. Navigate to: http://localhost:8000/docs

2. **Login as Admin**:
   - Expand `POST /api/v1/auth/login`
   - Click "Try it out"
   - Enter:
     ```json
     {
       "email": "admin@marketpulse.com",
       "password": "Admin@1234"
     }
     ```
   - Click "Execute"
   - Copy the `access_token` from the response

3. **Authorize Swagger**:
   - Click the green "Authorize" button (top right)
   - Enter: `Bearer YOUR_ACCESS_TOKEN_HERE`
   - Click "Authorize" then "Close"

4. **Test Admin Endpoints**:
   - All endpoints under "Admin" tag are now accessible
   - Try:
     - `GET /api/v1/admin/users` - List all users
     - `PATCH /api/v1/admin/users/{user_id}/deactivate`
     - `PATCH /api/v1/admin/users/{user_id}/activate`

---

### **Method 2: cURL (Command Line)**

#### Step 1: Login and Get Token

```bash
# Login as admin
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@marketpulse.com",
    "password": "Admin@1234"
  }'

# Save the access_token from response
export TOKEN="your_access_token_here"
```

#### Step 2: Test Admin Endpoints

```bash
# List all users (Admin only)
curl http://localhost:8000/api/v1/admin/users \
  -H "Authorization: Bearer $TOKEN"

# List users with pagination
curl "http://localhost:8000/api/v1/admin/users?skip=0&limit=10" \
  -H "Authorization: Bearer $TOKEN"

# Deactivate a user
curl -X PATCH http://localhost:8000/api/v1/admin/users/{user_id}/deactivate \
  -H "Authorization: Bearer $TOKEN"

# Activate a user
curl -X PATCH http://localhost:8000/api/v1/admin/users/{user_id}/activate \
  -H "Authorization: Bearer $TOKEN"
```

---

### **Method 3: Postman**

1. **Import Collection**:
   - Create a new collection "MarketPulse API"
   - Set base URL variable: `{{base_url}}` = `http://localhost:8000`

2. **Setup Authentication**:
   - Collection → Authorization → Type: Bearer Token
   - Token: `{{access_token}}`

3. **Create Login Request**:
   ```
   POST {{base_url}}/api/v1/auth/login
   Body (JSON):
   {
     "email": "admin@marketpulse.com",
     "password": "Admin@1234"
   }
   
   Tests (to save token):
   pm.collectionVariables.set("access_token", pm.response.json().data.access_token);
   ```

4. **Create Admin Requests**:
   - GET `{{base_url}}/api/v1/admin/users`
   - PATCH `{{base_url}}/api/v1/admin/users/{{user_id}}/deactivate`

---

## 🔐 Testing Regular User vs Admin Access

### Create Regular User

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "testuser",
    "password": "User@1234"
  }'
```

### Test Access Control

```bash
# Login as regular user
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "User@1234"
  }'

# Try to access admin endpoint (should fail with 403 Forbidden)
curl http://localhost:8000/api/v1/admin/users \
  -H "Authorization: Bearer $USER_TOKEN"
```

Expected response:
```json
{
  "success": false,
  "message": "Forbidden: insufficient permissions",
  "status_code": 403
}
```

---

## 📊 Admin Endpoint Reference

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| GET | `/api/v1/admin/users` | List all users with pagination | Admin |
| PATCH | `/api/v1/admin/users/{id}/deactivate` | Deactivate user account | Admin |
| PATCH | `/api/v1/admin/users/{id}/activate` | Activate user account | Admin |

### Pagination Parameters

All list endpoints support pagination:
- `skip`: Number of records to skip (default: 0)
- `limit`: Max records to return (default: 50, max: 100)

Example:
```
GET /api/v1/admin/users?skip=0&limit=25
```

---

## 🧪 Complete Test Scenarios

### Scenario 1: User Management Workflow

```bash
# 1. Admin logs in
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@marketpulse.com","password":"Admin@1234"}' \
  | jq -r '.data.access_token')

# 2. List all users
curl -s http://localhost:8000/api/v1/admin/users \
  -H "Authorization: Bearer $TOKEN" | jq

# 3. Get user ID and deactivate
USER_ID="paste-user-id-here"
curl -X PATCH http://localhost:8000/api/v1/admin/users/$USER_ID/deactivate \
  -H "Authorization: Bearer $TOKEN"

# 4. Verify user cannot login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"User@1234"}'
# Should return "Account is deactivated"

# 5. Reactivate user
curl -X PATCH http://localhost:8000/api/v1/admin/users/$USER_ID/activate \
  -H "Authorization: Bearer $TOKEN"
```

### Scenario 2: Pagination Testing

```bash
# Create multiple test users first (loop)
for i in {1..15}; do
  curl -X POST http://localhost:8000/api/v1/auth/register \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"user$i@test.com\",\"username\":\"user$i\",\"password\":\"Test@1234\"}"
done

# Test pagination
curl "http://localhost:8000/api/v1/admin/users?skip=0&limit=5" \
  -H "Authorization: Bearer $TOKEN" | jq '.data.pagination'
```

---

## 🔍 Troubleshooting

### "401 Unauthorized"
- Token expired (15 min lifetime)
- Solution: Login again to get new token

### "403 Forbidden"
- User doesn't have admin role
- Solution: Verify user role in database or use admin account

### "Token is missing subject claim"
- Invalid token format
- Solution: Ensure token is prefixed with `Bearer `

### Admin user doesn't exist
```bash
docker-compose exec api python scripts/create_admin.py
```

---

## 📝 Notes for Reviewers/Testers

1. **Admin Access**: Use the provided script to create admin account
2. **Swagger UI**: Best for interactive testing (http://localhost:8000/docs)
3. **Security**: Admin endpoints properly protected with `require_admin` dependency
4. **Pagination**: All list endpoints support skip/limit parameters
5. **Error Handling**: Try invalid user IDs to test 404 responses

---

## 🚀 Next Steps (Phase 2)

Ready to discuss Phase 2 requirements! Possible enhancements:
- Email notifications
- Advanced analytics
- Bulk operations
- Export functionality
- Audit logging
- Two-factor authentication

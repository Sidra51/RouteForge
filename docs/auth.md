# LLM Gateway - User Authentication & Identity Management

This document explains the user authentication and session management layer implemented in the platform.

---

## 1. Concepts & Identity Flow
* **Multi-Tenancy**: The gateway supports multiple developers/users. Each user owns a private database space for their API keys and usage logs.
* **Security Layer**: Authentication is powered by JSON Web Tokens (JWT) using `python-jose` and cryptographic hashing via `bcrypt`.

---

## 2. API Endpoints

### Registration (`POST /api/auth/register`)
Allows new developers to sign up.
* **Payload**:
  ```json
  {
    "email": "developer@company.com",
    "password": "secure_password"
  }
  ```
* **Status**: `201 Created`

### Login (`POST /api/auth/login`)
Validates password hashes and issues access and refresh tokens.
* **Payload**:
  ```json
  {
    "email": "developer@company.com",
    "password": "secure_password"
  }
  ```
* **Response**:
  ```json
  {
    "access_token": "JWT_TOKEN",
    "refresh_token": "REFRESH_TOKEN",
    "token_type": "bearer"
  }
  ```

### Silent Refresh (`POST /api/auth/refresh`)
Uses the refresh token stored in local storage to fetch a new access token without logging the user out. Access tokens are valid for 15 minutes, while refresh tokens are valid for 7 days.

---

## 3. Database Schema

The authentication system is supported by the `User` and `RefreshToken` SQLAlchemy models:

* **`users` Table**:
  * `id`: UUID (Primary Key)
  * `email`: String(255), unique, indexed
  * `hashed_password`: String(255)
  * `is_active`: Boolean
  
* **`refresh_tokens` Table**:
  * `id`: UUID (Primary Key)
  * `token`: String(255), unique, indexed
  * `user_id`: ForeignKey("users.id")
  * `expires_at`: DateTime
  * `revoked`: Boolean

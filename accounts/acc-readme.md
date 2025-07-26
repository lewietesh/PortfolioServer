# User Management

 - Role-based permissions (client, developer, admin)
 - Profile management via /users/me/ endpoint
 - Client profile automatic creation and management
 - Password change for authenticated users

# Security Features:

## Email Verification

 - Inactive accounts until email verified
 - Automatic profile creation for clients upon verification
 - Resend verification capability with rate limiting via cache

## Password Security

 - Django password validation enforced
 - Current password verification for changes
 - Secure reset process with temporary codes
 - No password exposure in API responses

## Permission System

 - IsDeveloperOrAdmin: Staff-only access
 - IsOwnerOrReadOnly: Users manage own data
 - IsClientOwner: Client-specific profile access

## 📧 Email Integration:
 - The system uses Django's email backend. 
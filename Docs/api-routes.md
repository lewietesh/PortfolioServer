# Complete API Structure:
"""
PORTFOLIO API v1 - Complete Endpoint Structure

═══════════════════════════════════════════════════════════════════════════════
🔐 AUTHENTICATION & USER MANAGEMENT (/api/v1/accounts/)
═══════════════════════════════════════════════════════════════════════════════

Authentication:
POST   /api/v1/accounts/auth/register/              # Client registration
POST   /api/v1/accounts/auth/verify-email/          # Email verification
POST   /api/v1/accounts/auth/resend-verification/   # Resend verification code
POST   /api/v1/accounts/auth/login/                 # User login
POST   /api/v1/accounts/auth/logout/                # User logout
POST   /api/v1/accounts/auth/refresh/               # Refresh JWT token
POST   /api/v1/accounts/auth/forgot-password/       # Password reset request
POST   /api/v1/accounts/auth/reset-password/        # Password reset confirmation

User Management:
GET    /api/v1/accounts/users/                      # List users (admin)
POST   /api/v1/accounts/users/                      # Create user (admin)
GET    /api/v1/accounts/users/{id}/                 # User details (admin)
PUT    /api/v1/accounts/users/{id}/                 # Update user (admin)
DELETE /api/v1/accounts/users/{id}/                 # Delete user (admin)
GET    /api/v1/accounts/users/me/                   # Current user profile
PATCH  /api/v1/accounts/users/me/                   # Update own profile
POST   /api/v1/accounts/users/change-password/      # Change password

Client Profiles:
GET    /api/v1/accounts/clients/                    # List clients
GET    /api/v1/accounts/clients/{id}/               # Client details
PATCH  /api/v1/accounts/clients/{id}/               # Update client profile
GET    /api/v1/accounts/clients/{id}/projects/      # Client's projects
GET    /api/v1/accounts/clients/{id}/orders/        # Client's orders

═══════════════════════════════════════════════════════════════════════════════
🎨 SITE CONTENT MANAGEMENT (/api/v1/core/)
═══════════════════════════════════════════════════════════════════════════════

GET    /api/v1/core/hero/                           # Hero section content
PUT    /api/v1/core/hero/{id}/                      # Update hero section
GET    /api/v1/core/about/                          # About section content
PUT    /api/v1/core/about/{id}/                     # Update about section

═══════════════════════════════════════════════════════════════════════════════
💼 PROJECTS & PORTFOLIO (/api/v1/projects/)
═══════════════════════════════════════════════════════════════════════════════

Projects:
GET    /api/v1/projects/projects/                   # List projects
POST   /api/v1/projects/projects/                   # Create project
GET    /api/v1/projects/projects/{id}/              # Project details
PUT    /api/v1/projects/projects/{id}/              # Update project
DELETE /api/v1/projects/projects/{id}/              # Delete project
GET    /api/v1/projects/projects/featured/          # Featured projects
POST   /api/v1/projects/projects/{id}/like/         # Like project
GET    /api/v1/projects/projects/{id}/comments/     # Project comments

Technologies:
GET    /api/v1/projects/technologies/               # List technologies
GET    /api/v1/projects/technologies/{id}/          # Technology details
GET    /api/v1/projects/technologies/categories/    # Technologies by category

Comments:
GET    /api/v1/projects/comments/                   # List comments (admin)
POST   /api/v1/projects/comments/                   # Add comment
PUT    /api/v1/projects/comments/{id}/              # Update comment
DELETE /api/v1/projects/comments/{id}/              # Delete comment

═══════════════════════════════════════════════════════════════════════════════
📝 BLOG & CONTENT (/api/v1/blog/)
═══════════════════════════════════════════════════════════════════════════════

Blog Posts:
GET    /api/v1/blog/posts/                          # List blog posts
POST   /api/v1/blog/posts/                          # Create post
GET    /api/v1/blog/posts/{id}/                     # Post details
PUT    /api/v1/blog/posts/{id}/                     # Update post
DELETE /api/v1/blog/posts/{id}/                     # Delete post
GET    /api/v1/blog/posts/published/                # Published posts only
GET    /api/v1/blog/posts/featured/                 # Featured posts
GET    /api/v1/blog/posts/{id}/comments/            # Post comments

Tags:
GET    /api/v1/blog/tags/                           # List tags
POST   /api/v1/blog/tags/                           # Create tag
GET    /api/v1/blog/tags/{id}/                      # Tag details
GET    /api/v1/blog/tags/popular/                   # Most used tags

Comments:
GET    /api/v1/blog/comments/                       # List comments (admin)
POST   /api/v1/blog/comments/                       # Add comment
PUT    /api/v1/blog/comments/{id}/                  # Update comment

═══════════════════════════════════════════════════════════════════════════════
🛍️ SERVICES & PRICING (/api/v1/services/)
═══════════════════════════════════════════════════════════════════════════════

Services:
GET    /api/v1/services/services/                   # List services
POST   /api/v1/services/services/                   # Create service
GET    /api/v1/services/services/{id}/              # Service details
PUT    /api/v1/services/services/{id}/              # Update service
DELETE /api/v1/services/services/{id}/              # Delete service
GET    /api/v1/services/services/active/            # Active services only
GET    /api/v1/services/services/{id}/tiers/        # Service pricing tiers
GET    /api/v1/services/services/{id}/faqs/         # Service FAQs

Pricing Tiers:
GET    /api/v1/services/tiers/                      # List pricing tiers
POST   /api/v1/services/tiers/                      # Create tier
GET    /api/v1/services/tiers/{id}/                 # Tier details
PUT    /api/v1/services/tiers/{id}/                 # Update tier

Features:
GET    /api/v1/services/features/                   # List features
POST   /api/v1/services/features/                   # Create feature
GET    /api/v1/services/features/by-category/       # Features by category

═══════════════════════════════════════════════════════════════════════════════
📦 DIGITAL PRODUCTS (/api/v1/products/)
═══════════════════════════════════════════════════════════════════════════════

Products:
GET    /api/v1/products/products/                   # List products
POST   /api/v1/products/products/                   # Create product
GET    /api/v1/products/products/{id}/              # Product details
PUT    /api/v1/products/products/{id}/              # Update product
DELETE /api/v1/products/products/{id}/              # Delete product
GET    /api/v1/products/products/featured/          # Featured products
POST   /api/v1/products/products/{id}/purchase/     # Purchase product
GET    /api/v1/products/products/{id}/reviews/      # Product reviews
GET    /api/v1/products/products/{id}/updates/      # Product updates

Purchases:
GET    /api/v1/products/purchases/                  # List purchases (admin)
GET    /api/v1/products/purchases/my-purchases/     # User's purchases
GET    /api/v1/products/purchases/{id}/             # Purchase details

Reviews:
GET    /api/v1/products/reviews/                    # List reviews
POST   /api/v1/products/reviews/                    # Add review
GET    /api/v1/products/reviews/{id}/               # Review details

═══════════════════════════════════════════════════════════════════════════════
📋 BUSINESS OPERATIONS (/api/v1/business/)
═══════════════════════════════════════════════════════════════════════════════

Orders:
GET    /api/v1/business/orders/                     # List orders (admin)
POST   /api/v1/business/orders/                     # Create order
GET    /api/v1/business/orders/{id}/                # Order details
PUT    /api/v1/business/orders/{id}/                # Update order
GET    /api/v1/business/orders/my-orders/           # Client's orders

Testimonials:
GET    /api/v1/business/testimonials/               # List testimonials
POST   /api/v1/business/testimonials/               # Add testimonial
GET    /api/v1/business/testimonials/{id}/          # Testimonial details
GET    /api/v1/business/testimonials/approved/      # Approved testimonials

Contact:
GET    /api/v1/business/contact/                    # List messages (admin)
POST   /api/v1/business/contact/submit/             # Submit contact form
GET    /api/v1/business/contact/{id}/               # Message details

Notifications:
GET    /api/v1/business/notifications/              # List notifications
GET    /api/v1/business/notifications/unread/       # Unread notifications
PUT    /api/v1/business/notifications/{id}/         # Mark as read

═══════════════════════════════════════════════════════════════════════════════
"""
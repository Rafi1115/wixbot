# Wixbot — Postman Testing Flow

## SETUP FIRST

Create a Postman **Environment** called `Wixbot Local` with these variables:

| Variable | Initial Value | Notes |
|---|---|---|
| `base_url` | `http://localhost:8000` | |
| `access` | *(empty)* | Set after login |
| `refresh` | *(empty)* | Set after login |
| `bot_id` | *(empty)* | Set after create bot |
| `source_id` | *(empty)* | Set after add website |
| `conv_id` | *(empty)* | Set after first chat |
| `lead_id` | *(empty)* | Set after lead appears |
| `behavior_id` | *(empty)* | Set after add behavior |

**Every authenticated request needs this header:**
```
Authorization: Bearer {{access}}
Content-Type: application/json
```

**Pro tip:** In your Login request → Tests tab, paste this to auto-set the token:
```javascript
const res = pm.response.json();
pm.environment.set("access", res.data.access);
pm.environment.set("refresh", res.data.refresh);
```

---

## 📁 FOLDER 1 — Auth

### 1.1 Register
```
POST {{base_url}}/api/auth/register/
```
```json
{
  "email": "johal@test.com",
  "password": "StrongPass123!",
  "password2": "StrongPass123!",
  "company_name": "Johal Store"
}
```
> ✅ Expected: 201 — `"Registration successful. Please check your email for verification code."`

---

### 1.2 Verify Email (OTP)
```
POST {{base_url}}/api/auth/verify-email/
```
```json
{
  "email": "johal@test.com",
  "otp": "1234"
}
```
> ✅ Expected: 200 with `access` + `refresh` tokens — copy them into your environment

---

### 1.3 Login
```
POST {{base_url}}/api/auth/login/
```
```json
{
  "email": "johal@test.com",
  "password": "StrongPass123!"
}
```
> ✅ Expected: 200 with tokens → set `{{access}}` and `{{refresh}}`

---

### 1.4 Social Login / Registration
```
POST {{base_url}}/api/auth/social-auth/
```
```json
{
  "email": "socialuser@test.com",
  "provider": "google",
  "name": "Social User"
}
```
> ✅ Expected: 200 with tokens -> set `{{access}}` and `{{refresh}}`

---

### 1.5 Refresh Token
```
POST {{base_url}}/api/auth/token/refresh/
```
```json
{
  "refresh": "{{refresh}}"
}
```
> ✅ Expected: 200 with new `access` token

---

### 1.6 Get My Profile (Me)
```
GET {{base_url}}/api/auth/me/
Authorization: Bearer {{access}}
```
> ✅ Expected: user object with `email`, `role`, `tenant` info (plan, limits, slug)

---

### 1.7 Update My Name
```
PATCH {{base_url}}/api/auth/me/
Authorization: Bearer {{access}}
```
```json
{
  "full_name": "Johal Al-Rashid"
}
```

---

### 1.8 Get User Profile
```
GET {{base_url}}/api/auth/profile/
Authorization: Bearer {{access}}
```
> ✅ Expected: 200 with profile object (name, phone, bio, profile_picture, etc.)

---

### 1.9 Update User Profile (Full)
```
PUT {{base_url}}/api/auth/profile/
Authorization: Bearer {{access}}
```
```json
{
  "name": "Johal Store",
  "phone": "+447700123456",
  "bio": "Expert electronics retailer since 2010"
}
```
> ✅ Expected: 200 with updated profile object

---

### 1.10 Update Profile Details (Email/Bio)
```
PATCH {{base_url}}/api/auth/profile/update/
Authorization: Bearer {{access}}
```
```json
{
  "name": "Johal Store Updated",
  "email": "newemail@johal.com",
  "phone": "+447700987654",
  "bio": "New bio description",
  "date_of_birth": "1995-01-01",
  "gender": "male"
}
```
> ✅ Expected: 200 with profile updated response. If email was changed, returns `"email_verification_pending": true` and sends OTP to the new email.

---

### 1.11 Verify Profile Email Change
```
POST {{base_url}}/api/auth/profile/verify-email-change/
Authorization: Bearer {{access}}
```
```json
{
  "otp": "1234"
}
```
> ✅ Expected: 200 — `{ "detail": "Email successfully updated." }`

---

### 1.12 Get Tenant Info
```
GET {{base_url}}/api/auth/tenant/
Authorization: Bearer {{access}}
```
> ✅ Expected: `{ "name": "Johal Store", "plan": "free", "slug": "johal-store", "plan_limits": { "bots": 1, "messages": 100 } }`

---

### 1.13 Update Tenant Name
```
PATCH {{base_url}}/api/auth/tenant/
Authorization: Bearer {{access}}
```
```json
{
  "name": "Johal Electronics"
}
```

---

### 1.14 Invite an Agent
```
POST {{base_url}}/api/auth/agents/
Authorization: Bearer {{access}}
```
```json
{
  "email": "agent@johal.com",
  "full_name": "Support Agent",
  "password": "AgentPass123!"
}
```
> ✅ Expected: agent user object with `role: agent`

---

### 1.15 List Agents
```
GET {{base_url}}/api/auth/agents/
Authorization: Bearer {{access}}
```

---

### 1.16 Change Password
```
POST {{base_url}}/api/auth/password/change/
Authorization: Bearer {{access}}
```
```json
{
  "old_password": "StrongPass123!",
  "new_password": "NewPass456!",
  "new_password2": "NewPass456!"
}
```

---

### 1.17 Logout
```
POST {{base_url}}/api/auth/logout/
Authorization: Bearer {{access}}
```
```json
{
  "refresh": "{{refresh}}"
}
```

---

### 1.18 Resend OTP
```
POST {{base_url}}/api/auth/resend-otp/
```
```json
{
  "email": "johal@test.com",
  "purpose": "verification"
}
```
> Purpose options: `verification` or `password_reset`
> ✅ Expected: 200 — `{ "message": "OTP has been sent to your email" }`

---

### 1.19 Reset Password Request
```
POST {{base_url}}/api/auth/password/reset-request/
```
```json
{
  "email": "johal@test.com"
}
```
> ✅ Expected: 200 — `{ "message": "If the email exists, a password reset OTP has been sent" }`

---

### 1.20 Reset Password Verify OTP
```
POST {{base_url}}/api/auth/password/reset-verify-otp/
```
```json
{
  "email": "johal@test.com",
  "otp": "1234"
}
```
> ✅ Expected: 200 — `{ "email": "johal@test.com", "message": "OTP verified successfully" }`

---

### 1.21 Reset Password Confirm
```
POST {{base_url}}/api/auth/password/reset-confirm/
```
```json
{
  "email": "johal@test.com",
  "otp": "1234",
  "new_password": "NewPass456!",
  "new_password2": "NewPass456!"
}
```
> ✅ Expected: 200 — `{ "message": "Password has been reset successfully" }`

---

### 1.22 Soft Delete Account
```
POST {{base_url}}/api/auth/account/delete/
Authorization: Bearer {{access}}
```
```json
{
  "confirm": true
}
```
> ✅ Expected: 200 — `{ "message": "Account has been deactivated successfully" }`

---

### 1.23 Restore Account (Admin Only)
```
POST {{base_url}}/api/auth/account/restore/
Authorization: Bearer {{access}}
```
```json
{
  "email": "johal@test.com"
}
```
> ✅ Expected: 200 — `{ "data": { "email": "johal@test.com" }, "message": "Account restored successfully" }`

---

## 📁 FOLDER 2 — Bots

### 2.1 Create Bot
```
POST {{base_url}}/api/bots/
Authorization: Bearer {{access}}
Content-Type: multipart/form-data
```
```
Body → form-data:
  Key: name               Type: Text     Value: Johal AI Assistant (required)
  Key: business_context   Type: Text     Value: We sell electronics in London. Free shipping over £50. Return policy: 30 days. (optional)
  Key: widget_enabled     Type: Text     Value: true (optional)
  Key: website_url        Type: Text     Value: https://en.wikipedia.org/wiki/Artificial_intelligence (optional)
  Key: files              Type: File     Value: (pick any .pdf, .docx, .txt, or .xlsx) (optional, supports multiple files)
```
> ✅ Expected: bot object with `id` — **copy id → set `{{bot_id}}`**

---

### 2.2 List My Bots
```
GET {{base_url}}/api/bots/
Authorization: Bearer {{access}}
```

---

### 2.3 Get Single Bot
```
GET {{base_url}}/api/bots/{{bot_id}}/
Authorization: Bearer {{access}}
```

---

### 2.4 Update Bot
```
PATCH {{base_url}}/api/bots/{{bot_id}}/
Authorization: Bearer {{access}}
Content-Type: multipart/form-data
```
```
Body → form-data:
  Key: name               Type: Text     Value: Johal Store Bot (optional)
  Key: business_context   Type: Text     Value: We are Johal Electronics, London's top electronics retailer since 2010. (optional)
  Key: widget_enabled     Type: Text     Value: true (optional)
  Key: website_url        Type: Text     Value: https://en.wikipedia.org/wiki/Artificial_intelligence (optional, will add source)
  Key: files              Type: File     Value: (pick any .pdf, .docx, .txt, or .xlsx) (optional, supports multiple files, will add sources)
```

---

### 2.5 Get Widget Design
```
GET {{base_url}}/api/bots/{{bot_id}}/design/
Authorization: Bearer {{access}}
```

---

### 2.6 Update Widget Design
```
PATCH {{base_url}}/api/bots/{{bot_id}}/design/
Authorization: Bearer {{access}}
```
```json
{
  "header_text": "Chat with Johal",
  "welcome_message": "Hi! 👋 How can I help you today?",
  "theme_color": "#7C3AED",
  "font_family": "Inter",
  "widget_position": "right",
  "widget_size": "medium",
  "border_radius": 16,
  "predefined_questions": [
    "What products do you sell?",
    "Do you ship internationally?",
    "What is your return policy?"
  ],
  "enable_pulsing": true,
  "remove_branding": false
}
```

---

### 2.7 Add Behavior #1
```
POST {{base_url}}/api/bots/{{bot_id}}/behaviors/
Authorization: Bearer {{access}}
```
```json
{
  "instruction": "Always greet the customer warmly and end with: Is there anything else I can help you with?",
  "order": 1
}
```
> ✅ Expected: behavior object with `id` — **copy id → set `{{behavior_id}}`**

---

### 2.8 Add Behavior #2
```
POST {{base_url}}/api/bots/{{bot_id}}/behaviors/
Authorization: Bearer {{access}}
```
```json
{
  "instruction": "Never mention competitor stores or products. If asked, redirect to our catalogue.",
  "order": 2
}
```

---

### 2.9 List Behaviors
```
GET {{base_url}}/api/bots/{{bot_id}}/behaviors/
Authorization: Bearer {{access}}
```

---

### 2.10 Update Behavior
```
PATCH {{base_url}}/api/bots/{{bot_id}}/behaviors/{{behavior_id}}/
Authorization: Bearer {{access}}
```
```json
{
  "instruction": "Always be friendly, professional, and helpful. End with a question."
}
```

---

### 2.11 Delete Behavior
```
DELETE {{base_url}}/api/bots/{{bot_id}}/behaviors/{{behavior_id}}/
Authorization: Bearer {{access}}
```
> ✅ Expected: 204 No Content

---

### 2.12 Public Bot Config (NO AUTH — widget uses this)
```
GET {{base_url}}/api/bots/public/{{bot_id}}/config/
```
> ✅ Expected: design settings for the widget — no token needed

---

## 📁 FOLDER 3 — Knowledge Base

### 📂 Websites

### 3.1 Add Website URL
```
POST {{base_url}}/api/knowledge/{{bot_id}}/websites/
Authorization: Bearer {{access}}
```
```json
{
  "url": "https://en.wikipedia.org/wiki/Artificial_intelligence",
  "auto_rescrape": false
}
```
> ✅ Expected: source with `status: "pending"` — Celery processes it in background
> **Copy source id → set `{{source_id}}`**
> Wait 10–15 seconds then check status

---

### 3.2 List Websites
```
GET {{base_url}}/api/knowledge/{{bot_id}}/websites/
Authorization: Bearer {{access}}
```
> Check `status` field — should change from `pending` → `processing` → `ready`

---

### 3.3 Get Single Website Source
```
GET {{base_url}}/api/knowledge/{{bot_id}}/websites/{{source_id}}/
Authorization: Bearer {{access}}
```
> ✅ Expected: `chunks_count` > 0 when ready, `raw_text_preview` shows scraped content

---

### 3.4 Rescrape Website
```
POST {{base_url}}/api/knowledge/{{bot_id}}/websites/{{source_id}}/rescrape/
Authorization: Bearer {{access}}
```
> ✅ Expected: `{ "detail": "Rescrape started." }`

---

### 3.5 Toggle Auto-Rescrape
```
PATCH {{base_url}}/api/knowledge/{{bot_id}}/websites/{{source_id}}/
Authorization: Bearer {{access}}
```
```json
{
  "auto_rescrape": true
}
```

---

### 3.6 Delete Website Source
```
DELETE {{base_url}}/api/knowledge/{{bot_id}}/websites/{{source_id}}/
Authorization: Bearer {{access}}
```

---

### 📂 File Uploads

### 3.7 Upload a File
```
POST {{base_url}}/api/knowledge/{{bot_id}}/files/
Authorization: Bearer {{access}}
Content-Type: multipart/form-data
```
```
Body → form-data:
  Key: file     Type: File     Value: (pick any .pdf, .docx, .txt, or .xlsx)
```
> ✅ Expected: source object with `status: "pending"` — Celery reads and embeds it

---

### 3.8 List Files
```
GET {{base_url}}/api/knowledge/{{bot_id}}/files/
Authorization: Bearer {{access}}
```

---

### 3.9 Delete File
```
DELETE {{base_url}}/api/knowledge/{{bot_id}}/files/<file_id>/
Authorization: Bearer {{access}}
```

---

### 📂 Q&A Pairs

### 3.10 Add Q&A #1
```
POST {{base_url}}/api/knowledge/{{bot_id}}/qa/
Authorization: Bearer {{access}}
```
```json
{
  "question": "What is your return policy?",
  "answer": "We accept returns within 30 days. Items must be unused and in original packaging. Contact support@johal.com to start a return."
}
```

---

### 3.11 Add Q&A #2
```
POST {{base_url}}/api/knowledge/{{bot_id}}/qa/
Authorization: Bearer {{access}}
```
```json
{
  "question": "Do you ship internationally?",
  "answer": "Yes! We ship to over 50 countries. UK orders arrive in 2-3 days. International orders take 5-7 business days."
}
```

---

### 3.12 List Q&A Pairs
```
GET {{base_url}}/api/knowledge/{{bot_id}}/qa/
Authorization: Bearer {{access}}
```

---

### 3.13 Update a Q&A
```
PATCH {{base_url}}/api/knowledge/{{bot_id}}/qa/<qa_id>/
Authorization: Bearer {{access}}
```
```json
{
  "answer": "Updated: We accept returns within 45 days now."
}
```

---

### 3.14 Delete a Q&A
```
DELETE {{base_url}}/api/knowledge/{{bot_id}}/qa/<qa_id>/
Authorization: Bearer {{access}}
```

---

### 📂 External Sources (Google Drive & OneDrive)

### 3.15 Google Drive - Check Status
```
GET {{base_url}}/api/knowledge/{{bot_id}}/gdrive/
Authorization: Bearer {{access}}
```
> ✅ Expected: 200 — `{ "connected": false }` or `{ "connected": true, ...config }`

---

### 3.16 Google Drive - Disconnect
```
DELETE {{base_url}}/api/knowledge/{{bot_id}}/gdrive/
Authorization: Bearer {{access}}
```
> ✅ Expected: 200 — `{ "detail": "Google Drive disconnected." }`

---

### 3.17 OneDrive - Check Status
```
GET {{base_url}}/api/knowledge/{{bot_id}}/onedrive/
Authorization: Bearer {{access}}
```
> ✅ Expected: 200 — `{ "connected": false }` or `{ "connected": true, ...config }`

---

### 3.18 OneDrive - Disconnect
```
DELETE {{base_url}}/api/knowledge/{{bot_id}}/onedrive/
Authorization: Bearer {{access}}
```
> ✅ Expected: 200 — `{ "detail": "OneDrive disconnected." }`

---

### 3.19 Import External File
```
POST {{base_url}}/api/knowledge/{{bot_id}}/import-external/
Authorization: Bearer {{access}}
```
```json
{
  "source_type": "google_drive",
  "file_id": "file_12345",
  "file_name": "Product_Catalog.pdf"
}
```
> ✅ Expected: 201 — knowledge source object with `status: "pending"`, celery processes sync in background.

---

## 📁 FOLDER 4 — Chat (NO AUTH — simulates the widget)

> ⚠️ Remove the Authorization header for all chat requests

### 4.1 First Message
```
POST {{base_url}}/api/chat/
```
```json
{
  "bot_id": "{{bot_id}}",
  "session_id": "test_session_001",
  "message": "Hello! What products do you sell?"
}
```
> ✅ Expected: `{ "reply": "...", "session_id": "test_session_001", "handoff": false }`

---

### 4.2 Ask About Knowledge Base
```
POST {{base_url}}/api/chat/
```
```json
{
  "bot_id": "{{bot_id}}",
  "session_id": "test_session_001",
  "message": "What is your return policy?"
}
```
> ✅ Expected: answer pulled from your Q&A / website — this is the RAG in action

---

### 4.3 Trigger Lead Capture
```
POST {{base_url}}/api/chat/
```
```json
{
  "bot_id": "{{bot_id}}",
  "session_id": "test_session_001",
  "message": "I would like a quote for a bulk order. Can I leave my contact details?"
}
```
> ✅ Expected: bot asks for name, email, phone

---

### 4.4 Provide Lead Details
```
POST {{base_url}}/api/chat/
```
```json
{
  "bot_id": "{{bot_id}}",
  "session_id": "test_session_001",
  "message": "My name is Ahmed, email ahmed@test.com, phone +447700123456"
}
```
> ✅ Expected: bot confirms and saves lead → check Folder 6 to see it appear

---

### 4.5 New Session (Different Customer)
```
POST {{base_url}}/api/chat/
```
```json
{
  "bot_id": "{{bot_id}}",
  "session_id": "test_session_002",
  "message": "Hi, do you have any iPhone 15 cases?"
}
```

---

## 📁 FOLDER 5 — Conversations (Dashboard)

### 5.1 WebSocket — Live updates socket
```text
ws://localhost:8000/ws/conversations/{{bot_id}}/
```
**Headers (for connection handshake):**
* `Authorization`: `Bearer {{access}}`
*(Note: Send a ping event from Postman `{"type": "ping"}` to test keep-alive, you will receive `{"type": "pong"}`).*

> ✅ Expected real-time pushed event types:
> * `connected` — upon successful handshake.
> * `new_conversation` — when a new chat starts.
> * `new_message` — when a customer sends a message or when the AI replies.
> * `conversation_updated` — when an agent takes over/releases or is assigned.

---

### 5.2 List All Conversations
```
GET {{base_url}}/api/conversations/
Authorization: Bearer {{access}}
```
> ✅ Expected: list of all conversations — **copy a `conv_id` → set `{{conv_id}}`**

---

### 5.3 Filter by Bot
```
GET {{base_url}}/api/conversations/?bot={{bot_id}}
Authorization: Bearer {{access}}
```

---

### 5.4 Filter by Channel
```
GET {{base_url}}/api/conversations/?channel=website
Authorization: Bearer {{access}}
```

---

### 5.5 Filter by Mode
```
GET {{base_url}}/api/conversations/?mode=ai
Authorization: Bearer {{access}}
```

---

### 5.6 Search Conversations
```
GET {{base_url}}/api/conversations/?search=Ahmed
Authorization: Bearer {{access}}
```

---

### 5.7 Get Full Conversation + Messages
```
GET {{base_url}}/api/conversations/{{conv_id}}/
Authorization: Bearer {{access}}
```
> ✅ Expected: conversation with full message history

---

### 5.8 Human Takeover
```
POST {{base_url}}/api/conversations/{{conv_id}}/handoff/
Authorization: Bearer {{access}}
```
```json
{
  "action": "takeover"
}
```
> ✅ Expected: `{ "mode": "human" }` — AI stops responding for this conversation
> Now send another chat from Folder 4 with the same session_id → `"handoff": true`

---

### 5.9 Send Agent Message (Human Mode)
```
POST {{base_url}}/api/conversations/{{conv_id}}/message/
Authorization: Bearer {{access}}
```
```json
{
  "content": "Hi Ahmed! This is the support team. I've seen your bulk order request — let me check stock for you right now."
}
```
> ✅ Expected: message saved and dispatched to the right channel

---

### 5.10 Release Back to AI
```
POST {{base_url}}/api/conversations/{{conv_id}}/handoff/
Authorization: Bearer {{access}}
```
```json
{
  "action": "release"
}
```
> ✅ Expected: `{ "mode": "ai" }` — AI takes back over

---

### 5.11 Delete Conversation
```
DELETE {{base_url}}/api/conversations/{{conv_id}}/
Authorization: Bearer {{access}}
```

---

## 📁 FOLDER 6 — Leads

### 6.1 List All Leads
```
GET {{base_url}}/api/leads/
Authorization: Bearer {{access}}
```
> ✅ Expected: Ahmed's lead should appear here — **copy id → set `{{lead_id}}`**

---

### 6.2 Filter Leads
```
GET {{base_url}}/api/leads/?bot={{bot_id}}
GET {{base_url}}/api/leads/?status=new
GET {{base_url}}/api/leads/?channel=website
GET {{base_url}}/api/leads/?search=Ahmed
```

---

### 6.3 Get Single Lead
```
GET {{base_url}}/api/leads/{{lead_id}}/
Authorization: Bearer {{access}}
```

---

### 6.4 Update Lead Status
```
PATCH {{base_url}}/api/leads/{{lead_id}}/
Authorization: Bearer {{access}}
```
```json
{
  "status": "contacted",
  "notes": "Called Ahmed. Very interested in 50 units. Sending quote tomorrow."
}
```
> Status options: `new` → `contacted` → `converted`

---

### 6.5 Export Leads as CSV
```
GET {{base_url}}/api/leads/export/?bot={{bot_id}}
Authorization: Bearer {{access}}
```
> ✅ Expected: CSV file download with all leads

---

## 📁 FOLDER 7 — Messaging (Meta Channels)

### 📂 Connect Channels

### 7.1 Check Facebook Status
```
GET {{base_url}}/api/messaging/facebook/?bot={{bot_id}}
Authorization: Bearer {{access}}
```
> ✅ Expected: `{ "connected": false }`

---

### 7.2 Connect Facebook Page
```
POST {{base_url}}/api/messaging/facebook/
Authorization: Bearer {{access}}
```
```json
{
  "bot_id": "{{bot_id}}",
  "page_id": "123456789",
  "page_name": "Johal Store",
  "page_access_token": "EAAxxxxxxxx"
}
```

---

### 7.3 Check WhatsApp Status
```
GET {{base_url}}/api/messaging/whatsapp/?bot={{bot_id}}
Authorization: Bearer {{access}}
```

---

### 7.4 Connect WhatsApp
```
POST {{base_url}}/api/messaging/whatsapp/
Authorization: Bearer {{access}}
```
```json
{
  "bot_id": "{{bot_id}}",
  "phone_number_id": "123456789",
  "phone_number": "+447700123456",
  "access_token": "EAAxxxxxxxx"
}
```

---

### 7.5 Connect Instagram
```
POST {{base_url}}/api/messaging/instagram/
Authorization: Bearer {{access}}
```
```json
{
  "bot_id": "{{bot_id}}",
  "instagram_account_id": "987654321",
  "page_id": "123456789",
  "page_access_token": "EAAxxxxxxxx",
  "username": "johalstore"
}
```

---

### 7.6 Disconnect Facebook
```
DELETE {{base_url}}/api/messaging/facebook/?bot={{bot_id}}
Authorization: Bearer {{access}}
```

---

### 📂 Webhook Verification (NO AUTH — Meta calls these)

### 7.7 Verify WhatsApp Webhook
```
GET {{base_url}}/api/messaging/whatsapp/webhook/?hub.verify_token=YOUR_VERIFY_TOKEN&hub.challenge=99999&hub.mode=subscribe
```
> ✅ Expected: plain text response `99999` (the challenge value back)
> This is what Meta sends to confirm your webhook URL is valid

---

### 7.8 Verify Facebook Webhook
```
GET {{base_url}}/api/messaging/facebook/webhook/?hub.verify_token=YOUR_VERIFY_TOKEN&hub.challenge=88888&hub.mode=subscribe
```
> ✅ Expected: `88888`

---

### 📂 Simulate Incoming Messages (NO AUTH)

### 7.9 Simulate WhatsApp Message
```
POST {{base_url}}/api/messaging/whatsapp/webhook/
```
```json
{
  "entry": [{
    "changes": [{
      "value": {
        "metadata": {
          "phone_number_id": "123456789"
        },
        "messages": [{
          "from": "447700999888",
          "type": "text",
          "text": { "body": "Hello! Do you have iPhone 15 Pro in stock?" }
        }]
      }
    }]
  }]
}
```
> ✅ Expected: `{ "status": "ok" }` — then check Folder 5 for a new `channel: whatsapp` conversation

---

### 7.10 Simulate Facebook Message
```
POST {{base_url}}/api/messaging/facebook/webhook/
```
```json
{
  "entry": [{
    "messaging": [{
      "sender": { "id": "PSID_123456" },
      "recipient": { "id": "PAGE_123456789" },
      "message": { "text": "Hi, what are your store hours?" }
    }]
  }]
}
```

---

## 📁 FOLDER 8 — Analytics

### 8.1 Insights Overview
```
GET {{base_url}}/api/analytics/insights/?bot={{bot_id}}
Authorization: Bearer {{access}}
```
> ✅ Expected: `total_chats`, `total_messages`, `messages_used`, `messages_limit`, `avg_response_time`

---

### 8.2 Insights with Date Filter
```
GET {{base_url}}/api/analytics/insights/?bot={{bot_id}}&start=2026-01-01T00:00:00&end=2026-12-31T23:59:59
Authorization: Bearer {{access}}
```

---

### 8.3 Customer Locations
```
GET {{base_url}}/api/analytics/locations/?bot={{bot_id}}
Authorization: Bearer {{access}}
```

---

### 8.4 Top Questions
```
GET {{base_url}}/api/analytics/top-questions/?bot={{bot_id}}&limit=10
Authorization: Bearer {{access}}
```
> ✅ Expected: most frequent customer messages ranked by count

---

### 8.5 Chats Over Time (for charts)
```
GET {{base_url}}/api/analytics/chats-over-time/?bot={{bot_id}}
Authorization: Bearer {{access}}
```
> ✅ Expected: `chats_per_day` and `messages_per_day` arrays

---

### 8.6 Leads Summary
```
GET {{base_url}}/api/analytics/leads/?bot={{bot_id}}
Authorization: Bearer {{access}}
```
> ✅ Expected: `total`, `by_status: { new: x, contacted: x, converted: x }`, `by_channel`

---

## 📁 FOLDER 9 — Billing

### 9.1 Check Current Subscription
```
GET {{base_url}}/api/billing/subscription/
Authorization: Bearer {{access}}
```
> ✅ Expected: `{ "plan": "free", "status": "active" }` for new accounts

---

### 9.2 Create Stripe Checkout (Upgrade to Smart)
```
POST {{base_url}}/api/billing/checkout/
Authorization: Bearer {{access}}
```
```json
{
  "plan": "smart",
  "success_url": "http://localhost:3000/billing/success",
  "cancel_url": "http://localhost:3000/billing/cancel"
}
```
> ✅ Expected: `{ "checkout_url": "https://checkout.stripe.com/..." }`
> Open that URL in browser to test full Stripe payment flow

---

### 9.3 Open Billing Portal (Cancel / Manage)
```
POST {{base_url}}/api/billing/portal/
Authorization: Bearer {{access}}
```
```json
{
  "return_url": "http://localhost:3000/billing"
}
```
> ✅ Expected: `{ "portal_url": "https://billing.stripe.com/..." }`

---

### 9.4 List Invoices
```
GET {{base_url}}/api/billing/invoices/
Authorization: Bearer {{access}}
```

---

### 9.5 Test Stripe Webhook (Use Stripe CLI)
```
POST {{base_url}}/api/billing/webhook/
```
> ⚠️ Don't call this manually — use the Stripe CLI:
```bash
stripe listen --forward-to localhost:8000/api/billing/webhook/
stripe trigger checkout.session.completed
```
> ✅ Expected: tenant plan updated in DB after event fires

---

## ✅ CORRECT TESTING ORDER (Do This Exactly)

```
1.  Register                  → get email OTP
2.  Verify Email              → get access + refresh tokens
3.  Login                     → confirm tokens work
4.  Get Me                    → confirm user + tenant returned
5.  Get Tenant                → see plan limits
6.  Create Bot                → set {{bot_id}}
7.  Patch Bot Design          → customize the widget
8.  Add 2 Behaviors           → give bot personality
9.  Add Website URL           → wait 15 sec for Celery
10. Get Website (check status)→ confirm status = "ready"
11. Add 2 Q&A Pairs           → manual knowledge
12. Upload a file             → test file reader pipeline
13. Chat — Hello              → first message (no auth)
14. Chat — About knowledge    → RAG working? ← KEY TEST
15. Chat — Lead capture       → bot asks for info
16. Chat — Give details       → lead saved
17. List Conversations        → set {{conv_id}}
18. Takeover handoff          → human mode
19. Send agent message        → verify dispatch
20. Release handoff           → AI back
21. List Leads                → see Ahmed's lead
22. Update Lead status        → contacted
23. Export Leads CSV          → download works
24. Check Analytics           → see the numbers
25. Connect WhatsApp          → paste real tokens
26. Verify WA Webhook         → GET challenge test
27. Simulate WA message       → POST mock message
28. Check Conversations again → WA conv appeared
29. Stripe Checkout           → test upgrade flow
30. Get Subscription          → confirm plan changed
```

---

## ⚡ Quick Cheat Sheet (Copy-Paste URLs)

```
POST   /api/auth/register/
POST   /api/auth/verify-email/
POST   /api/auth/login/
POST   /api/auth/social-auth/
POST   /api/auth/token/refresh/
GET    /api/auth/me/
PATCH  /api/auth/me/
GET    /api/auth/profile/
PUT    /api/auth/profile/
PATCH  /api/auth/profile/update/
POST   /api/auth/profile/verify-email-change/
GET    /api/auth/tenant/
PATCH  /api/auth/tenant/
POST   /api/auth/agents/
GET    /api/auth/agents/
POST   /api/auth/password/change/
POST   /api/auth/logout/
POST   /api/auth/resend-otp/
POST   /api/auth/password/reset-request/
POST   /api/auth/password/reset-verify-otp/
POST   /api/auth/password/reset-confirm/
POST   /api/auth/account/delete/
POST   /api/auth/account/restore/

POST   /api/bots/
GET    /api/bots/<id>/
PATCH  /api/bots/<id>/design/
POST   /api/bots/<id>/behaviors/
GET    /api/bots/public/<id>/config/   ← NO AUTH

POST   /api/knowledge/<bot>/websites/
POST   /api/knowledge/<bot>/files/     ← multipart/form-data
POST   /api/knowledge/<bot>/qa/
GET    /api/knowledge/<bot>/gdrive/
DELETE /api/knowledge/<bot>/gdrive/
GET    /api/knowledge/<bot>/onedrive/
DELETE /api/knowledge/<bot>/onedrive/
POST   /api/knowledge/<bot>/import-external/

POST   /api/chat/                      ← NO AUTH

GET    /api/conversations/
POST   /api/conversations/<id>/handoff/
POST   /api/conversations/<id>/message/
WS     /ws/conversations/<bot_id>/

GET    /api/leads/
GET    /api/leads/export/
PATCH  /api/leads/<id>/

GET    /api/messaging/facebook/webhook/?hub.verify_token=...  ← NO AUTH
POST   /api/messaging/whatsapp/webhook/                       ← NO AUTH
POST   /api/messaging/facebook/
POST   /api/messaging/whatsapp/

GET    /api/analytics/insights/?bot=<id>
GET    /api/analytics/top-questions/?bot=<id>

GET    /api/billing/subscription/
POST   /api/billing/checkout/
POST   /api/billing/portal/
POST   /api/billing/webhook/           ← Stripe CLI only
```

# Developer & AI Agent Guide (`AGENTS.md`)

Welcome to the **SURE** repository. This document outlines the architecture, package management, testing patterns, and frontend stack to facilitate rapid and correct development by human developers and AI coding assistants.

---

## 1. Codebase Overview

- **Development Environment**: The repository is fully pre-configured to work in a **Docker Devcontainer** (`.devcontainer`). Standard native terminal commands may fail due to lack of dependencies outside of the container. Run commands via the devcontainer.
- **Backend**: Django web application.
- **Package Manager**: **`uv`** (configured via `pyproject.toml` and `uv.lock`). 
- **Frontend**: A Single Page Application (SPA) built using **Vue 3**, **TypeScript**, and the **PrimeVue (v4)** component library located in the `frontend/` directory. (Note: TailwindCSS is NOT used).

---

## 2. Backend Highlights & Architecture

### App Structure
- `sure/`: Contains the core client forms, case registration, and questionnaire logic. 
  - `models.py`: Defines key entities like `Case`, `Visit` (which links a case to a questionnaire and holds status/tags), `Questionnaire`, `ClientQuestion`, and `Test`.
  - `client_service.py`: Contains transactional business actions like `create_case`, `create_visit`, `can_connect_case`, and `connect_case`.
  - `admin.py`: Encompasses Unfold Admin registrations and views.
- `tenants/`: Handles multi-tenant permissions. Features `Tenant` (organizations), `Location` (centers mapped to tenants), and `Consultant` (users).
- `labor/` & `sms/` & `texts/`: Micro-services handling lab integrations, SMS notifications, and localization/translation databases.

### Multi-Tenant Access Control
When writing admin views or models, access must be secured per-tenant. Non-superuser staff should only access objects owned by the tenants they administer:
```python
# Filtering records in get_queryset
tenants = request.user.tenants.all()
queryset = queryset.filter(case__location__tenant__in=tenants)
```

---

## 3. Django Admin 2FA & Unit Testing

### The 2FA Enforcement
The repository uses a custom `MyAdminSite` (`core/admin.py`) which subclasses Unfold's `UnfoldAdminSite`. It wraps all admin views with an `enforce_2fa` decorator.
This means that any HTTP request to `/admin/` (even by superusers) will be redirected (`302`) to `/login` or `/setup-2fa` if:
1. The user is not verified via OTP (`django-otp`).
2. The user's device/agent is not trusted (`django-agent-trust`).

### How to Bypass 2FA in Unit Tests
To write integration tests (`django.test.TestCase` using `self.client`) targeting custom admin views, you **must bypass 2FA in the test client's session**.

You can achieve this by creating a confirmed `TOTPDevice` for the test user and manually writing its persistent ID to the client's session before sending requests:

```python
from django.urls import reverse
from django_otp.plugins.otp_totp.models import TOTPDevice

def test_custom_admin_view(self):
    # 1. Setup user roles
    self.user.is_superuser = True
    self.user.is_staff = True
    self.user.save()

    # 2. Create verified OTP device and login
    device = TOTPDevice.objects.create(user=self.user, name="default", confirmed=True)
    self.client.force_login(self.user)

    # 3. Inject the device persistent ID into the test client session
    session = self.client.session
    session["otp_device_id"] = device.persistent_id
    session.save()

    # 4. Perform requests normally
    url = reverse("admin:your_custom_view_name")
    response = self.client.get(url)
    self.assertEqual(response.status_code, 200)
```

---

## 4. Frontend Highlights & Architecture

- **Stack**: Vue 3, Vue Router, Pinia (state management), TypeScript, Vite, PrimeVue (v4).
- **Location**: Everything lives in `/workspaces/sure/frontend/`.
- **API Client Generation**: The frontend uses `openapi-ts` to automatically generate API clients matching the Django Ninja backend endpoints. Types are synced in `frontend/src/client/types.gen.ts`.
- **Layouts**: Custom views are divided between client-facing routes (`/client/:caseId`) and consultant-facing dashboards (`/consultant`).

---

## 5. Quick Development Commands

Run these inside the devcontainer (`docker exec`):

### Running Unit Tests
```bash
python manage.py test
```

### Running Backend Dev Server
```bash
python manage.py runserver
```

### Frontend Dependencies & Dev Server
```bash
cd frontend
npm install
npm run dev
```

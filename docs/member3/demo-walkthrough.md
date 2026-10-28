# BundleGraph: 3-Minute Hackathon Demo & Evaluation Walkthrough

This document guides judges and teammates through the complete, reproducible **Member 3 (Experience)** demonstration.

---

## 1. Quick Start Guide (One-Command Dev)

### Terminal 1: Python API Bridge (Optional - Frontend has full offline fallback)
```powershell
cd e:\study\BundleGraph\BundleGraph
$env:PYTHONPATH="src"
python -m uvicorn bundlegraph_api.app:app --port 8000 --reload
```

### Terminal 2: Vite React Frontend
```powershell
cd e:\study\BundleGraph\BundleGraph\frontend
npm run dev
```
Open **http://localhost:5173** in your browser.

> [!NOTE]  
> If the Python server is not started, the application operates in **Autonomous Offline Fixture Mode** using validated static fixtures from Member 1 without throwing network errors.

---

## 2. The 3-Minute Hackathon Storyboard (Judge Script)

### [0:00 - 0:40] Act I: The Real-World Problem & The "1-Input Trap"
1. **Show the Interface:** Point out the tactile, high-contrast studio engineering interface. Highlight that this is **not generic AI slop**—no purple/blue gradients or ungrounded claims.
2. **Click Preset 2: `[The 1-Input Trap]`** on the top toolbar.
   - Scenario: A user asks for a 2-person podcast on a cheap budget using *Interface One*.
   - Click **"Extract Requirements & Review"**, then **"Confirm Constraints & Solve Bundles"**.
   - **The Result:** BundleGraph safely rejects the bundle:
     `NO_FEASIBLE_BUNDLE: Rule R2 Rejection (Interface One has only 1 microphone input, which is physically incompatible with 2 required microphones)`.
   - **Key Judge Takeaway:** Generic LLM chatbots hallucinate and recommend incompatible hardware. BundleGraph prevents costly purchasing mistakes with mathematical constraint verification.

---

### [0:40 - 1:30] Act II: Complete Verified Bundle & Sponsor Integrations
1. **Click Preset 1: `[Standard 2-Person Podcast]`** on the top toolbar.
   - Goal: 2-person podcast, $600 budget, USB-C laptop.
2. Click **"Extract Requirements & Review"** $\rightarrow$ shows extracted facts vs questions.
3. Click **"Confirm Constraints & Solve Bundles"** $\rightarrow$ generates verified proposal `prop-verified-std-v1` ($443.00 USD).
4. **Demonstrate Sponsor Integrations:**
   - **AG Grid Integration:** Switch to the **AG Grid** tab. Filter by Category, sort by Unit Price, and inspect the verified rule badges for each component.
   - **React Flow Evidence Graph:** Switch to the **React Flow** tab. Point out the interactive dependency graph (`Mic` $\rightarrow$ `XLR` $\rightarrow$ `Interface` $\rightarrow$ `Laptop`). Click on any rule finding (e.g. `R2_INTERFACE_INPUT_CAPACITY`) to inspect the verified physical evidence citation.
   - **Bryntum Timeline:** Switch to the **Bryntum Schedule** tab. Show how the hardware shipping, transit days, and studio assembly/soundcheck buffer are mapped against the user's launch deadline.

---

### [1:30 - 2:30] Act III: Immutable Approval & Injected Stock Failure
1. Click **"Lock Exact Plan & Proceed to Approval"**.
2. **Explain Cryptographic Plan Binding:**
   - Plan ID `plan-v1-8f92`
   - Plan Version `1.0 (Locked)`
   - Exact Total `$443.00 USD`
   - Point out: An approval is bound to **one exact plan version**. A model or merchant cannot silently change items or prices.
3. **Simulate Injected Stock Failure:**
   - Check the box **"Inject Stock Failure"** (simulating merchant zero-stock on primary microphones).
   - Click **"Authorize with PayPal Sandbox"**.
   - **The Result:** The transaction halts to protect buyer funds.
   - An alert appears: `SECURITY LOCK: PREVIOUS APPROVAL INVALIDATED`.

---

### [2:30 - 3:00] Act IV: Dependency-Aware Re-planning & Zapier Alert
1. **Show the Re-planning Diff / Delta Card:**
   - ❌ **Removed:** 2x Mic Alpha (-$198.00)
   - ✅ **Added:** 2x Mic Gamma (+$170.00, compatible alternative)
   - 🔒 **Retained Working Cart:** Interface Two, XLR Cables, Headphones remain locked so the buyer doesn't lose their cart.
   - 💰 **Price Impact:** Updated plan total is **$415.00** ($28.00 savings!).
   - 📅 **Bryntum Schedule Update:** Delivery shifted by +1 day, but still comfortably 2 days before the Friday recording deadline.
2. **Show the Zapier Integration:**
   - Point out the `Zapier Webhook Notification Dispatched` card confirming that an external notification (`bundle_replan_recovery`) was broadcasted to team channels.
3. **Click "Approve Plan 2.0 ($415.00) & Settle via PayPal":**
   - Completes the journey with full auditability and state reconciliation.

---

## 3. Sponsor Checklist for Judges

| Sponsor | Feature Demonstrated in BundleGraph | Screen Location |
| :--- | :--- | :--- |
| **AG Grid** | Candidate & bundle comparison grid with sorting, filtering, and status badges. | Screen 3 (Tab 1) |
| **Bryntum** | Project schedule timeline mapping order dispatch, shipping, assembly buffer, and deadline. | Screen 3 (Tab 3) & Screen 5 |
| **Zapier** | Automated outbound webhook dispatch on recovery re-planning event. | Screen 5 |
| **PayPal Sandbox** | Version-specific authorization, strict plan binding, and stock outage compensation. | Screen 4 & Screen 5 |

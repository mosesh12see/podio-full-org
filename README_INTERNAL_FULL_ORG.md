# INTERNAL FULL ORG TRACKER - RULES & DOCUMENTATION

**CRITICAL: This tracker works DIFFERENTLY from other trackers!**

---

## App Information

- **App URL:** https://podio.com/eg-solar/full-org/apps/full-org#/views/61308842
- **App ID:** 30430059
- **Token:** daf910d595cc805cf91a4ab4edc293cb
- **Also Called:** "Internal" or "Full Org" (these terms are interchangeable)

---

## How Payment Status Works (DIFFERENT FROM OTHER TRACKERS)

The **SPS field** determines payment status:

| SPS Value | Payment Status | Notes |
|-----------|---------------|-------|
| **NP** | Not Paid | Standard unpaid status |
| **P** | Paid | Standard paid status |
| **Empty/Not Set** | **PAID** (via Google Sheets) | These show in "Paid by Sheets" view |

### Important:
- **Empty SPS = PAID** (not unpaid like you might expect!)
- There's a specific view called **"Paid by Sheets"** that shows all jobs where SPS is empty/not set
- These were paid through Google Sheets integration

---

## Special Audit Case: "Sit Dispo Changed" Jobs

### What Are These?
Special sits that were:
1. Initially marked as **"sat"** (sit = Yes)
2. Later changed to **"no sit"** (sit ≠ Yes)
3. Still showing up in the main view (as they should be)

**Note:** The number of these jobs varies - it's **whatever jobs match the criteria** at any given time (not a fixed number).

### How to Identify Them:
**Rule:** `SPS = NP` **AND** `Sit ≠ Yes`

### Why This Happens:
1. When `sit` field is marked as **"Yes"**, Podio **automatically sets** `SPS = NP` (Not Paid)
2. If someone later changes `sit` back to something else (No, or empty), the `SPS` field stays at `NP`
3. This creates a discrepancy: job shows as "Not Paid" but isn't actually a sit anymore

### Purpose of Audit:
- Need to investigate WHY these were changed from "sat" to "no sit"
- Verify if payment status should be updated
- Ensure proper tracking

### Screenshot Reference:
- See screenshot: **"sit dispo changed.png"**
- Shows the filtered view of these 20 jobs

---

## Views in Internal Full Org

1. **Full Internal All View (Private)**
   - Shows: Customer, SPS
   - Screenshot: "Full Org Internal ALL view.png"

2. **Paid by Sheets**
   - Shows all jobs where SPS is empty/not set
   - These are paid via Google Sheets

3. **Sit Dispo Changed**
   - Shows jobs with sit status discrepancies (number varies)
   - Filter: SPS = NP AND Sit ≠ Yes
   - These need manual audit

---

## Key Differences from Other Trackers

| Feature | Other Trackers | Internal Full Org |
|---------|---------------|-------------------|
| Payment field | "Paid Status" | **SPS** |
| Empty value means | Usually unpaid | **PAID (via sheets)** |
| Paid values | "Paid" | "P" or Empty |
| Unpaid values | "Need to pay" | **"NP"** |
| Special audit | No | **Yes - "sit dispo changed" jobs (varies)** |

---

## When Coding for Internal Full Org

### ✅ DO:
- Use **SPS field** for payment status
- Count **both "P" and Empty** as PAID
- Count **only "NP"** as UNPAID
- **Always check** for "sit dispo changed" jobs: `SPS = NP AND Sit ≠ Yes` (number varies!)
- Reference "Paid by Sheets" view for empty SPS values

### ❌ DON'T:
- Don't treat empty SPS as unpaid
- Don't use "Paid Status" field (use SPS instead)
- Don't ignore the "sit dispo changed" jobs in audits (always query for them!)

---

## Payment Calculation Formula

```
Unpaid Balance = (Count of SPS = "NP") × Rate Per Sit

Paid Count = (Count of SPS = "P") + (Count of SPS = Empty/Not Set)

Total Sits = Unpaid Balance + Paid Count
```

---

## External ID Field Mappings

Based on screenshots and previous data:

- Customer: `customer-name`
- SPS: `sps`
- Sit: `sit`
- Transaction ID: `transaction-id`
- Appointment Date: `appointment-date`
- Manager/Closer: `closer-assigned`
- REP: `rep`

---

## Summary for Claude

**When working with Internal Full Org tracker:**

1. **SPS = Payment Status** (not "Paid Status" field)
2. **Empty SPS = PAID** (via Google Sheets)
3. **Always query for special audit cases:** SPS=NP AND Sit≠Yes (number varies!)
4. **These jobs need investigation** - they were marked as sit, then changed back
5. **This tracker is DIFFERENT** from MEB, Elevate You, and Suntria

---

## Last Updated
2025-10-24

## Related Files
- Screenshot: `Full Org Internal ALL view.png`
- Screenshot: `sit dispo changed.png`
- Reference: `PODIO_APPS_REFERENCE.txt`

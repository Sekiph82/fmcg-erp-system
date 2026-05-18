# Common Problems and FAQ

**Audience:** All Staff  
**Version:** 1.0 (2026-05-18)

---

## Login Problems

**Q: I forgot my password.**  
A: Click **Forgot Password** on the login page. An email will be sent to your registered email address with a reset link. If you do not receive the email within 5 minutes, contact your administrator.

**Q: My account says "Inactive".**  
A: Your account has been deactivated. Contact your administrator to reactivate it.

**Q: I entered my password correctly but it says wrong.**  
A: After 5 failed attempts, the account is temporarily locked. Wait 15 minutes or ask admin to unlock it. Passwords are case-sensitive.

**Q: I set up 2FA but lost my authenticator phone.**  
A: Contact admin immediately. They can disable 2FA for your account so you can log in and set up a new authenticator.

**Q: I see "Permission Denied" when I open a page.**  
A: You need to be assigned the correct role for that module. Contact your administrator and tell them which page you need access to.

---

## Production

**Q: I cannot find my production order in the Shop Floor terminal.**  
A: The order must be released by a supervisor first. Ask your supervisor to release the order from Production → Orders tab.

**Q: The system says "Insufficient stock" when I try to release a production order.**  
A: Check which material is short. Raise a purchase request or check if stock is in an alternate location.

**Q: My batch number is not printing.**  
A: Check that the production order status is "Completed" and batch number has been assigned in the Batch & Lots tab. Check printer connection.

**Q: OEE is showing 0% for my line.**  
A: This usually means no production output was confirmed today. Ensure output is confirmed in the Execution tab.

---

## Inventory / Warehouse

**Q: Stock shows negative — how is that possible?**  
A: A movement was posted when the balance was zero (e.g., issue before receipt). Check the Movements tab for the erroneous entry. Contact admin to reverse the posting.

**Q: I cannot find a delivery to receive against.**  
A: The purchase order must be approved and released by procurement before it appears in Deliveries. Contact procurement.

**Q: A batch I received yesterday is not showing in stock.**  
A: Check if the receipt was confirmed (Procurement → Deliveries → status should be "Received"). If still "Pending", confirm the delivery.

---

## Sales / Invoicing

**Q: I cannot create an invoice — the button is greyed out.**  
A: The sales order must have a confirmed shipment (delivery note) before invoicing. Check logistics.

**Q: Customer invoice is not going to eTIMS.**  
A: The customer must have a valid KRA PIN in their master record. Update the customer KRA PIN and re-post the invoice.

**Q: A customer says they paid but it is not showing in the system.**  
A: Check Collections tab for any unmatched payments. If M-Pesa, check Finance → M-Pesa for unreconciled transactions.

**Q: Sales order is showing wrong price.**  
A: Price comes from the customer's assigned price list. Check Sales → Price Lists. If the list is correct, the customer may be on the wrong price list — update in customer master.

---

## Finance / Payroll

**Q: PAYE calculation looks wrong.**  
A: KRA tax bands may have changed. Check Payroll Settings and compare to KRA website. Contact admin if update is needed.

**Q: NHIF deduction is zero.**  
A: Employee NHIF number may be missing from their payroll profile. Add the NHIF number and recalculate.

**Q: Bank reconciliation shows large unreconciled balance.**  
A: Common causes: payments imported from bank statement not matched to transactions in ERP, or M-Pesa not reconciled. Use Finance → Bank Reconciliation → Unmatched tab to investigate.

---

## Quality Control

**Q: I cannot post an inspection — submit button not working.**  
A: All mandatory parameters must have a test result entered before submission. Check for empty required fields.

**Q: CoA is generating with blank test results.**  
A: The CoA pulls data from the inspection record. Ensure all tests were entered and the inspection was completed (not just saved as draft).

---

## System / Technical

**Q: The page is not loading — just spinning.**  
A: Try refreshing (F5). If still spinning after 30 seconds, check if the server is running. Contact IT.

**Q: I see "Application Error" overlay.**  
A: This is a system error. Take a screenshot and report to IT with the exact page you were on and what you were trying to do.

**Q: Everything is slow today.**  
A: Could be peak usage time or server load. Check with IT if performance is consistently slow for more than 10 minutes.

**Q: I exported data to Excel but some columns are missing.**  
A: Export includes only the currently visible columns. If a column is hidden, click the column settings (gear icon) to show it before exporting.

---

## Contact Support

For issues not covered here:

1. Ask your supervisor first
2. Contact IT / System Administrator: [add contact]
3. Screenshot the error and the page you were on before reporting
4. Include: your username, the time it happened, and what you were trying to do

# Shopnoltd Manual UI Checklist

Backend reachability is covered by the curl smoke test. This checklist is for
what only a real browser session can confirm — actual rendering, button
behavior, and end-to-end flows.

Log in as `test_user` first, repeat the relevant sections as `test_admin`.

## Blog
- [ ] Blog list page loads and shows posts (not blank/loading forever)
- [ ] Clicking a post opens the full post (not a 404 or blank page)
- [ ] Images/thumbnails in posts actually load
- [ ] Any comment/like button responds (even if just a toast/error, not a silent no-op)

## User Dashboard (test_user)
- [ ] Dashboard loads after login without redirect loop
- [ ] Profile/account section shows correct username
- [ ] Any "Services" or "My Subscriptions" list renders real data, not placeholders
- [ ] Logout works and actually clears the session (reload shows logged-out state)

## Admin Dashboard (test_admin)
- [ ] Admin nav item is visible (only for admin account, not test_user)
- [ ] Database/user-management tab loads a real table, not a spinner or 404
- [ ] Can view (not necessarily modify) a user record
- [ ] Any admin-only settings page renders without a permissions error

## Billing / Payment / Exchange (as test_user)
- [ ] Billing page shows an invoice list or "no invoices" state — not an error
- [ ] Adding/viewing a payment method doesn't throw a console error
- [ ] Exchange/currency conversion widget returns a rate, not blank/NaN
- [ ] Attempting a real charge is NOT required — stop at the point where it
      would hit a live payment processor unless you intend to test that path
      with a sandbox/test-mode key

## Cross-cutting
- [ ] Open browser devtools → Network tab while doing the above; note any
      request returning 4xx/5xx even if the UI doesn't visibly break
- [ ] Note the exact API paths you see called — feed those back so the curl
      script's placeholder paths (`/api/v1/...`) can be corrected to match reality

## After testing
- [ ] Rotate `test_admin` and `test_user` passwords (they were shared in chat)

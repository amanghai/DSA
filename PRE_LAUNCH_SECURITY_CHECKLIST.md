# Pre-Launch Security Checklist

> Ship Products, Not Liabilities.
>
> The security, privacy & abuse checklist every vibe coder needs before going live.
> Built for AI builders shipping with Cursor, GPT, Bolt, Replit & more.

---

## 01 — Legal & Privacy

- [ ] **Add a privacy policy to your app**
  If you collect ANY user data — emails, names, usage analytics — you legally need this. Free generators exist online, but make sure it actually matches what your app does.

- [ ] **Know exactly where user data is stored**
  Is it in a database? Which provider? Which region? If a user asks "where is my data?" you need an answer.

- [ ] **Understand your GDPR / data law obligations**
  If you have users in the EU, you need cookie consent, data deletion capability, and clear data processing terms. This applies even if YOU are not in the EU.

- [ ] **Don't collect data you don't need**
  Every field you collect is a liability. If you don't need their phone number, don't ask for it.

- [ ] **Add a terms of service page**
  This protects YOU. It sets expectations for what your app does and limits your liability if something breaks.

> **Pro Tip:** Prompt your AI: *"Generate a privacy policy for my app that collects [list your data]. Cover GDPR, CCPA, and include a cookie policy."* Then actually read it and customize it.

---

## 02 — Security Basics

- [ ] **Scan against OWASP Top 10**
  These are the 10 most common web vulnerabilities. SQL injection, broken auth, XSS — if you haven't checked for these, your app is probably vulnerable.

- [ ] **Check all security headers**
  `Content-Security-Policy`, `X-Frame-Options`, `HSTS`, `X-Content-Type-Options`. Most vibe-coded apps ship with zero security headers.

- [ ] **Test for SQL injection on every input**
  If a user can type into a field and it touches your database, test it. One unescaped input can leak your entire database.

- [ ] **Test for XSS (Cross-Site Scripting)**
  Can a user inject JavaScript through any input field? If yes, they can steal sessions, redirect users, or deface your app.

- [ ] **Verify authentication and session handling**
  Are sessions expiring? Are tokens secure? Can someone bypass login? Test every auth flow.

> **Pro Tip:** Quick win: Prompt your AI with *"Review my app as a security specialist and make sure I have strong security headers and a solid baseline security posture."* Takes 2 minutes.

---

## 03 — Secrets & API Keys

- [ ] **Check that `.env` files are in `.gitignore`**
  If your `.env` file is committed to git, your API keys are public. Check your git history too — removing it now doesn't delete it from past commits.

- [ ] **No API keys in frontend / client-side code**
  Anything in your frontend JavaScript is visible to anyone. Open DevTools > Sources and search for `key`, `token`, `secret`. If you find one, you have a problem.

- [ ] **Check API responses for sensitive data leaks**
  Are your API endpoints returning user passwords, tokens, or internal IDs? Log a response and check every field.

- [ ] **Remove secrets from logs and error messages**
  Stack traces and error logs often contain database URLs, API keys, and tokens. Make sure your logging sanitizes sensitive data.

- [ ] **Move all keys server-side or behind a proxy**
  If your frontend needs to call a third-party API, route it through your backend. Never expose third-party keys to the client.

> **Pro Tip:** Run this in your terminal to find any OpenAI keys hiding in your codebase:
> ```bash
> grep -r 'sk-' --include='*.js' --include='*.ts' --include='*.py' .
> ```
> Do the same for `API_KEY`, `SECRET`, `TOKEN`.

---

## 04 — Abuse Prevention

- [ ] **Add rate limiting to all API endpoints**
  Without rate limits, one person or bot can call your API thousands of times per minute. If you're using a paid API like OpenAI, that's your bill getting burned.

- [ ] **Set up spend alerts and hard caps on paid APIs**
  Most API providers let you set billing alerts and usage limits. Set them BEFORE you launch, not after you get a surprise bill.

- [ ] **Add input validation on every user-facing field**
  Don't trust user input. Ever. Validate type, length, format, and range on both frontend AND backend.

- [ ] **Implement basic bot protection**
  CAPTCHAs, honeypot fields, or rate limiting on signup/login. If bots can create unlimited accounts, they will.

- [ ] **Plan for abuse scenarios before they happen**
  What if someone uploads illegal content? What if someone spams your API? What if someone creates 10,000 accounts? Have a plan.

> **Pro Tip:** The #1 way vibe coders lose money: shipping an AI wrapper with no rate limits. Someone finds your endpoint, writes a script, and burns through your entire OpenAI budget in one night. Add rate limits on day one.

---

## 05 — Copy-Paste Security Prompts

Paste these into any AI coding tool to instantly audit your app.

### Full Security Audit
```
Review my app as a security specialist. Check for SQL injection, XSS, CSRF,
broken authentication, and insecure direct object references. List every
vulnerability with severity and fix.
```

### Environment & Secrets Check
```
Scan my entire codebase for hardcoded API keys, tokens, passwords, and secrets.
Check if .env files are gitignored. Check if any sensitive values are exposed
in frontend code or API responses.
```

### Security Headers
```
Review my app's HTTP security headers. Make sure I have Content-Security-Policy,
X-Frame-Options, X-Content-Type-Options, Strict-Transport-Security, and
Referrer-Policy properly configured.
```

### Rate Limiting
```
Add rate limiting to all my API endpoints. Implement IP-based and user-based
limits. Add exponential backoff for auth endpoints to prevent brute force attacks.
```

### Privacy & GDPR Check
```
Review my app for GDPR compliance. Check what user data I collect, where it's
stored, if I have a privacy policy, cookie consent, data deletion capability,
and if I'm logging any PII.
```

---

> AI builds the app. **You secure it.**
>
> Run this checklist before every launch. Ship products, not liabilities.

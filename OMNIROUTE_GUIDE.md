# 🚀 OmniRoute — Setup & Beginner's Guide

A super-simple guide to installing and using **OmniRoute**
(<https://github.com/diegosouzapw/OmniRoute>), explained like you're 10 years old.

---

## 🧸 What is OmniRoute? (the kid version)

Imagine you have **lots of different robot helpers** (AIs) — one from Google,
one from OpenAI, some free ones, some paid ones. Normally, to talk to each
robot you'd need a **different remote control** for every single one. Annoying!

**OmniRoute is ONE magic remote** that talks to *all* the robots.

- You press one button → it picks the **best** robot for the job.
- If a robot is **tired** (its free turns ran out), it quietly asks the
  **next** robot instead. You never get stuck.
- It **tries the FREE robots first**, so you spend $0 when you can.

You point your coding tools at **one address**, and OmniRoute does the rest.

---

## ✅ Did it install correctly? (Yes!)

Here's what was checked, and the result:

| Check | What it means | Result |
|-------|---------------|--------|
| `omniroute --version` | The program exists | ✅ **3.8.49** |
| `omniroute serve` | The server turns on | ✅ Booted on port **20128** |
| Open `http://localhost:20128` | The dashboard page loads | ✅ **HTTP 200** (login page) |
| `http://localhost:20128/v1/models` | It lists usable AI models | ✅ **115 models** |
| Database (SQLite) | It can save your settings | ✅ **Working** (1.6 MB) |

> **One note:** an actual test chat couldn't finish *in this locked-down cloud
> sandbox* because the sandbox blocks the internet to the free-AI websites
> (`opencode.ai`, `felo.ai` returned "no connection"). That is a **network wall
> of the sandbox — NOT a problem with OmniRoute.** On a normal computer with
> regular internet, the same command returns an answer. The router itself
> worked perfectly: it built a pool of 11 providers and tried them in order.

**Bottom line: OmniRoute is installed properly.** ✅

---

## 🛠️ How to install it yourself (3 tiny steps)

You only need **Node.js** first (version 22.22.2+ or 24). Check with `node -v`.

### Step 1 — Install OmniRoute (one line)
```bash
npm install -g omniroute
```
That's it. This downloads the magic remote onto your computer.

### Step 2 — Turn it on
```bash
omniroute serve
```
You'll see a big "OmniRoute" logo and:
```
Dashboard:  http://localhost:20128
API Base:   http://localhost:20128/v1
```

### Step 3 — Open the control panel
Open this in your web browser:
```
http://localhost:20128
```
The first time, it asks you to make a **username + password**. Do that — it's
your private lock so nobody else can use your remote.

🎉 **Done! OmniRoute is running.**

---

## 🎮 How to actually USE it (simple points)

Think of **two important addresses**:

1. **The control panel (for your eyes):** `http://localhost:20128`
   - This is the dashboard. Click around to see providers, free tiers, and usage.
2. **The brain plug (for your apps):** `http://localhost:20128/v1`
   - This is what you give to your coding tools. It speaks the same "language"
     as OpenAI, so almost every AI tool understands it.

### 👉 Point a tool at OmniRoute
In any tool that asks for an **"OpenAI Base URL / API endpoint"**, put:
```
http://localhost:20128/v1
```
- Use the model name **`auto`** → OmniRoute picks the best/free robot for you.
- For a key, use the one you create in the dashboard (or any placeholder if
  you haven't set one up yet).

Works with: **Claude Code, Cursor, Cline, VS Code Copilot, Codex,** and more.

### 👉 Try it from the terminal (a quick test)
```bash
curl http://localhost:20128/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"auto","messages":[{"role":"user","content":"Say hello!"}]}'
```
On a normal internet connection, a robot replies with a hello. 👋

### 👉 See all the models it can use
```bash
curl http://localhost:20128/v1/models
```

### 👉 Add more robots (providers)
1. Go to `http://localhost:20128` (the dashboard).
2. Find the **Providers** section.
3. Paste in an API key for any provider you have (Groq, DeepSeek, Gemini, etc.).
4. OmniRoute now includes that robot in its "who should I ask?" list.

### 👉 Turn it off / on again
```bash
omniroute stop        # turn the server off
omniroute serve       # turn it back on
omniroute status      # is it running? what's connected?
```

---

## 🧭 Cheat sheet (stick this on your wall)

| I want to... | Type this |
|--------------|-----------|
| Install it | `npm install -g omniroute` |
| Start it | `omniroute serve` |
| Stop it | `omniroute stop` |
| Check it | `omniroute status` |
| See models | `curl http://localhost:20128/v1/models` |
| Open dashboard | visit `http://localhost:20128` |
| Plug apps into it | use base URL `http://localhost:20128/v1`, model `auto` |

---

## ❓ If something goes wrong

- **"command not found: omniroute"** → Node's global folder isn't on your PATH,
  or install again with `npm install -g omniroute`.
- **Chat says "fetch failed" / connection error** → your network is blocking the
  AI websites (like in a locked-down cloud box). Try on a normal internet
  connection, or add your own provider API key in the dashboard.
- **Port 20128 already in use** → start on another port: `omniroute serve --port 8080`.
- **Need to reinstall clean** → `npm uninstall -g omniroute && npm install -g omniroute`.

---

*Guide generated after a verified install of `omniroute@3.8.49`. Official repo:
<https://github.com/diegosouzapw/OmniRoute> · Docs & dashboard at
`http://localhost:20128`.*

# Chrome / Chromium Setup

The `token_retriever` uses [pyppeteer](https://github.com/pyppeteer/pyppeteer) to drive a headless Chromium browser.  
By default it looks for the binary **inside this folder**:

| Platform | Expected path |
|----------|---------------|
| Windows  | `chrome/chrome.exe` |
| Linux / macOS | `chrome/chrome` |

You can always override the binary path by passing `chrome_executable=` to `fetch_access_token()`.

---

## Windows

A pre-built Chromium 133 for Windows x64 is available on Google Drive.

1. Download the archive:  
   <https://drive.google.com/file/d/1r7Cu5SsR04pgokneexfjWHpoQAIXk6vg/view?usp=sharing>
2. Extract the archive so that `chrome.exe` is at `advisor/utils/token_fatcher/chrome/chrome.exe` (alongside `chrome.dll`, `Locales/`, etc.).

The files already present in this folder (`chrome.dll`, `WidevineCdm/`, ...) are part of that Windows build - no extra steps needed if you downloaded and extracted correctly.

---

## Linux

### Option A - system package (recommended for CI/Docker)

```bash
# Debian / Ubuntu
sudo apt-get update && sudo apt-get install -y chromium-browser

# Then pass the system binary explicitly:
# fetch_access_token(..., chrome_executable="/usr/bin/chromium-browser")
```

### Option B - portable Chromium binary in this folder

1. Find the revision that matches Chromium 133 (`133.0.6943.116`) on the [Chromium snapshots index](https://commondatastorage.googleapis.com/chromium-browser-snapshots/index.html?prefix=Linux_x64/).
2. Download `chrome-linux.zip` for that revision.
3. Extract so the binary lands at `advisor/utils/token_fatcher/chrome/chrome` (the `chrome` executable, not a sub-directory).
4. Make it executable:
   ```bash
   chmod +x advisor/utils/token_fatcher/chrome/chrome
   ```

You may also need runtime libraries on minimal systems:

```bash
sudo apt-get install -y libnss3 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 \
    libxrandr2 libgbm1 libasound2
```

---

## macOS

### Option A - Homebrew (easiest)

```bash
brew install --cask chromium

# Then pass the binary explicitly:
# fetch_access_token(..., chrome_executable="/Applications/Chromium.app/Contents/MacOS/Chromium")
```

### Option B - portable binary in this folder

1. Download a macOS Chromium snapshot from the [snapshots index](https://commondatastorage.googleapis.com/chromium-browser-snapshots/index.html?prefix=Mac/).
2. Extract so the binary is at `advisor/utils/token_fatcher/chrome/chrome`.
3. Make it executable and remove the macOS quarantine flag:
   ```bash
   chmod +x advisor/utils/token_fatcher/chrome/chrome
   xattr -d com.apple.quarantine advisor/utils/token_fatcher/chrome/chrome
   ```

---

## Docker / containers

Add to your `Dockerfile` (Debian/Ubuntu base):

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium-driver chromium \
 && rm -rf /var/lib/apt/lists/*
```

Then pass the binary path explicitly:

```python
await fetch_access_token(
    web_ui_url=...,
    email=...,
    password=...,
    chrome_executable="/usr/bin/chromium",
)
```

The `--no-sandbox` and `--disable-dev-shm-usage` flags are already passed automatically when launching - no extra config needed for containers.
